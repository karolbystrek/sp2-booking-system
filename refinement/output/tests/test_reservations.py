from fastapi import status

def test_reservations_and_limits(client):
    # 1. Register and Login Patient
    pat_payload = {
        "email": "respatient@example.com",
        "password": "securepassword",
        "first_name": "Test",
        "last_name": "Patient",
        "role": "Patient"
    }
    client.post("/auth/register", json=pat_payload)
    login_resp = client.post("/auth/login", json={"email": "respatient@example.com", "password": "securepassword"})
    pat_token = login_resp.json()["access_token"]
    pat_me = client.get("/users/me", headers={"Authorization": f"Bearer {pat_token}"})
    pat_id = pat_me.json()["user_id"]

    # 2. Register and Login Specialist
    spec_payload = {
        "email": "resspecialist@example.com",
        "password": "securepassword",
        "first_name": "Test",
        "last_name": "Specialist",
        "role": "Specialist",
        "specialist_details": {
            "specialization": "Kardiolog",
            "default_appointment_duration_minutes": 30,
            "office_address": "Office B"
        }
    }
    client.post("/auth/register", json=spec_payload)
    login_resp = client.post("/auth/login", json={"email": "resspecialist@example.com", "password": "securepassword"})
    spec_token = login_resp.json()["access_token"]
    spec_me = client.get("/users/me", headers={"Authorization": f"Bearer {spec_token}"})
    spec_id = spec_me.json()["user_id"]

    # 3. Create schedule for specialist: 2026-07-01 from 08:00 to 12:00
    client.post(
        f"/specialists/{spec_id}/schedule/blocks",
        json={
            "start_time": "2026-07-01T08:00:00",
            "end_time": "2026-07-01T12:00:00",
            "block_type": "AVAILABLE"
        },
        headers={"Authorization": f"Bearer {spec_token}"}
    )

    # 4. Book valid reservation (09:00 - 09:30)
    res_resp = client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-07-01T09:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    assert res_resp.status_code == status.HTTP_201_CREATED
    res_data = res_resp.json()
    assert res_data["status"] == "CONFIRMED"
    res_id1 = res_data["reservation_id"]

    # 5. Attempt duplicate booking (same specialist, same time) - should fail
    res_resp_dup = client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-07-01T09:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    assert res_resp_dup.status_code == status.HTTP_409_CONFLICT

    # 6. Attempt booking outside availability (e.g. 13:00) - should fail
    res_resp_out = client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-07-01T13:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    assert res_resp_out.status_code == status.HTTP_409_CONFLICT

    # 7. Book two more valid slots (10:00 and 11:00) to hit the 3 active limit
    client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-07-01T10:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-07-01T11:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )

    # 8. Try to book 4th active reservation - should fail
    res_resp_limit = client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-07-01T08:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    assert res_resp_limit.status_code == status.HTTP_409_CONFLICT

    # 9. Cancel first reservation
    cancel_resp = client.put(
        f"/reservations/{res_id1}/cancel",
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    assert cancel_resp.status_code == status.HTTP_200_OK
    assert cancel_resp.json()["status"] == "CANCELLED"

    # 10. Booking 4th now succeeds (because only 2 are active now)
    res_resp_limit2 = client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-07-01T08:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    assert res_resp_limit2.status_code == status.HTTP_201_CREATED
