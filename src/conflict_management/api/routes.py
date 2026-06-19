from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from src.shared.api import api_error, require_roles
from src.shared.database import get_connection, new_id, row_to_dict, rows_to_list, write_audit_log

router = APIRouter(prefix="/api/v1", tags=["conflict-management"])


class ConflictExceptionRequest(BaseModel):
    specialistId: str | None = None
    slotId: str | None = None
    reason: str
    activeFrom: datetime
    activeTo: datetime


def conflict_exception_response(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "specialistId": item["specialist_id"],
        "slotId": item["slot_id"],
        "reason": item["reason"],
        "activeFrom": item["active_from"],
        "activeTo": item["active_to"],
    }


@router.get("/conflict-exceptions")
def list_conflict_exceptions(_: dict[str, Any] = Depends(require_roles("ADMIN"))) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM conflict_exceptions ORDER BY active_from DESC").fetchall()
    return [conflict_exception_response(item) for item in rows_to_list(rows)]


@router.post("/conflict-exceptions", status_code=status.HTTP_201_CREATED)
def create_conflict_exception(
    request: ConflictExceptionRequest,
    actor: dict[str, Any] = Depends(require_roles("ADMIN")),
) -> dict[str, Any]:
    if not request.specialistId and not request.slotId:
        raise api_error(status.HTTP_400_BAD_REQUEST, "INVALID_EXCEPTION_SCOPE", "Specialist or slot must be provided.")
    if request.activeFrom >= request.activeTo:
        raise api_error(status.HTTP_400_BAD_REQUEST, "INVALID_TIME_RANGE", "Exception start must be before end.")

    exception_id = new_id()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO conflict_exceptions (id, specialist_id, slot_id, reason, active_from, active_to)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                exception_id,
                request.specialistId,
                request.slotId,
                request.reason,
                request.activeFrom.isoformat(),
                request.activeTo.isoformat(),
            ),
        )
        write_audit_log(connection, actor["id"], "ConflictExceptionApplied", "ConflictException", exception_id, request.model_dump(mode="json"))
        item = row_to_dict(connection.execute("SELECT * FROM conflict_exceptions WHERE id = ?", (exception_id,)).fetchone())

    return conflict_exception_response(item)


@router.delete("/conflict-exceptions/{exception_id}")
def delete_conflict_exception(
    exception_id: str,
    actor: dict[str, Any] = Depends(require_roles("ADMIN")),
) -> dict[str, str]:
    with get_connection() as connection:
        item = row_to_dict(connection.execute("SELECT * FROM conflict_exceptions WHERE id = ?", (exception_id,)).fetchone())
        if not item:
            raise api_error(status.HTTP_404_NOT_FOUND, "CONFLICT_EXCEPTION_NOT_FOUND", "Conflict exception was not found.")
        connection.execute("DELETE FROM conflict_exceptions WHERE id = ?", (exception_id,))
        write_audit_log(connection, actor["id"], "ConflictExceptionDeleted", "ConflictException", exception_id, {})
    return {"status": "deleted"}
