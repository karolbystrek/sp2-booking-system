from fastapi import status

def test_schedule_management(client):
    # 1. Register Specialist
    spec_payload = {
        "email": "spec2@example.com",
        "password": "password123",
        "first_name": "Anna",
        "last_name": "Nowak",
        "role": "Specialist",
        "specialist_details": {
            "specialization": "Dermatolog",
            "default_appointment_duration_minutes": 30,
            "office_address": "Office A"
        }
    }
    client.post("/auth/register", json=spec_payload)
    login_resp = client.post("/auth/login", json={"email": "spec2@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    # 2. Get specialist ID
    me_resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    spec_id = me_resp.json()["user_id"]

    # 3. Add availability block
    block_payload = {
        "start_time": "2026-06-01T08:00:00",
        "end_time": "2026-06-01T12:00:00",
        "block_type": "AVAILABLE"
    }
    resp = client.post(
        f"/specialists/{spec_id}/schedule/blocks",
        json=block_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == status.HTTP_201_CREATED
    block_id = resp.json()["block_id"]

    # 4. Try to add overlapping block of the same type - should fail
    resp_overlap = client.post(
        f"/specialists/{spec_id}/schedule/blocks",
        json={
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T14:00:00",
            "block_type": "AVAILABLE"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_overlap.status_code == status.HTTP_409_CONFLICT

    # 5. Try to add invalid times block (end before start) - should fail
    resp_invalid = client.post(
        f"/specialists/{spec_id}/schedule/blocks",
        json={
            "start_time": "2026-06-01T15:00:00",
            "end_time": "2026-06-01T14:00:00",
            "block_type": "AVAILABLE"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_invalid.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 6. Retrieve schedule
    resp_list = client.get(
        f"/specialists/{spec_id}/schedule",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert len(resp_list.json()) == 1
    assert resp_list.json()[0]["block_id"] == block_id

    # 7. Delete block
    resp_del = client.delete(
        f"/specialists/{spec_id}/schedule/blocks/{block_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_del.status_code == status.HTTP_204_NO_CONTENT
