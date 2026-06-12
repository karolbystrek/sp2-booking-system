import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "booking_system.db"


def get_db():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        -- Identity module tables
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

        -- Availability module tables
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

        -- Booking module tables
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

        -- Notification module tables
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

        -- Administration module tables
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

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_reservations_user_status ON reservations(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_reservations_specialist ON reservations(specialist_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_reservations_slot ON reservations(time_slot_id);
        CREATE INDEX IF NOT EXISTS idx_time_slots_search ON time_slots(specialist_id, start_time, status);
        CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_history_reservation ON reservation_history(reservation_id, created_at);
    """)

    conn.commit()
    conn.close()
