import pytest

from src.shared.security import create_access_token


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def test_health_endpoint_is_available(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_returns_token_and_user_roles(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "patient@example.com", "password": "patient123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tokenType"] == "bearer"
    assert payload["accessToken"]
    assert payload["user"]["roles"] == ["PATIENT"]


@pytest.mark.parametrize(
    "email,password",
    [
        ("patient@example.com", "wrong-password"),
        ("missing@example.com", "patient123"),
    ],
)
def test_login_rejects_invalid_credentials(client, email, password):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert error_code(response) == "INVALID_CREDENTIALS"


def test_current_user_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert error_code(response) == "INVALID_TOKEN"


def test_current_user_returns_authenticated_identity(
    client, patient, auth_headers
):
    response = client.get("/api/v1/auth/me", headers=auth_headers(patient))

    assert response.status_code == 200
    assert response.json()["email"] == "patient@example.com"
    assert response.json()["roles"] == ["PATIENT"]


def test_patient_cannot_list_users(client, patient, auth_headers):
    response = client.get("/api/v1/users", headers=auth_headers(patient))

    assert response.status_code == 403
    assert error_code(response) == "FORBIDDEN"


def test_admin_can_list_users_with_roles(client, admin, auth_headers):
    response = client.get("/api/v1/users", headers=auth_headers(admin))

    assert response.status_code == 200
    users = response.json()
    assert {user["email"] for user in users} == {
        "admin@example.com",
        "patient@example.com",
        "specialist@example.com",
    }
    assert all(user["roles"] for user in users)


def test_public_specialist_directory_returns_seeded_specialist(client):
    list_response = client.get("/api/v1/specialists")

    assert list_response.status_code == 200
    specialists = list_response.json()
    assert len(specialists) == 1
    assert specialists[0]["specialization"] == "Cardiology"

    detail_response = client.get(
        f"/api/v1/specialists/{specialists[0]['id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["email"] == "specialist@example.com"


def test_missing_specialist_returns_domain_error(client):
    response = client.get("/api/v1/specialists/missing-id")

    assert response.status_code == 404
    assert error_code(response) == "SPECIALIST_NOT_FOUND"


def test_admin_can_replace_user_roles(client, patient, admin, auth_headers):
    response = client.put(
        f"/api/v1/users/{patient['id']}/roles",
        json={"roles": ["PATIENT", "SPECIALIST"]},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["roles"] == ["PATIENT", "SPECIALIST"]


def test_assigning_unknown_role_is_rejected(
    client, patient, admin, auth_headers
):
    response = client.put(
        f"/api/v1/users/{patient['id']}/roles",
        json={"roles": ["PATIENT", "UNKNOWN"]},
        headers=auth_headers(admin),
    )

    assert response.status_code == 400
    assert error_code(response) == "UNKNOWN_ROLE"


def test_admin_gets_domain_error_for_missing_user(
    client, admin, auth_headers
):
    response = client.get(
        "/api/v1/users/missing-user", headers=auth_headers(admin)
    )

    assert response.status_code == 404
    assert error_code(response) == "USER_NOT_FOUND"


def test_token_for_missing_user_is_rejected(client):
    token = create_access_token("missing-user", ["PATIENT"])

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert error_code(response) == "USER_NOT_FOUND"


def test_assigning_roles_to_missing_user_is_rejected(
    client, admin, auth_headers
):
    response = client.put(
        "/api/v1/users/missing-user/roles",
        json={"roles": ["PATIENT"]},
        headers=auth_headers(admin),
    )

    assert response.status_code == 404
    assert error_code(response) == "USER_NOT_FOUND"

