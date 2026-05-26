import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, UniqueConstraint
from app.database import Base

class Reservation(Base):
    __tablename__ = "reservations"

    reservation_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    specialist_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=30)
    status = Column(String(50), nullable=False, default="CONFIRMED")  # 'PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # Ensure a specialist cannot be booked at the exact same start time twice
        UniqueConstraint("specialist_id", "appointment_time", name="uq_specialist_appointment_time"),
    )
