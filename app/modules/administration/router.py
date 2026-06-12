import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies import require_roles
from app.modules.administration import service
from app.modules.administration.schemas import (
    SystemConfigUpdateRequest, ConflictExceptionCreateRequest,
)

router = APIRouter()


@router.get("/admin/config")
def get_config(current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
               conn: sqlite3.Connection = Depends(get_db)):
    return service.get_system_config(conn)


@router.put("/admin/config")
def update_config(request: SystemConfigUpdateRequest,
                  current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                  conn: sqlite3.Connection = Depends(get_db)):
    return service.update_system_config(
        conn, current_user["id"],
        request.minCancellationHours,
        request.maxAdvanceBookingDays,
        request.maxReservationsPerUser,
    )


@router.get("/admin/conflict-exceptions")
def list_exceptions(current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                    conn: sqlite3.Connection = Depends(get_db)):
    return service.get_conflict_exceptions(conn)


@router.post("/admin/conflict-exceptions", status_code=201)
def create_exception(request: ConflictExceptionCreateRequest,
                     current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                     conn: sqlite3.Connection = Depends(get_db)):
    return service.create_conflict_exception(
        conn, current_user["id"], request.type,
        request.description, request.maxOverlapping,
    )


@router.delete("/admin/conflict-exceptions/{exception_id}", status_code=204)
def delete_exception(exception_id: str,
                     current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                     conn: sqlite3.Connection = Depends(get_db)):
    if not service.delete_conflict_exception(conn, exception_id):
        raise HTTPException(status_code=404, detail="Exception not found")


@router.get("/admin/reports")
def get_report(type: str = "reservations_summary",
               date_from: str | None = None, date_to: str | None = None,
               current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
               conn: sqlite3.Connection = Depends(get_db)):
    return service.get_report(conn, type, date_from, date_to)


@router.get("/admin/audit-logs")
def list_audit_logs(entity: str | None = None, action: str | None = None,
                    date_from: str | None = None, date_to: str | None = None,
                    page: int = 0, size: int = 20,
                    current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                    conn: sqlite3.Connection = Depends(get_db)):
    return service.get_audit_logs(conn, entity=entity, action=action,
                                  date_from=date_from, date_to=date_to,
                                  page=page, size=size)
