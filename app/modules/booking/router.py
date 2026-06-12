import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.modules.booking.schemas import (
    CreateReservationRequest, ReservationResponse,
    CancelBySpecialistRequest, RescheduleRequest, AdminResolveRequest,
)
from app.modules.booking import service
from app.modules.booking.service import ConflictError
from app.modules.availability.service import get_specialist_id_for_user

router = APIRouter()


@router.post("/reservations", response_model=ReservationResponse, status_code=201)
def create_reservation(request: CreateReservationRequest,
                       current_user: dict = Depends(require_roles(["USER"])),
                       conn: sqlite3.Connection = Depends(get_db)):
    try:
        result = service.create_reservation(
            conn, current_user["id"], request.specialistId,
            request.timeSlotId, request.notes,
        )
        return result
    except ConflictError as e:
        raise HTTPException(status_code=409, detail={
            "error": "SLOT_ALREADY_BOOKED",
            "message": e.message,
            "suggestedAlternatives": e.alternatives,
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reservations")
def list_my_reservations(status: str | None = None, page: int = 0, size: int = 20,
                         current_user: dict = Depends(get_current_user),
                         conn: sqlite3.Connection = Depends(get_db)):
    return service.get_user_reservations(conn, current_user["id"], status=status, page=page, size=size)


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
def get_reservation(reservation_id: str,
                    current_user: dict = Depends(get_current_user),
                    conn: sqlite3.Connection = Depends(get_db)):
    result = service.get_reservation(conn, reservation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if result["userId"] != current_user["id"] and "SPECIALIST" not in current_user["roles"] and "ADMINISTRATOR" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return result


@router.delete("/reservations/{reservation_id}", status_code=200)
def cancel_reservation(reservation_id: str,
                       current_user: dict = Depends(require_roles(["USER"])),
                       conn: sqlite3.Connection = Depends(get_db)):
    try:
        return service.cancel_reservation_by_user(conn, reservation_id, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/reservations/{reservation_id}/cancel")
def cancel_by_specialist(reservation_id: str, request: CancelBySpecialistRequest,
                         current_user: dict = Depends(require_roles(["SPECIALIST"])),
                         conn: sqlite3.Connection = Depends(get_db)):
    specialist_id = get_specialist_id_for_user(conn, current_user["id"])
    if not specialist_id:
        raise HTTPException(status_code=404, detail="Specialist profile not found")
    try:
        return service.cancel_reservation_by_specialist(conn, reservation_id, specialist_id, request.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/reservations/{reservation_id}/reschedule")
def reschedule(reservation_id: str, request: RescheduleRequest,
               current_user: dict = Depends(require_roles(["SPECIALIST"])),
               conn: sqlite3.Connection = Depends(get_db)):
    specialist_id = get_specialist_id_for_user(conn, current_user["id"])
    if not specialist_id:
        raise HTTPException(status_code=404, detail="Specialist profile not found")
    try:
        return service.reschedule_reservation(conn, reservation_id, specialist_id, request.newTimeSlotId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reservations/{reservation_id}/history")
def get_history(reservation_id: str,
                current_user: dict = Depends(get_current_user),
                conn: sqlite3.Connection = Depends(get_db)):
    reservation = service.get_reservation(conn, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return service.get_reservation_history(conn, reservation_id)


@router.get("/specialists/{specialist_id}/reservations")
def get_specialist_reservations(specialist_id: str,
                                date_from: str | None = None, date_to: str | None = None,
                                current_user: dict = Depends(require_roles(["SPECIALIST"])),
                                conn: sqlite3.Connection = Depends(get_db)):
    own_specialist_id = get_specialist_id_for_user(conn, current_user["id"])
    if own_specialist_id != specialist_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return service.get_specialist_reservations(conn, specialist_id, date_from, date_to)


@router.get("/admin/reservations")
def admin_list_reservations(specialist: str | None = None, status: str | None = None,
                            date_from: str | None = None, date_to: str | None = None,
                            page: int = 0, size: int = 20,
                            current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                            conn: sqlite3.Connection = Depends(get_db)):
    return service.get_all_reservations_admin(conn, specialist=specialist, status=status,
                                             date_from=date_from, date_to=date_to,
                                             page=page, size=size)


@router.patch("/admin/reservations/{reservation_id}/resolve")
def admin_resolve(reservation_id: str, request: AdminResolveRequest,
                  current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                  conn: sqlite3.Connection = Depends(get_db)):
    try:
        return service.resolve_conflict_admin(conn, reservation_id, request.action,
                                             current_user["id"], request.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
