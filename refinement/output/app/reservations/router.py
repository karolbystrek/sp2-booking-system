from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.database import get_db
from app.identity.auth import get_current_user, RequireRole
from app.identity.models import User
from app.reservations.schemas import ReservationCreate, ReservationModify, ReservationRead
from app.reservations.service import ReservationService

router = APIRouter()

@router.post(
    "/reservations",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED
)
async def create_reservation(
    payload: ReservationCreate,
    current_user: User = Depends(RequireRole(["Patient"])),
    db: Session = Depends(get_db)
):
    service = ReservationService(db)
    # Ensure a patient is booking for themselves, unless admin
    is_admin = any(r.name in ["Admin", "Administrator"] for r in current_user.roles)
    if not is_admin and payload.patient_id != current_user.user_id:
        from app.exceptions import ForbiddenException
        raise ForbiddenException("You can only make reservations for yourself")
        
    return await service.create_reservation(payload)

@router.get(
    "/reservations/{reservationId}",
    response_model=ReservationRead
)
async def get_reservation(
    reservationId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ReservationService(db)
    reservation = service.get_reservation(reservationId)
    # Check permissions (only patient, specialist, or admin)
    is_admin = any(r.name in ["Admin", "Administrator"] for r in current_user.roles)
    if not is_admin and current_user.user_id not in [reservation.patient_id, reservation.specialist_id]:
        from app.exceptions import ForbiddenException
        raise ForbiddenException("Access denied to this reservation")
    return reservation

@router.put(
    "/reservations/{reservationId}/cancel",
    response_model=ReservationRead
)
async def cancel_reservation(
    reservationId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ReservationService(db)
    return await service.cancel_reservation(reservationId, current_user.user_id)

@router.put(
    "/reservations/{reservationId}/modify",
    response_model=ReservationRead
)
async def modify_reservation(
    reservationId: str,
    payload: ReservationModify,
    current_user: User = Depends(RequireRole(["Specialist"])),
    db: Session = Depends(get_db)
):
    service = ReservationService(db)
    return await service.modify_reservation(reservationId, payload, current_user.user_id)

@router.get(
    "/patients/{patientId}/reservations",
    response_model=List[ReservationRead]
)
async def get_patient_reservations(
    patientId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ReservationService(db)
    return service.get_patient_reservations(patientId, current_user.user_id)

@router.get(
    "/specialists/{specialistId}/reservations",
    response_model=List[ReservationRead]
)
async def get_specialist_reservations(
    specialistId: str,
    startDate: Optional[datetime] = Query(None, description="Start date filter"),
    endDate: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ReservationService(db)
    return service.get_specialist_reservations(specialistId, current_user.user_id, startDate, endDate)
