from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from src.shared.api import api_error, require_roles
from src.shared.database import get_connection, new_id, now_iso, row_to_dict, rows_to_list, write_audit_log

router = APIRouter(prefix="/api/v1", tags=["scheduling"])


class AvailabilitySlotRequest(BaseModel):
    dayOfWeek: int = Field(ge=0, le=6)
    startTime: str
    endTime: str


class ScheduleUpdateRequest(BaseModel):
    availabilitySlots: list[AvailabilitySlotRequest]


class ScheduleExceptionRequest(BaseModel):
    date: date
    startTime: str
    endTime: str
    type: str


def specialist_for_user(connection, user_id: str) -> dict[str, Any]:
    specialist = row_to_dict(connection.execute("SELECT * FROM specialists WHERE user_id = ?", (user_id,)).fetchone())
    if not specialist:
        raise api_error(status.HTTP_404_NOT_FOUND, "SPECIALIST_NOT_FOUND", "Current user is not a specialist.")
    return specialist


def validate_no_overlaps(slots: list[AvailabilitySlotRequest]) -> None:
    by_day: dict[int, list[tuple[str, str]]] = {}
    for slot in slots:
        if slot.startTime >= slot.endTime:
            raise api_error(status.HTTP_400_BAD_REQUEST, "INVALID_TIME_RANGE", "Slot start time must be before end time.")
        by_day.setdefault(slot.dayOfWeek, []).append((slot.startTime, slot.endTime))

    for ranges in by_day.values():
        ordered = sorted(ranges)
        for index in range(1, len(ordered)):
            if ordered[index][0] < ordered[index - 1][1]:
                raise api_error(status.HTTP_409_CONFLICT, "SCHEDULE_OVERLAP", "Availability slots cannot overlap.")


@router.get("/availability")
def get_availability(
    specialistId: str = Query(...),
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    offset = (page - 1) * size
    start = f"{from_.isoformat()}T00:00:00"
    end = f"{to.isoformat()}T23:59:59"
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, specialist_id, start_at, end_at, status, version
            FROM time_slots
            WHERE specialist_id = ?
              AND status = 'AVAILABLE'
              AND start_at >= ?
              AND start_at <= ?
              AND NOT EXISTS (
                  SELECT 1 FROM reservations r
                  WHERE r.slot_id = time_slots.id
                    AND r.status IN ('CREATED', 'CONFIRMED')
              )
            ORDER BY start_at
            LIMIT ? OFFSET ?
            """,
            (specialistId, start, end, size, offset),
        ).fetchall()
    return {"page": page, "size": size, "items": rows_to_list(rows)}


@router.get("/schedules/me")
def get_my_schedule(user: dict[str, Any] = Depends(require_roles("SPECIALIST"))) -> dict[str, Any]:
    with get_connection() as connection:
        specialist = specialist_for_user(connection, user["id"])
        schedule = row_to_dict(connection.execute("SELECT * FROM schedules WHERE specialist_id = ?", (specialist["id"],)).fetchone())
        slots = rows_to_list(
            connection.execute(
                "SELECT id, day_of_week, start_time, end_time FROM availability_slots WHERE schedule_id = ? ORDER BY day_of_week, start_time",
                (schedule["id"],),
            ).fetchall()
        )
        exceptions = rows_to_list(
            connection.execute(
                "SELECT id, date, start_time, end_time, type FROM schedule_exceptions WHERE schedule_id = ? ORDER BY date, start_time",
                (schedule["id"],),
            ).fetchall()
        )
    return {**schedule, "availabilitySlots": slots, "exceptions": exceptions}


@router.put("/schedules/me")
def update_my_schedule(
    request: ScheduleUpdateRequest,
    user: dict[str, Any] = Depends(require_roles("SPECIALIST")),
) -> dict[str, Any]:
    validate_no_overlaps(request.availabilitySlots)
    with get_connection() as connection:
        specialist = specialist_for_user(connection, user["id"])
        schedule = row_to_dict(connection.execute("SELECT * FROM schedules WHERE specialist_id = ?", (specialist["id"],)).fetchone())
        connection.execute("DELETE FROM availability_slots WHERE schedule_id = ?", (schedule["id"],))
        for slot in request.availabilitySlots:
            connection.execute(
                """
                INSERT INTO availability_slots (id, schedule_id, day_of_week, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (new_id(), schedule["id"], slot.dayOfWeek, slot.startTime, slot.endTime),
            )
        connection.execute(
            "UPDATE schedules SET version = version + 1, updated_at = ? WHERE id = ?",
            (now_iso(), schedule["id"]),
        )
        write_audit_log(connection, user["id"], "ScheduleUpdated", "Schedule", schedule["id"], request.model_dump())

    return get_my_schedule(user)


@router.post("/schedules/me/exceptions")
def add_schedule_exception(
    request: ScheduleExceptionRequest,
    user: dict[str, Any] = Depends(require_roles("SPECIALIST")),
) -> dict[str, Any]:
    if request.startTime >= request.endTime:
        raise api_error(status.HTTP_400_BAD_REQUEST, "INVALID_TIME_RANGE", "Exception start time must be before end time.")

    with get_connection() as connection:
        specialist = specialist_for_user(connection, user["id"])
        schedule = row_to_dict(connection.execute("SELECT * FROM schedules WHERE specialist_id = ?", (specialist["id"],)).fetchone())
        exception_id = new_id()
        connection.execute(
            """
            INSERT INTO schedule_exceptions (id, schedule_id, date, start_time, end_time, type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (exception_id, schedule["id"], request.date.isoformat(), request.startTime, request.endTime, request.type),
        )
        connection.execute("UPDATE schedules SET version = version + 1, updated_at = ? WHERE id = ?", (now_iso(), schedule["id"]))
        write_audit_log(connection, user["id"], "ScheduleUpdated", "Schedule", schedule["id"], request.model_dump(mode="json"))
        exception = row_to_dict(connection.execute("SELECT * FROM schedule_exceptions WHERE id = ?", (exception_id,)).fetchone())

    return exception
