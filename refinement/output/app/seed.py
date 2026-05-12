from datetime import datetime
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Slot
from app.models import SlotStatus
from app.models import Specialist
from app.models import User
from app.models import UserRole


def seed_data(db: Session):
    if db.query(User).count() > 0:
        return

    admin = User(name="Admin", role=UserRole.ADMIN)
    specialist_user = User(name="Dr. Smith", role=UserRole.SPECIALIST)
    user_1 = User(name="John Doe", role=UserRole.USER)
    user_2 = User(name="Jane Doe", role=UserRole.USER)

    db.add_all([admin, specialist_user, user_1, user_2])
    db.commit()

    specialist = Specialist(
        user_id=specialist_user.id,
        specialization="Dentist",
    )

    db.add(specialist)
    db.commit()

    now = datetime.utcnow() + timedelta(days=2)

    slots = [
        Slot(
            specialist_id=specialist.id,
            start_time=now,
            end_time=now + timedelta(minutes=30),
            status=SlotStatus.AVAILABLE,
        ),
        Slot(
            specialist_id=specialist.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=1, minutes=30),
            status=SlotStatus.AVAILABLE,
        ),
    ]

    db.add_all(slots)
    db.commit()