from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Booking, BookingStatus, Slot, SlotStatus, Specialist, User, UserRole


def seed():
    db: Session = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return  # Already seeded

        users = [
            User(id=1, name="Alice", role=UserRole.USER),
            User(id=2, name="Bob", role=UserRole.USER),
            User(id=3, name="Carol", role=UserRole.SPECIALIST),
            User(id=4, name="Dave", role=UserRole.SPECIALIST),
            User(id=5, name="Eve", role=UserRole.ADMIN),
        ]
        db.add_all(users)
        db.flush()

        specialists = [
            Specialist(id=1, user_id=3, specialization="Cardiology"),
            Specialist(id=2, user_id=4, specialization="Dermatology"),
        ]
        db.add_all(specialists)
        db.flush()

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        slots = [
            Slot(id=1, specialist_id=1, start_time=now + timedelta(days=1), end_time=now + timedelta(days=1, minutes=30), status=SlotStatus.AVAILABLE),
            Slot(id=2, specialist_id=1, start_time=now + timedelta(days=1, hours=1), end_time=now + timedelta(days=1, hours=1, minutes=30), status=SlotStatus.AVAILABLE),
            Slot(id=3, specialist_id=1, start_time=now + timedelta(days=2), end_time=now + timedelta(days=2, minutes=30), status=SlotStatus.BLOCKED),
            Slot(id=4, specialist_id=2, start_time=now + timedelta(days=1), end_time=now + timedelta(days=1, minutes=30), status=SlotStatus.AVAILABLE),
            Slot(id=5, specialist_id=2, start_time=now + timedelta(days=3), end_time=now + timedelta(days=3, minutes=30), status=SlotStatus.AVAILABLE),
            Slot(id=6, specialist_id=2, start_time=now + timedelta(days=4), end_time=now + timedelta(days=4, minutes=30), status=SlotStatus.BOOKED),
        ]
        db.add_all(slots)
        db.flush()

        bookings = [
            Booking(id=1, user_id=1, slot_id=6, status=BookingStatus.BOOKED),
        ]
        db.add_all(bookings)

        db.commit()
        print("Database seeded with test data.")
    finally:
        db.close()
