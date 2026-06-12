import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from src.shared.security import hash_password

DATABASE_PATH = Path(__file__).resolve().parents[2] / "booking.sqlite3"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def write_audit_log(
    connection: sqlite3.Connection,
    actor_id: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO audit_logs (id, actor_id, event_type, entity_type, entity_id, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(),
            actor_id,
            event_type,
            entity_type,
            entity_id,
            json.dumps(payload or {}),
            now_iso(),
        ),
    )


def init_database() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA_SQL)
        seed_database(connection)


def seed_database(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return

    admin_id = new_id()
    patient_id = new_id()
    specialist_user_id = new_id()
    role_ids = {name: new_id() for name in ["ADMIN", "PATIENT", "SPECIALIST"]}

    users = [
        (admin_id, "admin@example.com", "Admin", "User", "admin123"),
        (patient_id, "patient@example.com", "Patient", "User", "patient123"),
        (specialist_user_id, "specialist@example.com", "Specialist", "User", "specialist123"),
    ]
    for user_id, email, first_name, last_name, password in users:
        connection.execute(
            """
            INSERT INTO users (id, email, password_hash, first_name, last_name, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)
            """,
            (user_id, email, hash_password(password), first_name, last_name, now_iso()),
        )

    for role_name, role_id in role_ids.items():
        connection.execute("INSERT INTO roles (id, name) VALUES (?, ?)", (role_id, role_name))

    assignments = [
        (admin_id, "ADMIN"),
        (patient_id, "PATIENT"),
        (specialist_user_id, "SPECIALIST"),
    ]
    for user_id, role_name in assignments:
        connection.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_ids[role_name]),
        )

    specialist_id = new_id()
    schedule_id = new_id()
    connection.execute(
        "INSERT INTO specialists (id, user_id, specialization, active) VALUES (?, ?, ?, 1)",
        (specialist_id, specialist_user_id, "Cardiology"),
    )
    connection.execute(
        "INSERT INTO schedules (id, specialist_id, version, updated_at) VALUES (?, ?, 1, ?)",
        (schedule_id, specialist_id, now_iso()),
    )
    connection.execute(
        """
        INSERT INTO availability_slots (id, schedule_id, day_of_week, start_time, end_time)
        VALUES (?, ?, 1, '09:00', '17:00')
        """,
        (new_id(), schedule_id),
    )

    seed_time_slots(connection, specialist_id)
    connection.execute(
        """
        INSERT INTO booking_policies (
            id, max_active_reservations, cancellation_window_hours, active_from, active_to
        )
        VALUES (?, 3, 24, ?, NULL)
        """,
        (new_id(), now_iso()),
    )


def seed_time_slots(connection: sqlite3.Connection, specialist_id: str) -> None:
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    first_monday = today + timedelta(days=days_until_monday or 7)

    for day_offset in range(5):
        slot_date = first_monday + timedelta(days=day_offset)
        for hour in range(9, 17):
            start_at = datetime.combine(slot_date, time(hour, 0), tzinfo=timezone.utc)
            end_at = start_at + timedelta(hours=1)
            connection.execute(
                """
                INSERT INTO time_slots (id, specialist_id, start_at, end_at, status, version)
                VALUES (?, ?, ?, ?, 'AVAILABLE', 1)
                """,
                (new_id(), specialist_id, start_at.isoformat(), end_at.isoformat()),
            )


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS specialists (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id),
    specialization TEXT NOT NULL,
    active INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    specialist_id TEXT NOT NULL UNIQUE REFERENCES specialists(id),
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS availability_slots (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedule_exceptions (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS time_slots (
    id TEXT PRIMARY KEY,
    specialist_id TEXT NOT NULL REFERENCES specialists(id),
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    specialist_id TEXT NOT NULL REFERENCES specialists(id),
    slot_id TEXT NOT NULL REFERENCES time_slots(id),
    status TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    cancelled_at TEXT,
    version INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_active_slot_reservation
ON reservations(slot_id)
WHERE status IN ('CREATED', 'CONFIRMED');

CREATE TABLE IF NOT EXISTS booking_policies (
    id TEXT PRIMARY KEY,
    max_active_reservations INTEGER NOT NULL,
    cancellation_window_hours INTEGER NOT NULL,
    active_from TEXT NOT NULL,
    active_to TEXT
);

CREATE TABLE IF NOT EXISTS conflict_exceptions (
    id TEXT PRIMARY KEY,
    specialist_id TEXT REFERENCES specialists(id),
    slot_id TEXT REFERENCES time_slots(id),
    reason TEXT NOT NULL,
    active_from TEXT NOT NULL,
    active_to TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    actor_id TEXT REFERENCES users(id),
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_reservations_user_status ON reservations(user_id, status);
CREATE INDEX IF NOT EXISTS ix_reservations_slot ON reservations(slot_id);
CREATE INDEX IF NOT EXISTS ix_reservations_created_at ON reservations(created_at);
CREATE INDEX IF NOT EXISTS ix_time_slots_specialist_start ON time_slots(specialist_id, start_at);
CREATE INDEX IF NOT EXISTS ix_time_slots_status_start ON time_slots(status, start_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
"""
