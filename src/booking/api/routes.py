import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from src.shared.api import api_error, current_user
from src.shared.database import get_connection, new_id, now_iso, row_to_dict, rows_to_list, write_audit_log

router = APIRouter(prefix="/api/v1", tags=["booking"])


class CreateReservationRequest(BaseModel):
    slotId: str
    notes: str | None = None


def active_statuses() -> tuple[str, str]:
    return ("CREATED", "CONFIRMED")


def active_policy(connection) -> dict[str, Any]:
    policy = row_to_dict(
        connection.execute(
            """
            SELECT *
            FROM booking_policies
            WHERE active_to IS NULL
            ORDER BY active_from DESC
            LIMIT 1
            """
        ).fetchone()
    )
    if not policy:
        raise api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "POLICY_MISSING", "Active booking policy is missing.")
    return policy


def reservation_response(reservation: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": reservation["id"],
        "userId": reservation["user_id"],
        "specialistId": reservation["specialist_id"],
        "slotId": reservation["slot_id"],
        "status": reservation["status"],
        "notes": reservation["notes"],
        "createdAt": reservation["created_at"],
        "cancelledAt": reservation["cancelled_at"],
        "version": reservation["version"],
    }


def valid_conflict_exception(connection, slot: dict[str, Any]) -> bool:
    current_time = now_iso()
    row = connection.execute(
        """
        SELECT 1
        FROM conflict_exceptions
        WHERE (slot_id = ? OR specialist_id = ?)
          AND active_from <= ?
          AND active_to >= ?
        LIMIT 1
        """,
        (slot["id"], slot["specialist_id"], current_time, current_time),
    ).fetchone()
    return row is not None


@router.post("/reservations", status_code=status.HTTP_201_CREATED)
def create_reservation(
    request: CreateReservationRequest,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with get_connection() as connection:
        policy = active_policy(connection)
        active_count = connection.execute(
            "SELECT COUNT(*) FROM reservations WHERE user_id = ? AND status IN ('CREATED', 'CONFIRMED')",
            (user["id"],),
        ).fetchone()[0]
        if active_count > policy["max_active_reservations"]:
            raise api_error(status.HTTP_409_CONFLICT, "ACTIVE_RESERVATION_LIMIT", "Active reservation limit was reached.")

        slot = row_to_dict(connection.execute("SELECT * FROM time_slots WHERE id = ?", (request.slotId,)).fetchone())
        if not slot:
            raise api_error(status.HTTP_404_NOT_FOUND, "SLOT_NOT_FOUND", "Time slot was not found.")

        existing = connection.execute(
            "SELECT 1 FROM reservations WHERE slot_id = ? AND status IN ('CREATED', 'CONFIRMED')",
            (slot["id"],),
        ).fetchone()
        if existing:
            raise api_error(status.HTTP_409_CONFLICT, "SLOT_ALREADY_BOOKED", "Selected slot is no longer available.")

        if slot["status"] != "AVAILABLE" and not valid_conflict_exception(connection, slot):
            raise api_error(status.HTTP_409_CONFLICT, "CONFLICT_DETECTED", "Selected slot is not available.")

        reservation_id = new_id()
        try:
            connection.execute(
                """
                INSERT INTO reservations (id, user_id, specialist_id, slot_id, status, notes, created_at, cancelled_at, version)
                VALUES (?, ?, ?, ?, 'CREATED', ?, ?, NULL, 1)
                """,
                (reservation_id, user["id"], slot["specialist_id"], slot["id"], request.notes, now_iso()),
            )
            connection.execute("UPDATE time_slots SET status = 'BOOKED', version = version + 1 WHERE id = ?", (slot["id"],))
        except sqlite3.IntegrityError:
            raise api_error(status.HTTP_409_CONFLICT, "SLOT_ALREADY_BOOKED", "Selected slot is no longer available.")

        write_audit_log(connection, user["id"], "ReservationCreated", "Reservation", reservation_id, {"slotId": slot["id"]})
        reservation = row_to_dict(connection.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone())

    return reservation_response(reservation)


@router.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with get_connection() as connection:
        reservation = row_to_dict(connection.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone())
    if not reservation:
        raise api_error(status.HTTP_404_NOT_FOUND, "RESERVATION_NOT_FOUND", "Reservation was not found.")
    if reservation["user_id"] != user["id"] and "ADMIN" not in user["roles"]:
        raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Reservation is not available for this user.")
    return reservation_response(reservation)


@router.get("/users/me/reservations")
def get_my_reservations(user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM reservations WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    return [reservation_response(row) for row in rows_to_list(rows)]


@router.delete("/reservations/{reservation_id}")
def cancel_reservation(reservation_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with get_connection() as connection:
        reservation = row_to_dict(connection.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone())
        if not reservation:
            raise api_error(status.HTTP_404_NOT_FOUND, "RESERVATION_NOT_FOUND", "Reservation was not found.")
        if reservation["user_id"] != user["id"] and "ADMIN" not in user["roles"]:
            raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Reservation cannot be cancelled by this user.")
        if reservation["status"] not in active_statuses():
            raise api_error(status.HTTP_409_CONFLICT, "RESERVATION_NOT_ACTIVE", "Only active reservations can be cancelled.")

        slot = row_to_dict(connection.execute("SELECT * FROM time_slots WHERE id = ?", (reservation["slot_id"],)).fetchone())
        policy = active_policy(connection)
        slot_start = datetime.fromisoformat(slot["start_at"])
        hours_until_start = (slot_start - datetime.now(timezone.utc)).total_seconds() / 3600
        if hours_until_start < policy["cancellation_window_hours"] and "ADMIN" not in user["roles"]:
            raise api_error(status.HTTP_409_CONFLICT, "CANCELLATION_WINDOW_CLOSED", "Cancellation window is closed.")

        connection.execute(
            "UPDATE reservations SET status = 'CANCELLED', cancelled_at = ?, version = version + 1 WHERE id = ?",
            (now_iso(), reservation_id),
        )
        connection.execute("UPDATE time_slots SET status = 'AVAILABLE', version = version + 1 WHERE id = ?", (reservation["slot_id"],))
        write_audit_log(connection, user["id"], "ReservationCancelled", "Reservation", reservation_id, {})
        updated = row_to_dict(connection.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone())

    return reservation_response(updated)


@router.post("/reservations/{reservation_id}/confirm")
def confirm_reservation(reservation_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with get_connection() as connection:
        reservation = row_to_dict(connection.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone())
        if not reservation:
            raise api_error(status.HTTP_404_NOT_FOUND, "RESERVATION_NOT_FOUND", "Reservation was not found.")
        if reservation["user_id"] != user["id"] and "ADMIN" not in user["roles"]:
            raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Reservation cannot be confirmed by this user.")
        if reservation["status"] != "CREATED":
            raise api_error(status.HTTP_409_CONFLICT, "INVALID_RESERVATION_STATUS", "Only created reservations can be confirmed.")
        connection.execute("UPDATE reservations SET status = 'CONFIRMED', version = version + 1 WHERE id = ?", (reservation_id,))
        updated = row_to_dict(connection.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone())

    return reservation_response(updated)
