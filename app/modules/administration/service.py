import sqlite3
import json

from app.database import generate_uuid, utcnow
from app.event_bus import event_bus


def get_system_config(conn: sqlite3.Connection) -> dict:
    row = conn.execute("SELECT * FROM system_config WHERE key = 'booking_rules'").fetchone()
    if not row:
        return {
            "minCancellationHours": 24,
            "maxAdvanceBookingDays": 90,
            "maxReservationsPerUser": 5,
            "updatedBy": None,
            "updatedAt": None,
        }
    config = json.loads(row["value"])
    config["updatedBy"] = row["updated_by"]
    config["updatedAt"] = row["updated_at"]
    return config


def update_system_config(conn: sqlite3.Connection, admin_id: str,
                         min_cancellation_hours: int, max_advance_days: int,
                         max_reservations: int) -> dict:
    now = utcnow()
    value = json.dumps({
        "minCancellationHours": min_cancellation_hours,
        "maxAdvanceBookingDays": max_advance_days,
        "maxReservationsPerUser": max_reservations,
    })

    existing = conn.execute("SELECT key FROM system_config WHERE key = 'booking_rules'").fetchone()
    if existing:
        conn.execute(
            "UPDATE system_config SET value = ?, updated_by = ?, updated_at = ? WHERE key = 'booking_rules'",
            (value, admin_id, now),
        )
    else:
        conn.execute(
            "INSERT INTO system_config (key, value, description, updated_by, updated_at) VALUES ('booking_rules', ?, 'Global booking rules', ?, ?)",
            (value, admin_id, now),
        )
    conn.commit()

    event_bus.publish("SystemRuleUpdated", {
        "minCancellationHours": min_cancellation_hours,
        "maxAdvanceBookingDays": max_advance_days,
        "maxReservationsPerUser": max_reservations,
    })

    return {
        "minCancellationHours": min_cancellation_hours,
        "maxAdvanceBookingDays": max_advance_days,
        "maxReservationsPerUser": max_reservations,
        "updatedBy": admin_id,
        "updatedAt": now,
    }


def get_conflict_exceptions(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM conflict_exceptions ORDER BY created_at DESC"
    ).fetchall()
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "description": r["description"],
            "maxOverlapping": r["max_overlapping"],
            "isActive": bool(r["is_active"]),
            "createdBy": r["created_by"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]


def create_conflict_exception(conn: sqlite3.Connection, admin_id: str,
                              exception_type: str, description: str,
                              max_overlapping: int) -> dict:
    exception_id = generate_uuid()
    now = utcnow()
    conn.execute(
        "INSERT INTO conflict_exceptions (id, type, description, max_overlapping, is_active, created_by, created_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
        (exception_id, exception_type, description, max_overlapping, admin_id, now),
    )
    conn.commit()

    event_bus.publish("ConflictExceptionCreated", {
        "id": exception_id,
        "type": exception_type,
        "maxOverlapping": max_overlapping,
    })

    return {
        "id": exception_id,
        "type": exception_type,
        "description": description,
        "maxOverlapping": max_overlapping,
        "isActive": True,
        "createdBy": admin_id,
        "createdAt": now,
    }


def delete_conflict_exception(conn: sqlite3.Connection, exception_id: str) -> bool:
    row = conn.execute("SELECT id FROM conflict_exceptions WHERE id = ?", (exception_id,)).fetchone()
    if not row:
        return False
    conn.execute("UPDATE conflict_exceptions SET is_active = 0 WHERE id = ?", (exception_id,))
    conn.commit()
    return True


