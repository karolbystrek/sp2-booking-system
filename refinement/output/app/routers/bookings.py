from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.dependencies import get_db
from app.models import Booking
from app.models import User
from app.schemas import BookingCreate
from app.schemas import BookingResponse
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return BookingService.create_booking(db, user, payload.slot_id)


@router.delete("/{booking_id}", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return BookingService.cancel_booking(db, user, booking_id)


@router.get("/my", response_model=list[BookingResponse])
def get_my_bookings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Booking).filter(Booking.user_id == user.id).all()