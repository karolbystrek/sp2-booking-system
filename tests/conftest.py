from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.shared import database
from src.shared.security import create_access_token, hash_password


@pytest.fixture()
def isolated_database(tmp_path, monkeypatch):
    """Create a freshly seeded SQLite database for every test."""
    database_path = tmp_path / "booking.sqlite3"
    monkeypatch.setattr(database, "DATABASE_PATH", database_path)
    database.init_database()
    return database


@pytest.fixture()
def client(isolated_database):
    """Exercise the real FastAPI routing and dependency stack."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def user_factory(isolated_database):
    def load_user(email: str) -> dict:
        with isolated_database.get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            assert row is not None, f"Seeded user {email!r} does not exist"
            user = dict(row)
            roles = connection.execute(
                """
                SELECT r.name
                FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = ?
                ORDER BY r.name
                """,
                (user["id"],),
            ).fetchall()
        user["roles"] = [role["name"] for role in roles]
        return user

    return load_user


@pytest.fixture()
def new_user_factory(isolated_database, user_factory):
    def create_user(email: str, roles: tuple[str, ...] = ("PATIENT",)) -> dict:
        user_id = str(uuid4())
        with isolated_database.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    id, email, password_hash, first_name, last_name, status, created_at
                ) VALUES (?, ?, ?, 'Test', 'User', 'ACTIVE', ?)
                """,
                (
                    user_id,
                    email,
                    hash_password("test-password"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            for role_name in roles:
                role_id = connection.execute(
                    "SELECT id FROM roles WHERE name = ?", (role_name,)
                ).fetchone()["id"]
                connection.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    (user_id, role_id),
                )
        return user_factory(email)

    return create_user


@pytest.fixture()
def patient(user_factory):
    return user_factory("patient@example.com")


@pytest.fixture()
def specialist(user_factory):
    return user_factory("specialist@example.com")


@pytest.fixture()
def admin(user_factory):
    return user_factory("admin@example.com")


@pytest.fixture()
def auth_headers():
    def headers_for(user: dict) -> dict[str, str]:
        token = create_access_token(user["id"], user["roles"])
        return {"Authorization": f"Bearer {token}"}

    return headers_for


@pytest.fixture()
def slot_factory(isolated_database):
    def create_slot(
        *,
        start_at: datetime | None = None,
        duration_minutes: int = 60,
        status: str = "AVAILABLE",
        specialist_id: str | None = None,
    ) -> dict:
        start_at = start_at or datetime.now(timezone.utc) + timedelta(days=7)
        end_at = start_at + timedelta(minutes=duration_minutes)
        slot_id = str(uuid4())

        with isolated_database.get_connection() as connection:
            if specialist_id is None:
                specialist_id = connection.execute(
                    "SELECT id FROM specialists LIMIT 1"
                ).fetchone()["id"]
            connection.execute(
                """
                INSERT INTO time_slots (
                    id, specialist_id, start_at, end_at, status, version
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    slot_id,
                    specialist_id,
                    start_at.isoformat(),
                    end_at.isoformat(),
                    status,
                ),
            )

        return {
            "id": slot_id,
            "specialist_id": specialist_id,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "status": status,
        }

    return create_slot


@pytest.fixture()
def book_slot(client, auth_headers):
    def book(user: dict, slot: dict, *, expected_status: int = 201):
        response = client.post(
            "/api/v1/reservations",
            json={"slotId": slot["id"]},
            headers=auth_headers(user),
        )
        assert response.status_code == expected_status, response.text
        return response

    return book

