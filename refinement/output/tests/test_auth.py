from fastapi import status

def test_register_and_login(client):
    # 1. Register Patient
    reg_payload = {
        "email": "testpatient@example.com",
        "password": "securepassword",
        "first_name": "Test",
        "last_name": "Patient",
        "role": "Patient"
    }
    response = client.post("/auth/register", json=reg_payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "testpatient@example.com"
    assert data["roles"][0]["name"] == "Patient"

    # 2. Register Duplicate Patient
    response = client.post("/auth/register", json=reg_payload)
    assert response.status_code == status.HTTP_409_CONFLICT

    # 3. Login
    login_payload = {
        "email": "testpatient@example.com",
        "password": "securepassword"
    }
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_200_OK
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # 4. Get Profile
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    profile = response.json()
    assert profile["email"] == "testpatient@example.com"

def test_role_authorization(client):
    # 1. Register Patient and Specialist
    pat_payload = {
        "email": "pat@example.com",
        "password": "password123",
        "first_name": "Jan",
        "last_name": "Kowalski",
        "role": "Patient"
    }
    spec_payload = {
        "email": "spec@example.com",
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
    
    client.post("/auth/register", json=pat_payload)
    client.post("/auth/register", json=spec_payload)

    # 2. Login as Patient
    response = client.post("/auth/login", json={"email": "pat@example.com", "password": "password123"})
    pat_token = response.json()["access_token"]

    # 3. Login as Specialist
    response = client.post("/auth/login", json={"email": "spec@example.com", "password": "password123"})
    spec_token = response.json()["access_token"]

    # 4. Patient tries to access specialist endpoint (manage schedule) - should fail
    response = client.post(
        "/specialists/some-id/schedule/blocks", 
        json={"start_time": "2026-05-27T09:00:00", "end_time": "2026-05-27T17:00:00", "block_type": "AVAILABLE"},
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 5. Specialist accesses their own schedule - should succeed
    response = client.get("/users/me", headers={"Authorization": f"Bearer {spec_token}"})
    spec_id = response.json()["user_id"]
    
    response = client.post(
        f"/specialists/{spec_id}/schedule/blocks", 
        json={"start_time": "2026-05-27T09:00:00", "end_time": "2026-05-27T17:00:00", "block_type": "AVAILABLE"},
        headers={"Authorization": f"Bearer {spec_token}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
