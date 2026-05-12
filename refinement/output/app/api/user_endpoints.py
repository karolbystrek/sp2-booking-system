from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.schemas import BookingCreate, BookingOut, SlotOut
from app.services import booking_service, schedule_service

router = APIRouter(tags=["user"])


@router.get("/slots", response_model=list[SlotOut])
def list_available_slots(
    specialist_id: Optional[int] = None,
    date: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return schedule_service.get_available_slots(db, specialist_id=specialist_id, date_filter=date)


@router.post("/bookings", response_model=BookingOut, status_code=201)
def book_slot(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.USER)),
):
    return booking_service.create_booking(db, user_id=current_user.id, slot_id=payload.slot_id)


@router.delete("/bookings/{booking_id}", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.USER)),
):
    return booking_service.cancel_booking(db, booking_id=booking_id, user_id=current_user.id)


@router.get("/bookings/my", response_model=list[BookingOut])
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.USER)),
):
    return booking_service.get_user_bookings(db, user_id=current_user.id)
