from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Booking
from app.models import BookingStatus
from app.models import Slot
from app.models import SlotStatus


class ScheduleService:
    @staticmethod
    def get_available_slots(
        db: Session,
        specialist_id: int,
        selected_date: date,
    ):
        return (
            db.query(Slot)
            .filter(Slot.specialist_id == specialist_id)
            .filter(Slot.status == SlotStatus.AVAILABLE)
            .filter(Slot.start_time >= selected_date)
            .filter(Slot.start_time < date.fromordinal(selected_date.toordinal() + 1))
            .all()
        )

    @staticmethod
    def get_slot(db: Session, slot_id: int):
        slot = db.query(Slot).filter(Slot.id == slot_id).first()

        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")

        return slot

    @staticmethod
    def validate_slot_available(slot: Slot):
        if slot.status != SlotStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail="Slot is not available")

    @staticmethod
    def validate_time_conflict(db: Session, user_id: int, slot: Slot):
        active_bookings = (
            db.query(Booking)
            .join(Slot, Booking.slot_id == Slot.id)
            .filter(Booking.user_id == user_id)
            .filter(Booking.status == BookingStatus.BOOKED)
            .all()
        )

        for booking in active_bookings:
            existing_slot = booking.slot

            overlaps = (
                slot.start_time < existing_slot.end_time
                and slot.end_time > existing_slot.start_time
            )

            if overlaps:
                raise HTTPException(
                    status_code=400,
                    detail="Booking conflict detected",
                )