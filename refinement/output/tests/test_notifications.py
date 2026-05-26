import time
from fastapi import status

def test_notification_logging_on_booking(client):
    # 1. Register Patient & Specialist
    pat_payload = {
        "email": "notifpatient@example.com",
        "password": "securepassword",
        "first_name": "Jan",
        "last_name": "Kowalski",
        "role": "Patient"
    }
    client.post("/auth/register", json=pat_payload)
    login_resp = client.post("/auth/login", json={"email": "notifpatient@example.com", "password": "securepassword"})
    pat_token = login_resp.json()["access_token"]
    pat_me = client.get("/users/me", headers={"Authorization": f"Bearer {pat_token}"})
    pat_id = pat_me.json()["user_id"]

    spec_payload = {
        "email": "notifspecialist@example.com",
        "password": "securepassword",
        "first_name": "Anna",
        "last_name": "Nowak",
        "role": "Specialist",
        "specialist_details": {
            "specialization": "Dermatolog",
            "default_appointment_duration_minutes": 30,
            "office_address": "Office E"
        }
    }
    client.post("/auth/register", json=spec_payload)
    login_resp = client.post("/auth/login", json={"email": "notifspecialist@example.com", "password": "securepassword"})
    spec_token = login_resp.json()["access_token"]
    spec_me = client.get("/users/me", headers={"Authorization": f"Bearer {spec_token}"})
    spec_id = spec_me.json()["user_id"]

    # 2. Add availability block for specialist
    client.post(
        f"/specialists/{spec_id}/schedule/blocks",
        json={
            "start_time": "2026-09-01T08:00:00",
            "end_time": "2026-09-01T12:00:00",
            "block_type": "AVAILABLE"
        },
        headers={"Authorization": f"Bearer {spec_token}"}
    )

    # Verify no notification logs exist initially
    logs_resp = client.get(f"/notifications?userId={pat_id}", headers={"Authorization": f"Bearer {pat_token}"})
    assert len(logs_resp.json()) == 0

    # 3. Book slot 09:00 - 09:30
    client.post(
        "/reservations",
        json={
            "patient_id": pat_id,
            "specialist_id": spec_id,
            "appointment_time": "2026-09-01T09:00:00",
            "duration_minutes": 30
        },
        headers={"Authorization": f"Bearer {pat_token}"}
    )

    # 4. Wait brief moment for async event dispatcher to process and log
    time.sleep(0.5)

    # 5. Query notifications log
    logs_resp = client.get(f"/notifications?userId={pat_id}", headers={"Authorization": f"Bearer {pat_token}"})
    assert logs_resp.status_code == status.HTTP_200_OK
    logs = logs_resp.json()
    assert len(logs) == 1
    assert logs[0]["recipient"] == "notifpatient@example.com"
    assert "Anna Nowak" in logs[0]["body"]
    assert "Jan Kowalski" in logs[0]["body"]
    assert "SENT" in logs[0]["status"]
