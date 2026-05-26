from fastapi import status

def test_available_appointments_calculation(client):
    # 1. Register Patient & Specialist
    pat_payload = {
        "email": "avpatient@example.com",
        "password": "securepassword",
        "first_name": "Test",
        "last_name": "Patient",
        "role": "Patient"
    }
    client.post("/auth/register", json=pat_payload)
    login_resp = client.post("/auth/login", json={"email": "avpatient@example.com", "password": "securepassword"})
    pat_token = login_resp.json()["access_token"]
    pat_me = client.get("/users/me", headers={"Authorization": f"Bearer {pat_token}"})
    pat_id = pat_me.json()["user_id"]

    spec_payload = {
        "email": "avspecialist@example.com",
        "password": "securepassword",
        "first_name": "Test",
        "last_name": "Specialist",
        "role": "Specialist",
        "specialist_details": {
            "specialization": "Dermatolog",
            "default_appointment_duration_minutes": 30,
            "office_address": "Office D"
        }
    }
    client.post("/auth/register", json=spec_payload)
    login_resp = client.post("/auth/login", json={"email": "avspecialist@example.com", "password": "securepassword"})
    spec_token = login_resp.json()["access_token"]
    spec_me = client.get("/users/me", headers={"Authorization": f"Bearer {spec_token}"})
    spec_id = spec_me.json()["user_id"]

    # 2. Add availability block: 2026-08-01 from 08:00 to 10:00 (4 slots of 30 mins)
    client.post(
        f"/specialists/{spec_id}/schedule/blocks",
        json={
            "start_time": "2026-08-01T08:00:00",
            "end_time": "2026-08-01T10:00:00",
            "block_type": "AVAILABLE"
        },
        headers={"Authorization": f"Bearer {spec_token}"}
    )

    # 3. Query slots - should return 4 slots
    avail_resp = client.get("/available-appointments?date=2026-08-01&specialistId=" + spec_id)
    assert avail_resp.status_code == status.HTTP_200_OK
    avail_data = avail_resp.json()[0]
    assert len(avail_data["availableSlots"]) == 4

    # 4. Add a BREAK block: 09:00 to 09:30
    client.post(
        f"/specialists/{spec_id}/schedule/blocks",
        json={
            "start_time": "2026-08-01T09:00:00",
            "end_time": "2026-08-01T09:30:00",
            "block_type": "BREAK"
        },
        headers={"Authorization": f"Bearer {spec_token}"}
    )

    # 5. Query slots - slot 09:00-09:30 should be removed (leaving 3 slots)
    avail_resp = client.get("/available-appointments?date=2026-08-01&specialistId=" + spec_id)
    avail_data = avail_resp.json()[0]
    slots = avail_data["availableSlots"]
    assert len(slots) == 3
    # Check start times do not include 09:00:00
    start_times = [s["startTime"] for s in slots]
    assert not any("09:00:00" in t for t in start_times)

    # 6. Book slot 08:00 - 08:30
    client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-08-01T08:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )

    # 7. Query slots - 08:00-08:30 should also be removed (leaving 2 slots)
    avail_resp = client.get("/available-appointments?date=2026-08-01&specialistId=" + spec_id)
    avail_data = avail_resp.json()[0]
    slots = avail_data["availableSlots"]
    assert len(slots) == 2
    start_times = [s["startTime"] for s in slots]
    assert not any("08:00:00" in t for t in start_times)
    assert not any("09:00:00" in t for t in start_times)
