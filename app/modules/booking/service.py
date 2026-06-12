import sqlite3
import json
from datetime import datetime, timezone

from app.database import generate_uuid, utcnow
from app.event_bus import event_bus


def get_booking_rules(conn: sqlite3.Connection) -> dict:
    defaults = {
        "minCancellationHours": 24,
        "maxAdvanceBookingDays": 90,
        "maxReservationsPerUser": 5,
    }
    row = conn.execute(
        "SELECT value FROM system_config WHERE key = 'booking_rules'"
    ).fetchone()
    if row:
        return json.loads(row["value"])
    return defaults


def check_conflict_exceptions(conn: sqlite3.Connection, specialist_id: str, time_slot_id: str) -> bool:
    """Returns True if an active conflict exception allows overlapping bookings."""
    slot = conn.execute("SELECT slot_type FROM time_slots WHERE id = ?", (time_slot_id,)).fetchone()
    if not slot:
        return False

    if slot["slot_type"] == "GROUP":
        exception = conn.execute(
            "SELECT * FROM conflict_exceptions WHERE type = 'GROUP_VISIT' AND is_active = 1"
        ).fetchone()
        if exception:
            booked_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM reservations WHERE time_slot_id = ? AND status NOT IN ('CANCELLED_BY_USER', 'CANCELLED_BY_SPECIALIST')",
                (time_slot_id,),
            ).fetchone()["cnt"]
            return booked_count < exception["max_overlapping"]

    emergency_exception = conn.execute(
        "SELECT * FROM conflict_exceptions WHERE type = 'EMERGENCY' AND is_active = 1"
    ).fetchone()
    if emergency_exception and slot["slot_type"] == "EMERGENCY":
        return True

    return False


def create_reservation(conn: sqlite3.Connection, user_id: str, specialist_id: str,
                       time_slot_id: str, notes: str | None = None) -> dict:
    slot = conn.execute(
        "SELECT * FROM time_slots WHERE id = ? AND specialist_id = ?",
        (time_slot_id, specialist_id),
    ).fetchone()
    if not slot:
        raise ValueError("Slot not found")

    if slot["status"] != "AVAILABLE":
        has_exception = check_conflict_exceptions(conn, specialist_id, time_slot_id)
        if not has_exception:
            alternatives = conn.execute(
                "SELECT id, start_time, end_time FROM time_slots WHERE specialist_id = ? AND status = 'AVAILABLE' ORDER BY start_time LIMIT 3",
                (specialist_id,),
            ).fetchall()
            raise ConflictError(
                "Slot is not available",
                [{"slotId": a["id"], "startTime": a["start_time"], "endTime": a["end_time"]} for a in alternatives],
            )

    rules = get_booking_rules(conn)

    user_reservation_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM reservations WHERE user_id = ? AND status IN ('CONFIRMED', 'PENDING')",
        (user_id,),
    ).fetchone()["cnt"]
    if user_reservation_count >= rules["maxReservationsPerUser"]:
        raise ValueError(f"Maximum reservations limit ({rules['maxReservationsPerUser']}) reached")

    existing = conn.execute(
        "SELECT id FROM reservations WHERE specialist_id = ? AND time_slot_id = ? AND status NOT IN ('CANCELLED_BY_USER', 'CANCELLED_BY_SPECIALIST')",
        (specialist_id, time_slot_id),
    ).fetchone()
    if existing:
        has_exception = check_conflict_exceptions(conn, specialist_id, time_slot_id)
        if not has_exception:
            raise ConflictError("Slot already booked", [])

    reservation_id = generate_uuid()
    now = utcnow()

    conn.execute(
        """INSERT INTO reservations (id, user_id, specialist_id, time_slot_id, status, notes, version, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'CONFIRMED', ?, 1, ?, ?)""",
        (reservation_id, user_id, specialist_id, time_slot_id, notes, now, now),
    )

    # Record history
    history_id = generate_uuid()
    conn.execute(
        "INSERT INTO reservation_history (id, reservation_id, action, performed_by, performed_role, details, created_at) VALUES (?, ?, 'CREATED', ?, 'USER', ?, ?)",
        (history_id, reservation_id, user_id, json.dumps({"notes": notes}), now),
    )

    # Outbox event
    outbox_id = generate_uuid()
    conn.execute(
        "INSERT INTO outbox (id, event_type, aggregate_id, payload, status, created_at) VALUES (?, 'ReservationCreated', ?, ?, 'PENDING', ?)",
        (outbox_id, reservation_id, json.dumps({
            "reservationId": reservation_id,
            "userId": user_id,
            "specialistId": specialist_id,
            "timeSlotId": time_slot_id,
        }), now),
    )

    conn.execute(
        "UPDATE time_slots SET status = 'BOOKED', updated_at = ? WHERE id = ?",
        (now, time_slot_id),
    )

    conn.commit()

    event_bus.publish("ReservationCreated", {
        "reservationId": reservation_id,
        "userId": user_id,
        "specialistId": specialist_id,
        "timeSlotId": time_slot_id,
    })

    specialist = conn.execute(
        "SELECT u.name FROM specialists sp JOIN users u ON sp.user_id = u.id WHERE sp.id = ?",
        (specialist_id,),
    ).fetchone()

    return {
        "id": reservation_id,
        "userId": user_id,
        "specialistId": specialist_id,
        "timeSlotId": time_slot_id,
        "status": "CONFIRMED",
        "startTime": slot["start_time"],
        "endTime": slot["end_time"],
        "specialistName": specialist["name"] if specialist else "",
        "notes": notes,
        "createdAt": now,
    }


