from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, models
from ..database import get_db
from ..dependencies import get_current_user
from ..services import schedule_service, booking_service

router = APIRouter(prefix="", tags=["Users"])

@router.get("/slots", response_model=List[schemas.SlotResponse])
def get_available_slots(
    specialist_id: Optional[int] = None, 
    date: Optional[str] = None, 
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    slots = schedule_service.get_slots(db, specialist_id=specialist_id, date=date)
    return [slot for slot in slots if slot.status == "AVAILABLE"]

@router.post("/bookings", response_model=schemas.BookingResponse)
def create_booking(
    booking_in: schemas.BookingCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    return booking_service.book_slot(db, user, booking_in.slot_id)

@router.delete("/bookings/{booking_id}", response_model=schemas.BookingResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    return booking_service.cancel_booking(db, user, booking_id)

@router.get("/bookings/my", response_model=List[schemas.BookingResponse])
def get_my_bookings(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    if user.role != "USER":
        raise HTTPException(status_code=403, detail="Only users have bookings")
    return booking_service.get_user_bookings(db, user.id)
