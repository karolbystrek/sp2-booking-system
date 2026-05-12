from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, SlotStatus
from app.services import audit_service, schedule_service

MAX_ACTIVE_BOOKINGS = 3


def get_active_booking_count(db: Session, user_id: int) -> int:
    return db.query(Booking).filter(Booking.user_id == user_id, Booking.status == BookingStatus.BOOKED).count()


def create_booking(db: Session, user_id: int, slot_id: int) -> Booking:
    slot = schedule_service.get_slot(db, slot_id)

    if slot.status != SlotStatus.AVAILABLE:
        audit_service.log_event(db, "BOOKING_REJECTED", user_id=user_id, slot_id=slot_id, details="Slot not available")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot is not available")

    if get_active_booking_count(db, user_id) >= MAX_ACTIVE_BOOKINGS:
        audit_service.log_event(db, "BOOKING_REJECTED", user_id=user_id, slot_id=slot_id, details="Active booking limit reached")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active booking limit reached")

    if schedule_service.has_time_conflict(db, user_id, slot):
        audit_service.log_event(db, "BOOKING_REJECTED", user_id=user_id, slot_id=slot_id, details="Time conflict with existing booking")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time conflict with an existing booking")

    slot.status = SlotStatus.BOOKED
    booking = Booking(user_id=user_id, slot_id=slot_id, status=BookingStatus.BOOKED)
    db.add(booking)
    db.flush()

    audit_service.log_event(db, "BOOKING_CREATED", user_id=user_id, slot_id=slot_id)
    db.commit()
    db.refresh(booking)
    return booking


def cancel_booking(db: Session, booking_id: int, user_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")

    if booking.status != BookingStatus.BOOKED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is not active")

    slot = booking.slot
    if slot.start_time - datetime.utcnow() <= timedelta(hours=24):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot cancel within 24 hours of appointment")

    booking.status = BookingStatus.CANCELLED

    # Restore slot to AVAILABLE only if it wasn't independently blocked
    if slot.status == SlotStatus.BOOKED:
        slot.status = SlotStatus.AVAILABLE

    audit_service.log_event(db, "BOOKING_CANCELLED", user_id=user_id, slot_id=slot.id)
    db.commit()
    db.refresh(booking)
    return booking


def get_user_bookings(db: Session, user_id: int) -> list[Booking]:
    return db.query(Booking).filter(Booking.user_id == user_id).all()


def get_all_bookings(db: Session) -> list[Booking]:
    return db.query(Booking).all()
