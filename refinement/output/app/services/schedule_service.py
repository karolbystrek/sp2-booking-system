from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import BookingStatus, Slot, SlotStatus, Specialist


def get_slot(db: Session, slot_id: int) -> Slot:
    slot = db.get(Slot, slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")
    return slot


def get_available_slots(db: Session, specialist_id: int | None = None, date_filter: date | None = None) -> list[Slot]:
    query = db.query(Slot).filter(Slot.status == SlotStatus.AVAILABLE)
    if specialist_id:
        query = query.filter(Slot.specialist_id == specialist_id)
    if date_filter:
        query = query.filter(
            Slot.start_time >= datetime.combine(date_filter, datetime.min.time()),
            Slot.start_time < datetime.combine(date_filter, datetime.max.time()),
        )
    return query.all()


def get_specialist_slots(db: Session, specialist_id: int) -> list[Slot]:
    return db.query(Slot).filter(Slot.specialist_id == specialist_id).all()


def get_specialist_by_user(db: Session, user_id: int) -> Specialist:
    specialist = db.query(Specialist).filter(Specialist.user_id == user_id).first()
    if not specialist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist profile not found")
    return specialist


def add_slot(db: Session, specialist_id: int, start_time: datetime, end_time: datetime) -> Slot:
    slot = Slot(specialist_id=specialist_id, start_time=start_time, end_time=end_time, status=SlotStatus.AVAILABLE)
    db.add(slot)
    db.flush()
    return slot


def delete_slot(db: Session, slot: Slot) -> None:
    if slot.status == SlotStatus.BOOKED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete a booked slot")
    db.delete(slot)
    db.flush()


def block_slot(db: Session, slot: Slot) -> Slot:
    if slot.status == SlotStatus.BOOKED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot block a booked slot")
    slot.status = SlotStatus.BLOCKED
    db.flush()
    return slot


def has_time_conflict(db: Session, user_id: int, new_slot: Slot) -> bool:
    """Check if new_slot overlaps any of the user's active bookings."""
    from app.models import Booking

    active_bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user_id, Booking.status == BookingStatus.BOOKED)
        .all()
    )
    for booking in active_bookings:
        existing = booking.slot
        if existing.start_time < new_slot.end_time and existing.end_time > new_slot.start_time:
            return True
    return False
