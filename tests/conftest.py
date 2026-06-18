from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


@pytest.fixture()
def isolated_database(tmp_path, monkeypatch):
    """Give every test a freshly seeded SQLite database."""
    database = pytest.importorskip(
        "src.shared.database",
        reason="The code/e2/gpt implementation has not been integrated yet.",
    )
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "booking.sqlite3")
    database.init_database()
    return database


@pytest.fixture()
def user_factory(isolated_database):
    def load_user(email):
        with isolated_database.get_connection() as connection:
            user = dict(
                connection.execute(
                    "SELECT * FROM users WHERE email = ?", (email,)
                ).fetchone()
            )
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
def patient(user_factory):
    return user_factory("patient@example.com")


@pytest.fixture()
def specialist(user_factory):
    return user_factory("specialist@example.com")


@pytest.fixture()
def admin(user_factory):
    return user_factory("admin@example.com")


@pytest.fixture()
def slot_factory(isolated_database):
    def create_slot(start_at=None, duration_minutes=60, status="AVAILABLE"):
        start_at = start_at or datetime.now(timezone.utc) + timedelta(days=7)
        end_at = start_at + timedelta(minutes=duration_minutes)
        slot_id = str(uuid4())

        with isolated_database.get_connection() as connection:
            specialist_id = connection.execute(
                "SELECT id FROM specialists LIMIT 1"
            ).fetchone()["id"]
            connection.execute(
                """
                INSERT INTO time_slots (
                    id, specialist_id, start_at, end_at, status, version
                )
                VALUES (?, ?, ?, ?, ?, 1)
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
