import sqlite3
import json
import logging

from app.database import generate_uuid, utcnow
from app.event_bus import event_bus

logger = logging.getLogger(__name__)


def create_notification(conn: sqlite3.Connection, recipient_id: str,
                        channel: str, notification_type: str, payload: dict):
    notification_id = generate_uuid()
    now = utcnow()
    conn.execute(
        """INSERT INTO notifications (id, recipient_id, channel, type, payload, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'PENDING', ?)""",
        (notification_id, recipient_id, channel, notification_type, json.dumps(payload), now),
    )
    conn.commit()

    # Simulate sending (in production would use email/push strategy)
    conn.execute(
        "UPDATE notifications SET status = 'SENT', sent_at = ? WHERE id = ?",
        (utcnow(), notification_id),
    )
    conn.commit()
    logger.info(f"Notification sent: {notification_type} to {recipient_id} via {channel}")


def get_user_notifications(conn: sqlite3.Connection, user_id: str,
                           read: bool | None = None, page: int = 0, size: int = 20) -> dict:
    query = "SELECT * FROM notifications WHERE recipient_id = ?"
    count_query = "SELECT COUNT(*) as total FROM notifications WHERE recipient_id = ?"
    params = [user_id]

    if read is not None:
        status_filter = "SENT" if read else "PENDING"
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status_filter)

    total = conn.execute(count_query, params).fetchone()["total"]
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    rows = conn.execute(query, params).fetchall()

    notifications = [
        {
            "id": r["id"],
            "recipientId": r["recipient_id"],
            "channel": r["channel"],
            "type": r["type"],
            "payload": r["payload"],
            "status": r["status"],
            "sentAt": r["sent_at"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]

    total_pages = (total + size - 1) // size if total > 0 else 0
    return {"content": notifications, "page": page, "size": size,
            "totalElements": total, "totalPages": total_pages}


def mark_as_read(conn: sqlite3.Connection, notification_id: str, user_id: str) -> bool:
    row = conn.execute(
        "SELECT * FROM notifications WHERE id = ? AND recipient_id = ?",
        (notification_id, user_id),
    ).fetchone()
    if not row:
        return False
    conn.execute(
        "UPDATE notifications SET status = 'DELIVERED' WHERE id = ?",
        (notification_id,),
    )
    conn.commit()
    return True


def get_preferences(conn: sqlite3.Connection, user_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM user_notification_preferences WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return {"userId": user_id, "emailEnabled": True, "pushEnabled": True, "updatedAt": utcnow()}
    return {
        "userId": row["user_id"],
        "emailEnabled": bool(row["email_enabled"]),
        "pushEnabled": bool(row["push_enabled"]),
        "updatedAt": row["updated_at"],
    }


def update_preferences(conn: sqlite3.Connection, user_id: str,
                       email_enabled: bool, push_enabled: bool) -> dict:
    now = utcnow()
    existing = conn.execute(
        "SELECT user_id FROM user_notification_preferences WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE user_notification_preferences SET email_enabled = ?, push_enabled = ?, updated_at = ? WHERE user_id = ?",
            (int(email_enabled), int(push_enabled), now, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO user_notification_preferences (user_id, email_enabled, push_enabled, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, int(email_enabled), int(push_enabled), now),
        )
    conn.commit()
    return {"userId": user_id, "emailEnabled": email_enabled, "pushEnabled": push_enabled, "updatedAt": now}


def handle_reservation_created(payload: dict):
    """Event handler for ReservationCreated events."""
    import sqlite3 as _sqlite3
    from app.database import DATABASE_PATH
    conn = _sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = _sqlite3.Row
    try:
        create_notification(conn, payload["userId"], "EMAIL",
                            "RESERVATION_CONFIRMED", payload)
    finally:
        conn.close()


def handle_reservation_cancelled(payload: dict):
    """Event handler for ReservationCancelled events."""
    import sqlite3 as _sqlite3
    from app.database import DATABASE_PATH
    conn = _sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = _sqlite3.Row
    try:
        create_notification(conn, payload["userId"], "EMAIL",
                            "RESERVATION_CANCELLED", payload)
    finally:
        conn.close()


def handle_reservation_rescheduled(payload: dict):
    """Event handler for ReservationRescheduled events."""
    import sqlite3 as _sqlite3
    from app.database import DATABASE_PATH
    conn = _sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = _sqlite3.Row
    try:
        create_notification(conn, payload["userId"], "EMAIL",
                            "RESERVATION_RESCHEDULED", payload)
    finally:
        conn.close()


def register_event_handlers():
    event_bus.subscribe("ReservationCreated", handle_reservation_created)
    event_bus.subscribe("ReservationCancelled", handle_reservation_cancelled)
    event_bus.subscribe("ReservationRescheduled", handle_reservation_rescheduled)
