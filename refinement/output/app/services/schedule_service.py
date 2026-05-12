from sqlalchemy.orm import Session
from ..models import Slot, Booking
from datetime import datetime

def get_slots(db: Session, specialist_id: int = None, date: str = None):
    query = db.query(Slot)
    if specialist_id:
        query = query.filter(Slot.specialist_id == specialist_id)
    if date:
        # Assuming date string 'YYYY-MM-DD'
        query = query.filter(Slot.start_time >= datetime.strptime(date, "%Y-%m-%d"))
        query = query.filter(Slot.start_time < datetime.strptime(date + " 23:59:59", "%Y-%m-%d %H:%M:%S"))
    return query.all()

def create_slot(db: Session, specialist_id: int, start_time: datetime, end_time: datetime):
    slot = Slot(specialist_id=specialist_id, start_time=start_time, end_time=end_time)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot

def get_slot_by_id(db: Session, slot_id: int):
    return db.query(Slot).filter(Slot.id == slot_id).first()

def delete_slot(db: Session, slot_id: int):
    slot = get_slot_by_id(db, slot_id)
    if slot and slot.status == "AVAILABLE":
        db.delete(slot)
        db.commit()
        return True
    return False

def update_slot_status(db: Session, slot_id: int, status: str):
    slot = get_slot_by_id(db, slot_id)
    if slot:
        slot.status = status
        db.commit()
        db.refresh(slot)
    return slot

def has_time_conflict(db: Session, user_id: int, start_time: datetime, end_time: datetime):
    # Get user's active bookings
    bookings = db.query(Booking).filter(
        Booking.user_id == user_id,
        Booking.status == "BOOKED"
    ).all()
    
    for booking in bookings:
        slot = booking.slot
        if max(start_time, slot.start_time) < min(end_time, slot.end_time):
            return True # Overlap found
    return False
