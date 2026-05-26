import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, CheckConstraint
from app.database import Base

class SpecialistSchedule(Base):
    __tablename__ = "specialist_schedule"

    block_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    specialist_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    block_type = Column(String(50), nullable=False)  # 'AVAILABLE', 'BREAK', 'HOLIDAY', 'UNAVAILABLE'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="chk_end_time_after_start_time"),
    )
