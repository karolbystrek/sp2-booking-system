import sqlite3
import json

from app.database import generate_uuid, utcnow
from app.event_bus import event_bus


def get_specialist_id_for_user(conn: sqlite3.Connection, user_id: str) -> str | None:
    row = conn.execute("SELECT id FROM specialists WHERE user_id = ?", (user_id,)).fetchone()
    return row["id"] if row else None


def search_available_slots(conn: sqlite3.Connection, specialization: str | None = None,
                           date_from: str | None = None, date_to: str | None = None,
                           time_from: str | None = None, time_to: str | None = None,
                           page: int = 0, size: int = 20) -> dict:
    query = """
        SELECT ts.id, ts.specialist_id, ts.start_time, ts.end_time, ts.status,
               u.name as specialist_name, ss.specialization_code
        FROM time_slots ts
        JOIN specialists sp ON ts.specialist_id = sp.id
        JOIN users u ON sp.user_id = u.id
        LEFT JOIN specialist_specializations ss ON sp.id = ss.specialist_id
        WHERE ts.status = 'AVAILABLE'
    """
    count_query = """
        SELECT COUNT(*) as total
        FROM time_slots ts
        JOIN specialists sp ON ts.specialist_id = sp.id
        LEFT JOIN specialist_specializations ss ON sp.id = ss.specialist_id
        WHERE ts.status = 'AVAILABLE'
    """
    params = []

    if specialization:
        query += " AND ss.specialization_code = ?"
        count_query += " AND ss.specialization_code = ?"
        params.append(specialization)

    if date_from:
        query += " AND ts.start_time >= ?"
        count_query += " AND ts.start_time >= ?"
        params.append(date_from)

    if date_to:
        query += " AND ts.start_time <= ?"
        count_query += " AND ts.start_time <= ?"
        params.append(date_to + "T23:59:59")

    if time_from:
        query += " AND substr(ts.start_time, 12, 5) >= ?"
        count_query += " AND substr(ts.start_time, 12, 5) >= ?"
        params.append(time_from)

    if time_to:
        query += " AND substr(ts.start_time, 12, 5) <= ?"
        count_query += " AND substr(ts.start_time, 12, 5) <= ?"
        params.append(time_to)

    total = conn.execute(count_query, params).fetchone()["total"]
    query += " ORDER BY ts.start_time ASC LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    rows = conn.execute(query, params).fetchall()

    slots = []
    for row in rows:
        slots.append({
            "slotId": row["id"],
            "specialistId": row["specialist_id"],
            "specialistName": row["specialist_name"],
            "specialization": row["specialization_code"],
            "startTime": row["start_time"],
            "endTime": row["end_time"],
            "status": row["status"],
        })

    total_pages = (total + size - 1) // size if total > 0 else 0
    return {
        "content": slots,
        "page": page,
        "size": size,
        "totalElements": total,
        "totalPages": total_pages,
    }