def get_audit_logs(conn: sqlite3.Connection, entity: str | None = None,
                   action: str | None = None, date_from: str | None = None,
                   date_to: str | None = None, page: int = 0, size: int = 20) -> dict:
    query = "SELECT * FROM audit_logs WHERE 1=1"
    count_query = "SELECT COUNT(*) as total FROM audit_logs WHERE 1=1"
    params = []

    if entity:
        query += " AND entity_type = ?"
        count_query += " AND entity_type = ?"
        params.append(entity)
    if action:
        query += " AND action = ?"
        count_query += " AND action = ?"
        params.append(action)
    if date_from:
        query += " AND created_at >= ?"
        count_query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        count_query += " AND created_at <= ?"
        params.append(date_to + "T23:59:59")

    total = conn.execute(count_query, params).fetchone()["total"]
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    rows = conn.execute(query, params).fetchall()

    logs = [
        {
            "id": r["id"],
            "action": r["action"],
            "performedBy": r["performed_by"],
            "performedRole": r["performed_role"],
            "entityType": r["entity_type"],
            "entityId": r["entity_id"],
            "details": r["details"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]

    total_pages = (total + size - 1) // size if total > 0 else 0
    return {"content": logs, "page": page, "size": size,
            "totalElements": total, "totalPages": total_pages}


def create_audit_log(conn: sqlite3.Connection, action: str, performed_by: str,
                     performed_role: str, entity_type: str,
                     entity_id: str | None = None, details: dict | None = None):
    log_id = generate_uuid()
    now = utcnow()
    conn.execute(
        "INSERT INTO audit_logs (id, action, performed_by, performed_role, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (log_id, action, performed_by, performed_role, entity_type,
         entity_id, json.dumps(details) if details else None, now),
    )
    conn.commit()


def get_report(conn: sqlite3.Connection, report_type: str,
               date_from: str | None = None, date_to: str | None = None) -> dict:
    data = {}

    if report_type == "reservations_summary":
        query = "SELECT status, COUNT(*) as count FROM reservations WHERE 1=1"
        params = []
        if date_from:
            query += " AND created_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND created_at <= ?"
            params.append(date_to + "T23:59:59")
        query += " GROUP BY status"
        rows = conn.execute(query, params).fetchall()
        data = {"statusCounts": {r["status"]: r["count"] for r in rows}}

    elif report_type == "specialist_utilization":
        query = """
            SELECT sp.id, u.name,
                   COUNT(CASE WHEN ts.status = 'BOOKED' THEN 1 END) as booked,
                   COUNT(CASE WHEN ts.status = 'AVAILABLE' THEN 1 END) as available,
                   COUNT(*) as total
            FROM specialists sp
            JOIN users u ON sp.user_id = u.id
            LEFT JOIN time_slots ts ON sp.id = ts.specialist_id
            GROUP BY sp.id, u.name
        """
        rows = conn.execute(query).fetchall()
        data = {
            "specialists": [
                {"id": r["id"], "name": r["name"], "booked": r["booked"],
                 "available": r["available"], "total": r["total"]}
                for r in rows
            ]
        }

    return {"type": report_type, "dateFrom": date_from, "dateTo": date_to, "data": data}


def handle_audit_event(payload: dict):
    """Generic audit event handler."""
    import sqlite3 as _sqlite3
    from app.database import DATABASE_PATH
    conn = _sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = _sqlite3.Row
    try:
        create_audit_log(
            conn,
            action=payload.get("event_type", "UNKNOWN"),
            performed_by=payload.get("userId", "system"),
            performed_role=payload.get("role", "SYSTEM"),
            entity_type=payload.get("entityType", "reservation"),
            entity_id=payload.get("reservationId"),
            details=payload,
        )
    finally:
        conn.close()


def register_event_handlers():
    event_bus.subscribe("ReservationCreated", lambda p: handle_audit_event({**p, "event_type": "RESERVATION_CREATED", "entityType": "reservation"}))
    event_bus.subscribe("ReservationCancelled", lambda p: handle_audit_event({**p, "event_type": "RESERVATION_CANCELLED", "entityType": "reservation"}))
    event_bus.subscribe("ReservationRescheduled", lambda p: handle_audit_event({**p, "event_type": "RESERVATION_RESCHEDULED", "entityType": "reservation"}))
    event_bus.subscribe("ScheduleModified", lambda p: handle_audit_event({**p, "event_type": "SCHEDULE_MODIFIED", "entityType": "schedule"}))
