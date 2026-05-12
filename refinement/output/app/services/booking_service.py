from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timedelta
from ..models import Booking, Slot, User
from . import schedule_service, audit_service

def book_slot(db: Session, user: User, slot_id: int):
    if user.role != "USER":
        raise HTTPException(status_code=403, detail="Only users can book slots")

    slot = schedule_service.get_slot_by_id(db, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if slot.status != "AVAILABLE":
        audit_service.log_event(db, "BOOKING_REJECTED_UNAVAILABLE", user.id, slot.id, "Slot is not available")
        raise HTTPException(status_code=400, detail="Slot is not available")

    active_bookings_count = db.query(Booking).filter(Booking.user_id == user.id, Booking.status == "BOOKED").count()
    if active_bookings_count >= 3:
        audit_service.log_event(db, "BOOKING_REJECTED_LIMIT_REACHED", user.id, slot.id, "User has reached the limit of 3 active bookings")
        raise HTTPException(status_code=400, detail="Maximum 3 active bookings allowed")

    if schedule_service.has_time_conflict(db, user.id, slot.start_time, slot.end_time):
        audit_service.log_event(db, "BOOKING_REJECTED_TIME_CONFLICT", user.id, slot.id, "Time conflict with an existing booking")
        raise HTTPException(status_code=400, detail="Time conflict with existing booking")

    try:
        # Create booking and change slot status
        booking = Booking(user_id=user.id, slot_id=slot.id, status="BOOKED")
        db.add(booking)
        slot.status = "BOOKED"
        db.commit()
        db.refresh(booking)

        audit_service.log_event(db, "BOOKING_CREATED", user.id, slot.id, f"Booking ID: {booking.id}")
        return booking
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error during booking")

def cancel_booking(db: Session, user: User, booking_id: int):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    if booking.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    slot = booking.slot
    time_until_slot = slot.start_time - datetime.utcnow()
    
    if time_until_slot < timedelta(hours=24) and user.role != "ADMIN":
        audit_service.log_event(db, "CANCEL_REJECTED_TIME", user.id, slot.id, "Less than 24h before slot")
        raise HTTPException(status_code=400, detail="Cannot cancel less than 24 hours before the appointment")

    try:
        booking.status = "CANCELLED"
        if slot.status == "BOOKED":
            slot.status = "AVAILABLE"
        
        db.commit()
        db.refresh(booking)
        
        audit_service.log_event(db, "BOOKING_CANCELLED", user.id, slot.id, f"Booking ID: {booking.id}")
        return booking
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error during cancellation")

def get_user_bookings(db: Session, user_id: int):
    return db.query(Booking).filter(Booking.user_id == user_id).all()

def get_all_bookings(db: Session):
    return db.query(Booking).all()