def get_user_reservations(conn: sqlite3.Connection, user_id: str,
                          status: str | None = None, page: int = 0, size: int = 20) -> dict:
    query = """
        SELECT r.*, ts.start_time, ts.end_time, u.name as specialist_name
        FROM reservations r
        JOIN time_slots ts ON r.time_slot_id = ts.id
        JOIN specialists sp ON r.specialist_id = sp.id
        JOIN users u ON sp.user_id = u.id
        WHERE r.user_id = ?
    """
    count_query = "SELECT COUNT(*) as total FROM reservations WHERE user_id = ?"
    params = [user_id]

    if status:
        query += " AND r.status = ?"
        count_query += " AND status = ?"
        params.append(status)

    total = conn.execute(count_query, params).fetchone()["total"]
    query += " ORDER BY r.created_at DESC LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    rows = conn.execute(query, params).fetchall()

    reservations = [
        {
            "id": r["id"],
            "userId": r["user_id"],
            "specialistId": r["specialist_id"],
            "timeSlotId": r["time_slot_id"],
            "status": r["status"],
            "startTime": r["start_time"],
            "endTime": r["end_time"],
            "specialistName": r["specialist_name"],
            "notes": r["notes"],
            "cancellationReason": r["cancellation_reason"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]

    total_pages = (total + size - 1) // size if total > 0 else 0
    return {"content": reservations, "page": page, "size": size,
            "totalElements": total, "totalPages": total_pages}


def get_reservation(conn: sqlite3.Connection, reservation_id: str) -> dict | None:
    row = conn.execute(
        """SELECT r.*, ts.start_time, ts.end_time, u.name as specialist_name
           FROM reservations r
           JOIN time_slots ts ON r.time_slot_id = ts.id
           JOIN specialists sp ON r.specialist_id = sp.id
           JOIN users u ON sp.user_id = u.id
           WHERE r.id = ?""",
        (reservation_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "specialistId": row["specialist_id"],
        "timeSlotId": row["time_slot_id"],
        "status": row["status"],
        "startTime": row["start_time"],
        "endTime": row["end_time"],
        "specialistName": row["specialist_name"],
        "notes": row["notes"],
        "cancellationReason": row["cancellation_reason"],
        "createdAt": row["created_at"],
    }


def cancel_reservation_by_user(conn: sqlite3.Connection, reservation_id: str, user_id: str) -> dict:
    reservation = conn.execute(
        "SELECT * FROM reservations WHERE id = ? AND user_id = ?",
        (reservation_id, user_id),
    ).fetchone()
    if not reservation:
        raise ValueError("Reservation not found")
    if reservation["status"] not in ("CONFIRMED", "PENDING"):
        raise ValueError("Reservation cannot be cancelled")

    rules = get_booking_rules(conn)
    slot = conn.execute("SELECT start_time FROM time_slots WHERE id = ?", (reservation["time_slot_id"],)).fetchone()
    if slot:
        slot_time = datetime.fromisoformat(slot["start_time"])
        hours_until = (slot_time - datetime.now(timezone.utc)).total_seconds() / 3600
        if hours_until < rules["minCancellationHours"]:
            raise ValueError(
                f"Cannot cancel less than {rules['minCancellationHours']} hours before appointment"
            )

    now = utcnow()
    conn.execute(
        "UPDATE reservations SET status = 'CANCELLED_BY_USER', cancelled_by = ?, updated_at = ? WHERE id = ?",
        (user_id, now, reservation_id),
    )
    conn.execute(
        "UPDATE time_slots SET status = 'AVAILABLE', updated_at = ? WHERE id = ?",
        (now, reservation["time_slot_id"]),
    )

    history_id = generate_uuid()
    conn.execute(
        "INSERT INTO reservation_history (id, reservation_id, action, performed_by, performed_role, created_at) VALUES (?, ?, 'CANCELLED', ?, 'USER', ?)",
        (history_id, reservation_id, user_id, now),
    )
    conn.commit()

    event_bus.publish("ReservationCancelled", {
        "reservationId": reservation_id,
        "userId": user_id,
        "specialistId": reservation["specialist_id"],
        "timeSlotId": reservation["time_slot_id"],
        "cancelledBy": "USER",
    })

    return get_reservation(conn, reservation_id)


def cancel_reservation_by_specialist(conn: sqlite3.Connection, reservation_id: str,
                                     specialist_id: str, reason: str) -> dict:
    reservation = conn.execute(
        "SELECT * FROM reservations WHERE id = ? AND specialist_id = ?",
        (reservation_id, specialist_id),
    ).fetchone()
    if not reservation:
        raise ValueError("Reservation not found")
    if reservation["status"] not in ("CONFIRMED", "PENDING"):
        raise ValueError("Reservation cannot be cancelled")

    now = utcnow()
    conn.execute(
        "UPDATE reservations SET status = 'CANCELLED_BY_SPECIALIST', cancellation_reason = ?, cancelled_by = ?, updated_at = ? WHERE id = ?",
        (reason, specialist_id, now, reservation_id),
    )
    conn.execute(
        "UPDATE time_slots SET status = 'AVAILABLE', updated_at = ? WHERE id = ?",
        (now, reservation["time_slot_id"]),
    )

    history_id = generate_uuid()
    conn.execute(
        "INSERT INTO reservation_history (id, reservation_id, action, performed_by, performed_role, details, created_at) VALUES (?, ?, 'CANCELLED', ?, 'SPECIALIST', ?, ?)",
        (history_id, reservation_id, specialist_id, json.dumps({"reason": reason}), now),
    )
    conn.commit()

    event_bus.publish("ReservationCancelled", {
        "reservationId": reservation_id,
        "userId": reservation["user_id"],
        "specialistId": specialist_id,
        "timeSlotId": reservation["time_slot_id"],
        "cancelledBy": "SPECIALIST",
        "reason": reason,
    })

    return get_reservation(conn, reservation_id)


def reschedule_reservation(conn: sqlite3.Connection, reservation_id: str,
                           specialist_id: str, new_time_slot_id: str) -> dict:
    reservation = conn.execute(
        "SELECT * FROM reservations WHERE id = ? AND specialist_id = ?",
        (reservation_id, specialist_id),
    ).fetchone()
    if not reservation:
        raise ValueError("Reservation not found")

    new_slot = conn.execute(
        "SELECT * FROM time_slots WHERE id = ? AND specialist_id = ? AND status = 'AVAILABLE'",
        (new_time_slot_id, specialist_id),
    ).fetchone()
    if not new_slot:
        raise ValueError("New slot is not available")

    now = utcnow()
    old_slot_id = reservation["time_slot_id"]

    conn.execute(
        "UPDATE reservations SET time_slot_id = ?, status = 'CONFIRMED', updated_at = ?, version = version + 1 WHERE id = ?",
        (new_time_slot_id, now, reservation_id),
    )
    conn.execute("UPDATE time_slots SET status = 'AVAILABLE', updated_at = ? WHERE id = ?", (now, old_slot_id))
    conn.execute("UPDATE time_slots SET status = 'BOOKED', updated_at = ? WHERE id = ?", (now, new_time_slot_id))

    history_id = generate_uuid()
    conn.execute(
        "INSERT INTO reservation_history (id, reservation_id, action, performed_by, performed_role, details, created_at) VALUES (?, ?, 'RESCHEDULED', ?, 'SPECIALIST', ?, ?)",
        (history_id, reservation_id, specialist_id,
         json.dumps({"oldSlotId": old_slot_id, "newSlotId": new_time_slot_id}), now),
    )
    conn.commit()

    event_bus.publish("ReservationRescheduled", {
        "reservationId": reservation_id,
        "userId": reservation["user_id"],
        "specialistId": specialist_id,
        "oldTimeSlotId": old_slot_id,
        "newTimeSlotId": new_time_slot_id,
    })

    return get_reservation(conn, reservation_id)


def get_reservation_history(conn: sqlite3.Connection, reservation_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM reservation_history WHERE reservation_id = ? ORDER BY created_at DESC",
        (reservation_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "reservationId": r["reservation_id"],
            "action": r["action"],
            "performedBy": r["performed_by"],
            "performedRole": r["performed_role"],
            "details": r["details"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]


def get_specialist_reservations(conn: sqlite3.Connection, specialist_id: str,
                                date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    query = """
        SELECT r.*, ts.start_time, ts.end_time, u.name as specialist_name
        FROM reservations r
        JOIN time_slots ts ON r.time_slot_id = ts.id
        JOIN specialists sp ON r.specialist_id = sp.id
        JOIN users u ON sp.user_id = u.id
        WHERE r.specialist_id = ?
    """
    params = [specialist_id]
    if date_from:
        query += " AND ts.start_time >= ?"
        params.append(date_from)
    if date_to:
        query += " AND ts.start_time <= ?"
        params.append(date_to + "T23:59:59")

    query += " ORDER BY ts.start_time ASC"
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": r["id"],
            "userId": r["user_id"],
            "specialistId": r["specialist_id"],
            "timeSlotId": r["time_slot_id"],
            "status": r["status"],
            "startTime": r["start_time"],
            "endTime": r["end_time"],
            "specialistName": r["specialist_name"],
            "notes": r["notes"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]


def get_all_reservations_admin(conn: sqlite3.Connection, specialist: str | None = None,
                               status: str | None = None,
                               date_from: str | None = None, date_to: str | None = None,
                               page: int = 0, size: int = 20) -> dict:
    query = """
        SELECT r.*, ts.start_time, ts.end_time, u.name as specialist_name
        FROM reservations r
        JOIN time_slots ts ON r.time_slot_id = ts.id
        JOIN specialists sp ON r.specialist_id = sp.id
        JOIN users u ON sp.user_id = u.id
        WHERE 1=1
    """
    count_query = "SELECT COUNT(*) as total FROM reservations r JOIN time_slots ts ON r.time_slot_id = ts.id WHERE 1=1"
    params = []

    if specialist:
        query += " AND r.specialist_id = ?"
        count_query += " AND r.specialist_id = ?"
        params.append(specialist)
    if status:
        query += " AND r.status = ?"
        count_query += " AND r.status = ?"
        params.append(status)
    if date_from:
        query += " AND ts.start_time >= ?"
        count_query += " AND ts.start_time >= ?"
        params.append(date_from)
    if date_to:
        query += " AND ts.start_time <= ?"
        count_query += " AND ts.start_time <= ?"
        params.append(date_to + "T23:59:59")

    total = conn.execute(count_query, params).fetchone()["total"]
    query += " ORDER BY r.created_at DESC LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    rows = conn.execute(query, params).fetchall()

    reservations = [
        {
            "id": r["id"],
            "userId": r["user_id"],
            "specialistId": r["specialist_id"],
            "timeSlotId": r["time_slot_id"],
            "status": r["status"],
            "startTime": r["start_time"],
            "endTime": r["end_time"],
            "specialistName": r["specialist_name"],
            "notes": r["notes"],
            "cancellationReason": r["cancellation_reason"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]

    total_pages = (total + size - 1) // size if total > 0 else 0
    return {"content": reservations, "page": page, "size": size,
            "totalElements": total, "totalPages": total_pages}


def resolve_conflict_admin(conn: sqlite3.Connection, reservation_id: str,
                           action: str, admin_id: str, reason: str | None = None) -> dict:
    reservation = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
    if not reservation:
        raise ValueError("Reservation not found")

    now = utcnow()
    if action == "CANCEL":
        conn.execute(
            "UPDATE reservations SET status = 'CANCELLED_BY_SPECIALIST', cancellation_reason = ?, cancelled_by = ?, updated_at = ? WHERE id = ?",
            (reason or "Resolved by admin", admin_id, now, reservation_id),
        )
        conn.execute(
            "UPDATE time_slots SET status = 'AVAILABLE', updated_at = ? WHERE id = ?",
            (now, reservation["time_slot_id"]),
        )
    elif action == "CONFIRM":
        conn.execute(
            "UPDATE reservations SET status = 'CONFIRMED', updated_at = ? WHERE id = ?",
            (now, reservation_id),
        )

    history_id = generate_uuid()
    conn.execute(
        "INSERT INTO reservation_history (id, reservation_id, action, performed_by, performed_role, details, created_at) VALUES (?, ?, 'CONFLICT_RESOLVED', ?, 'ADMINISTRATOR', ?, ?)",
        (history_id, reservation_id, admin_id, json.dumps({"action": action, "reason": reason}), now),
    )
    conn.commit()
    return get_reservation(conn, reservation_id)


class ConflictError(Exception):
    def __init__(self, message: str, alternatives: list[dict]):
        self.message = message
        self.alternatives = alternatives
        super().__init__(message)
