"""
Shared test fixtures for the SP2 Booking System test suite.
Provides in-memory database, FastAPI TestClient, and authentication helpers.
"""
import sqlite3
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, get_db, generate_uuid, utcnow
from app.modules.identity.service import hash_password, create_access_token
from app.event_bus import EventBus


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    """Provides a fresh in-memory SQLite connection with the full schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    # Re-use the same DDL from init_db but against our in-memory conn
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS specialists (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE REFERENCES users(id),
            bio TEXT,
            office_location TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS roles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS user_roles (
            user_id TEXT NOT NULL REFERENCES users(id),
            role_id TEXT NOT NULL REFERENCES roles(id),
            assigned_at TEXT NOT NULL,
            PRIMARY KEY (user_id, role_id)
        );

        CREATE TABLE IF NOT EXISTS specializations (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS specialist_specializations (
            specialist_id TEXT NOT NULL,
            specialization_code TEXT NOT NULL REFERENCES specializations(code),
            PRIMARY KEY (specialist_id, specialization_code)
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id TEXT PRIMARY KEY,
            specialist_id TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS time_slots (
            id TEXT PRIMARY KEY,
            schedule_id TEXT NOT NULL REFERENCES schedules(id),
            specialist_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'AVAILABLE',
            slot_type TEXT NOT NULL DEFAULT 'STANDARD',
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS slot_blocks (
            id TEXT PRIMARY KEY,
            time_slot_id TEXT NOT NULL REFERENCES time_slots(id),
            reason TEXT NOT NULL,
            blocked_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reservations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            specialist_id TEXT NOT NULL,
            time_slot_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'CONFIRMED',
            notes TEXT,
            cancellation_reason TEXT,
            cancelled_by TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (specialist_id, time_slot_id)
        );

        CREATE TABLE IF NOT EXISTS reservation_history (
            id TEXT PRIMARY KEY,
            reservation_id TEXT NOT NULL REFERENCES reservations(id),
            action TEXT NOT NULL,
            performed_by TEXT NOT NULL,
            performed_role TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS outbox (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            published_at TEXT
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            recipient_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            type TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            retry_count INTEGER NOT NULL DEFAULT 0,
            sent_at TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notification_templates (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            channel TEXT NOT NULL,
            subject TEXT,
            body_template TEXT NOT NULL,
            UNIQUE (type, channel)
        );

        CREATE TABLE IF NOT EXISTS user_notification_preferences (
            user_id TEXT PRIMARY KEY,
            email_enabled INTEGER NOT NULL DEFAULT 1,
            push_enabled INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_by TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conflict_exceptions (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            max_overlapping INTEGER NOT NULL DEFAULT 2,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            performed_by TEXT NOT NULL,
            performed_role TEXT,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            details TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reservations_user_status ON reservations(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_reservations_specialist ON reservations(specialist_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_reservations_slot ON reservations(time_slot_id);
        CREATE INDEX IF NOT EXISTS idx_time_slots_search ON time_slots(specialist_id, start_time, status);
        CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_history_reservation ON reservation_history(reservation_id, created_at);
    """)
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Seed data helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_roles(db):
    """Insert the three standard roles."""
    now = utcnow()
    role_user_id = generate_uuid()
    role_specialist_id = generate_uuid()
    role_admin_id = generate_uuid()

    db.execute("INSERT INTO roles (id, name) VALUES (?, 'USER')", (role_user_id,))
    db.execute("INSERT INTO roles (id, name) VALUES (?, 'SPECIALIST')", (role_specialist_id,))
    db.execute("INSERT INTO roles (id, name) VALUES (?, 'ADMINISTRATOR')", (role_admin_id,))
    db.commit()
    return {"USER": role_user_id, "SPECIALIST": role_specialist_id, "ADMINISTRATOR": role_admin_id}


@pytest.fixture()
def seed_users(db, seed_roles):
    """Create test users for all roles and return their IDs."""
    now = utcnow()
    roles = seed_roles

    # Regular user
    user_id = generate_uuid()
    db.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (user_id, "test.user@email.com", "Test User", "+48111111111", hash_password("user123"), now, now),
    )
    db.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
               (user_id, roles["USER"], now))

    # Second regular user
    user2_id = generate_uuid()
    db.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (user2_id, "test.user2@email.com", "Test User 2", "+48111111112", hash_password("user123"), now, now),
    )
    db.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
               (user2_id, roles["USER"], now))

    # Admin user
    admin_id = generate_uuid()
    db.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (admin_id, "admin@booking.com", "Admin User", "+48100000001", hash_password("admin123"), now, now),
    )
    db.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
               (admin_id, roles["ADMINISTRATOR"], now))

    # Specialist user
    spec_user_id = generate_uuid()
    db.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (spec_user_id, "dr.smith@clinic.com", "Dr. Adam Smith", "+48300000001", hash_password("spec123"), now, now),
    )
    db.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
               (spec_user_id, roles["SPECIALIST"], now))

    # Specialist profile
    spec_id = generate_uuid()
    db.execute(
        "INSERT INTO specialists (id, user_id, bio, office_location, created_at) VALUES (?, ?, ?, ?, ?)",
        (spec_id, spec_user_id, "Cardiologist with 15 years of experience", "Room 101", now),
    )

    # Second specialist user
    spec2_user_id = generate_uuid()
    db.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (spec2_user_id, "dr.jones@clinic.com", "Dr. Maria Jones", "+48300000002", hash_password("spec123"), now, now),
    )
    db.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
               (spec2_user_id, roles["SPECIALIST"], now))

    spec2_id = generate_uuid()
    db.execute(
        "INSERT INTO specialists (id, user_id, bio, office_location, created_at) VALUES (?, ?, ?, ?, ?)",
        (spec2_id, spec2_user_id, "Neurologist", "Room 205", now),
    )

    # Inactive user
    inactive_user_id = generate_uuid()
    db.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'INACTIVE', ?, ?)",
        (inactive_user_id, "inactive@email.com", "Inactive User", None, hash_password("user123"), now, now),
    )
    db.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
               (inactive_user_id, roles["USER"], now))

    db.commit()

    return {
        "user_id": user_id,
        "user2_id": user2_id,
        "admin_id": admin_id,
        "spec_user_id": spec_user_id,
        "spec_id": spec_id,
        "spec2_user_id": spec2_user_id,
        "spec2_id": spec2_id,
        "inactive_user_id": inactive_user_id,
    }