def get_specialist_slots(conn: sqlite3.Connection, specialist_id: str,
                         date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    query = """
        SELECT ts.id, ts.specialist_id, ts.start_time, ts.end_time, ts.status,
               u.name as specialist_name
        FROM time_slots ts
        JOIN specialists sp ON ts.specialist_id = sp.id
        JOIN users u ON sp.user_id = u.id
        WHERE ts.specialist_id = ? AND ts.status = 'AVAILABLE'
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
            "slotId": row["id"],
            "specialistId": row["specialist_id"],
            "specialistName": row["specialist_name"],
            "startTime": row["start_time"],
            "endTime": row["end_time"],
            "status": row["status"],
        }
        for row in rows
    ]


def get_schedule(conn: sqlite3.Connection, specialist_id: str) -> dict | None:
    schedule = conn.execute(
        "SELECT * FROM schedules WHERE specialist_id = ? AND is_active = 1",
        (specialist_id,),
    ).fetchone()
    if not schedule:
        return None

    slots = conn.execute(
        "SELECT * FROM time_slots WHERE schedule_id = ? ORDER BY start_time ASC",
        (schedule["id"],),
    ).fetchall()

    specialist = conn.execute("SELECT * FROM specialists WHERE id = ?", (specialist_id,)).fetchone()
    user = conn.execute("SELECT name FROM users WHERE id = ?", (specialist["user_id"],)).fetchone()

    return {
        "id": schedule["id"],
        "specialistId": specialist_id,
        "validFrom": schedule["valid_from"],
        "validTo": schedule["valid_to"],
        "isActive": bool(schedule["is_active"]),
        "slots": [
            {
                "slotId": s["id"],
                "specialistId": s["specialist_id"],
                "specialistName": user["name"],
                "startTime": s["start_time"],
                "endTime": s["end_time"],
                "status": s["status"],
            }
            for s in slots
        ],
    }


def create_slot(conn: sqlite3.Connection, specialist_id: str,
                start_time: str, end_time: str, slot_type: str = "STANDARD") -> dict:
    schedule = conn.execute(
        "SELECT id FROM schedules WHERE specialist_id = ? AND is_active = 1",
        (specialist_id,),
    ).fetchone()

    if not schedule:
        schedule_id = generate_uuid()
        now = utcnow()
        conn.execute(
            "INSERT INTO schedules (id, specialist_id, valid_from, is_active, created_at, updated_at) VALUES (?, ?, ?, 1, ?, ?)",
            (schedule_id, specialist_id, start_time[:10], now, now),
        )
    else:
        schedule_id = schedule["id"]

    slot_id = generate_uuid()
    now = utcnow()
    conn.execute(
        "INSERT INTO time_slots (id, schedule_id, specialist_id, start_time, end_time, status, slot_type, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'AVAILABLE', ?, 1, ?, ?)",
        (slot_id, schedule_id, specialist_id, start_time, end_time, slot_type, now, now),
    )
    conn.commit()

    specialist = conn.execute("SELECT user_id FROM specialists WHERE id = ?", (specialist_id,)).fetchone()
    user = conn.execute("SELECT name FROM users WHERE id = ?", (specialist["user_id"],)).fetchone()

    return {
        "slotId": slot_id,
        "specialistId": specialist_id,
        "specialistName": user["name"],
        "startTime": start_time,
        "endTime": end_time,
        "status": "AVAILABLE",
    }


def update_slot(conn: sqlite3.Connection, slot_id: str, specialist_id: str,
                start_time: str | None = None, end_time: str | None = None,
                new_status: str | None = None) -> dict | None:
    slot = conn.execute(
        "SELECT * FROM time_slots WHERE id = ? AND specialist_id = ?",
        (slot_id, specialist_id),
    ).fetchone()
    if not slot:
        return None

    now = utcnow()
    updated_start = start_time if start_time else slot["start_time"]
    updated_end = end_time if end_time else slot["end_time"]
    updated_status = new_status if new_status else slot["status"]

    conn.execute(
        "UPDATE time_slots SET start_time = ?, end_time = ?, status = ?, version = version + 1, updated_at = ? WHERE id = ?",
        (updated_start, updated_end, updated_status, now, slot_id),
    )
    conn.commit()

    event_bus.publish("ScheduleModified", {
        "slotId": slot_id,
        "specialistId": specialist_id,
        "oldStartTime": slot["start_time"],
        "oldEndTime": slot["end_time"],
        "newStartTime": updated_start,
        "newEndTime": updated_end,
    })

    specialist = conn.execute("SELECT user_id FROM specialists WHERE id = ?", (specialist_id,)).fetchone()
    user = conn.execute("SELECT name FROM users WHERE id = ?", (specialist["user_id"],)).fetchone()

    return {
        "slotId": slot_id,
        "specialistId": specialist_id,
        "specialistName": user["name"],
        "startTime": updated_start,
        "endTime": updated_end,
        "status": updated_status,
    }


def delete_slot(conn: sqlite3.Connection, slot_id: str, specialist_id: str) -> bool:
    slot = conn.execute(
        "SELECT * FROM time_slots WHERE id = ? AND specialist_id = ?",
        (slot_id, specialist_id),
    ).fetchone()
    if not slot:
        return False

    conn.execute(
        "UPDATE time_slots SET status = 'CANCELLED', updated_at = ? WHERE id = ?",
        (utcnow(), slot_id),
    )
    conn.commit()

    event_bus.publish("ScheduleModified", {
        "slotId": slot_id,
        "specialistId": specialist_id,
        "action": "CANCELLED",
    })
    return True


def block_slot(conn: sqlite3.Connection, slot_id: str, specialist_id: str, reason: str) -> bool:
    slot = conn.execute(
        "SELECT * FROM time_slots WHERE id = ? AND specialist_id = ?",
        (slot_id, specialist_id),
    ).fetchone()
    if not slot:
        return False

    now = utcnow()
    conn.execute(
        "UPDATE time_slots SET status = 'BLOCKED', updated_at = ? WHERE id = ?",
        (now, slot_id),
    )
    block_id = generate_uuid()
    conn.execute(
        "INSERT INTO slot_blocks (id, time_slot_id, reason, blocked_by, created_at) VALUES (?, ?, ?, ?, ?)",
        (block_id, slot_id, reason, specialist_id, now),
    )
    conn.commit()

    event_bus.publish("SlotBlocked", {
        "slotId": slot_id,
        "specialistId": specialist_id,
        "reason": reason,
    })
    return True


def unblock_slot(conn: sqlite3.Connection, slot_id: str, specialist_id: str) -> bool:
    slot = conn.execute(
        "SELECT * FROM time_slots WHERE id = ? AND specialist_id = ? AND status = 'BLOCKED'",
        (slot_id, specialist_id),
    ).fetchone()
    if not slot:
        return False

    now = utcnow()
    conn.execute(
        "UPDATE time_slots SET status = 'AVAILABLE', updated_at = ? WHERE id = ?",
        (now, slot_id),
    )
    conn.execute("DELETE FROM slot_blocks WHERE time_slot_id = ?", (slot_id,))
    conn.commit()
    return True


def find_alternative_slots(conn: sqlite3.Connection, specialist_id: str,
                           exclude_slot_id: str, limit: int = 3) -> list[dict]:
    rows = conn.execute(
        """SELECT ts.id, ts.start_time, ts.end_time
           FROM time_slots ts
           WHERE ts.specialist_id = ? AND ts.status = 'AVAILABLE' AND ts.id != ?
           ORDER BY ts.start_time ASC LIMIT ?""",
        (specialist_id, exclude_slot_id, limit),
    ).fetchall()
    return [{"slotId": r["id"], "startTime": r["start_time"], "endTime": r["end_time"]} for r in rows]


def mark_slot_as_booked(conn: sqlite3.Connection, slot_id: str):
    conn.execute(
        "UPDATE time_slots SET status = 'BOOKED', updated_at = ? WHERE id = ?",
        (utcnow(), slot_id),
    )
    conn.commit()


def release_slot(conn: sqlite3.Connection, slot_id: str):
    conn.execute(
        "UPDATE time_slots SET status = 'AVAILABLE', updated_at = ? WHERE id = ?",
        (utcnow(), slot_id),
    )
    conn.commit()
