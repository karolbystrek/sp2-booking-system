import sqlite3
from datetime import datetime, timedelta, timezone

from app.database import DATABASE_PATH, generate_uuid, utcnow
from app.modules.identity.service import hash_password


def seed_test_data():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    existing = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
    if existing > 0:
        conn.close()
        return

    now = utcnow()

    # Create roles
    role_user_id = generate_uuid()
    role_specialist_id = generate_uuid()
    role_admin_id = generate_uuid()

    conn.execute("INSERT INTO roles (id, name) VALUES (?, 'USER')", (role_user_id,))
    conn.execute("INSERT INTO roles (id, name) VALUES (?, 'SPECIALIST')", (role_specialist_id,))
    conn.execute("INSERT INTO roles (id, name) VALUES (?, 'ADMINISTRATOR')", (role_admin_id,))

    # Create test users
    admin_id = generate_uuid()
    conn.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (admin_id, "admin@booking.com", "Admin User", "+48100000001", hash_password("admin123"), now, now),
    )
    conn.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                 (admin_id, role_admin_id, now))

    user1_id = generate_uuid()
    conn.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (user1_id, "jan.kowalski@email.com", "Jan Kowalski", "+48200000001", hash_password("user123"), now, now),
    )
    conn.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                 (user1_id, role_user_id, now))

    user2_id = generate_uuid()
    conn.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (user2_id, "anna.nowak@email.com", "Anna Nowak", "+48200000002", hash_password("user123"), now, now),
    )
    conn.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                 (user2_id, role_user_id, now))

    # Create specialist users
    spec1_user_id = generate_uuid()
    conn.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (spec1_user_id, "dr.smith@clinic.com", "Dr. Adam Smith", "+48300000001", hash_password("spec123"), now, now),
    )
    conn.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                 (spec1_user_id, role_specialist_id, now))

    spec2_user_id = generate_uuid()
    conn.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (spec2_user_id, "dr.jones@clinic.com", "Dr. Maria Jones", "+48300000002", hash_password("spec123"), now, now),
    )
    conn.execute("INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                 (spec2_user_id, role_specialist_id, now))

    # Create specialist profiles
    spec1_id = generate_uuid()
    conn.execute(
        "INSERT INTO specialists (id, user_id, bio, office_location, created_at) VALUES (?, ?, ?, ?, ?)",
        (spec1_id, spec1_user_id, "Cardiologist with 15 years of experience", "Room 101, Main Building", now),
    )

    spec2_id = generate_uuid()
    conn.execute(
        "INSERT INTO specialists (id, user_id, bio, office_location, created_at) VALUES (?, ?, ?, ?, ?)",
        (spec2_id, spec2_user_id, "Neurologist specializing in headaches", "Room 205, Wing B", now),
    )

    # Create specializations
    conn.execute("INSERT INTO specializations (code, name) VALUES ('cardiology', 'Cardiology')")
    conn.execute("INSERT INTO specializations (code, name) VALUES ('neurology', 'Neurology')")
    conn.execute("INSERT INTO specializations (code, name) VALUES ('dermatology', 'Dermatology')")

    conn.execute("INSERT INTO specialist_specializations (specialist_id, specialization_code) VALUES (?, 'cardiology')", (spec1_id,))
    conn.execute("INSERT INTO specialist_specializations (specialist_id, specialization_code) VALUES (?, 'neurology')", (spec2_id,))

    # Create schedules and time slots for specialists
    schedule1_id = generate_uuid()
    conn.execute(
        "INSERT INTO schedules (id, specialist_id, valid_from, is_active, created_at, updated_at) VALUES (?, ?, ?, 1, ?, ?)",
        (schedule1_id, spec1_id, "2026-06-01", now, now),
    )

    schedule2_id = generate_uuid()
    conn.execute(
        "INSERT INTO schedules (id, specialist_id, valid_from, is_active, created_at, updated_at) VALUES (?, ?, ?, 1, ?, ?)",
        (schedule2_id, spec2_id, "2026-06-01", now, now),
    )

    # Generate time slots for the next 14 days
    base_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for day_offset in range(1, 15):
        day = base_date + timedelta(days=day_offset)
        if day.weekday() >= 5:  # Skip weekends
            continue

        for hour in range(9, 17):
            slot1_id = generate_uuid()
            start = day.replace(hour=hour, minute=0)
            end = day.replace(hour=hour, minute=30)
            conn.execute(
                "INSERT INTO time_slots (id, schedule_id, specialist_id, start_time, end_time, status, slot_type, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'AVAILABLE', 'STANDARD', 1, ?, ?)",
                (slot1_id, schedule1_id, spec1_id, start.isoformat(), end.isoformat(), now, now),
            )

            slot2_id = generate_uuid()
            conn.execute(
                "INSERT INTO time_slots (id, schedule_id, specialist_id, start_time, end_time, status, slot_type, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'AVAILABLE', 'STANDARD', 1, ?, ?)",
                (slot2_id, schedule2_id, spec2_id, start.isoformat(), end.isoformat(), now, now),
            )

    # Create default system config
    conn.execute(
        "INSERT INTO system_config (key, value, description, updated_by, updated_at) VALUES ('booking_rules', ?, 'Global booking rules', ?, ?)",
        ('{"minCancellationHours": 24, "maxAdvanceBookingDays": 90, "maxReservationsPerUser": 5}', admin_id, now),
    )

    # Create a conflict exception for group visits
    exception_id = generate_uuid()
    conn.execute(
        "INSERT INTO conflict_exceptions (id, type, description, max_overlapping, is_active, created_by, created_at) VALUES (?, 'GROUP_VISIT', 'Allow up to 5 patients for group therapy sessions', 5, 1, ?, ?)",
        (exception_id, admin_id, now),
    )

    conn.commit()
    conn.close()
