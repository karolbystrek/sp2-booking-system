from datetime import datetime
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Booking
from app.models import BookingStatus
from app.models import Slot
from app.models import SlotStatus
from app.models import User
from app.services.audit_service import AuditService
from app.services.schedule_service import ScheduleService


class BookingService:
    @staticmethod
    def create_booking(db: Session, user: User, slot_id: int):
        slot = ScheduleService.get_slot(db, slot_id)

        ScheduleService.validate_slot_available(slot)
        BookingService.validate_booking_limit(db, user)
        ScheduleService.validate_time_conflict(db, user.id, slot)

        try:
            booking = Booking(
                user_id=user.id,
                slot_id=slot.id,
                status=BookingStatus.BOOKED,
            )

            slot.status = SlotStatus.BOOKED

            db.add(booking)
            db.commit()
            db.refresh(booking)

            AuditService.log(
                db=db,
                event_type="BOOKING_CREATED",
                user_id=user.id,
                slot_id=slot.id,
                details="Booking created",
            )

            return booking
        except Exception:
            db.rollback()

            AuditService.log(
                db=db,
                event_type="BOOKING_FAILED",
                user_id=user.id,
                slot_id=slot.id,
                details="Booking failed",
            )

            raise HTTPException(status_code=409, detail="Booking conflict")

    @staticmethod
    def cancel_booking(db: Session, user: User, booking_id: int):
        booking = db.query(Booking).filter(Booking.id == booking_id).first()

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        if booking.user_id != user.id and user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Access denied")

        slot = db.query(Slot).filter(Slot.id == booking.slot_id).first()

        if slot.start_time - datetime.utcnow() <= timedelta(hours=24):
            raise HTTPException(
                status_code=400,
                detail="Cancellation is not allowed within 24 hours",
            )

        booking.status = BookingStatus.CANCELLED

        if slot.status != SlotStatus.BLOCKED:
            slot.status = SlotStatus.AVAILABLE

        db.commit()

        AuditService.log(
            db=db,
            event_type="BOOKING_CANCELLED",
            user_id=user.id,
            slot_id=slot.id,
            details="Booking cancelled",
        )

        return booking

    @staticmethod
    def validate_booking_limit(db: Session, user: User):
        limit = user.booking_limit_override or 3

        active_bookings = (
            db.query(Booking)
            .filter(Booking.user_id == user.id)
            .filter(Booking.status == BookingStatus.BOOKED)
            .count()
        )

        if active_bookings >= limit:
            raise HTTPException(
                status_code=400,
                detail="Booking limit reached",
            )