@pytest.fixture()
def seed_specializations(db, seed_users):
    """Create specializations and link them to specialists."""
    db.execute("INSERT INTO specializations (code, name) VALUES ('cardiology', 'Cardiology')")
    db.execute("INSERT INTO specializations (code, name) VALUES ('neurology', 'Neurology')")
    db.execute("INSERT INTO specializations (code, name) VALUES ('dermatology', 'Dermatology')")

    db.execute("INSERT INTO specialist_specializations (specialist_id, specialization_code) VALUES (?, 'cardiology')",
               (seed_users["spec_id"],))
    db.execute("INSERT INTO specialist_specializations (specialist_id, specialization_code) VALUES (?, 'neurology')",
               (seed_users["spec2_id"],))
    db.commit()
    return seed_users


@pytest.fixture()
def seed_schedules(db, seed_specializations):
    """Create schedules and time slots for specialists."""
    now = utcnow()
    users = seed_specializations

    schedule1_id = generate_uuid()
    db.execute(
        "INSERT INTO schedules (id, specialist_id, valid_from, is_active, created_at, updated_at) VALUES (?, ?, '2026-06-01', 1, ?, ?)",
        (schedule1_id, users["spec_id"], now, now),
    )

    schedule2_id = generate_uuid()
    db.execute(
        "INSERT INTO schedules (id, specialist_id, valid_from, is_active, created_at, updated_at) VALUES (?, ?, '2026-06-01', 1, ?, ?)",
        (schedule2_id, users["spec2_id"], now, now),
    )

    # Generate future time slots
    base_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    slot_ids = []
    for day_offset in range(1, 8):
        day = base_date + timedelta(days=day_offset)
        if day.weekday() >= 5:
            continue
        for hour in range(9, 13):
            slot_id = generate_uuid()
            start = day.replace(hour=hour, minute=0)
            end = day.replace(hour=hour, minute=30)
            db.execute(
                "INSERT INTO time_slots (id, schedule_id, specialist_id, start_time, end_time, status, slot_type, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'AVAILABLE', 'STANDARD', 1, ?, ?)",
                (slot_id, schedule1_id, users["spec_id"], start.isoformat(), end.isoformat(), now, now),
            )
            slot_ids.append(slot_id)

            slot2_id = generate_uuid()
            db.execute(
                "INSERT INTO time_slots (id, schedule_id, specialist_id, start_time, end_time, status, slot_type, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'AVAILABLE', 'STANDARD', 1, ?, ?)",
                (slot2_id, schedule2_id, users["spec2_id"], start.isoformat(), end.isoformat(), now, now),
            )

    db.commit()

    users["schedule1_id"] = schedule1_id
    users["schedule2_id"] = schedule2_id
    users["slot_ids"] = slot_ids
    return users


@pytest.fixture()
def seed_booking_rules(db, seed_users):
    """Insert default booking rules into system_config."""
    now = utcnow()
    db.execute(
        "INSERT INTO system_config (key, value, description, updated_by, updated_at) VALUES ('booking_rules', ?, 'Global booking rules', ?, ?)",
        ('{"minCancellationHours": 24, "maxAdvanceBookingDays": 90, "maxReservationsPerUser": 5}', seed_users["admin_id"], now),
    )
    db.commit()
    return seed_users


@pytest.fixture()
def seed_full(db, seed_schedules, seed_booking_rules):
    """Full seed: roles + users + specializations + schedules + booking rules."""
    return seed_schedules


# ---------------------------------------------------------------------------
# Event bus fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def fresh_event_bus():
    """Returns a fresh EventBus instance to avoid cross-test pollution."""
    return EventBus()


# ---------------------------------------------------------------------------
# FastAPI TestClient fixtures
# ---------------------------------------------------------------------------

def _override_db(conn):
    """Create a dependency override that yields the given connection."""
    def _get_db_override():
        yield conn
    return _get_db_override


@pytest.fixture()
def client(db, seed_full):
    """TestClient with DB overridden to in-memory. Returns (client, seed_data)."""
    app.dependency_overrides[get_db] = _override_db(db)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, seed_full
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth token helpers
# ---------------------------------------------------------------------------

def make_user_token(user_id: str, roles: list[str] | None = None) -> str:
    """Generate a JWT token for testing."""
    return create_access_token(user_id, roles or ["USER"])


def make_admin_token(admin_id: str) -> str:
    return create_access_token(admin_id, ["ADMINISTRATOR"])


def make_specialist_token(spec_user_id: str) -> str:
    return create_access_token(spec_user_id, ["SPECIALIST"])


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
