import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    template_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True) # e.g. 'RESERVATION_CREATED', etc.
    subject_template = Column(Text, nullable=False)
    body_template = Column(Text, nullable=False)
    channel = Column(String(50), nullable=False) # 'EMAIL', 'SMS'

    logs = relationship("NotificationLog", back_populates="template", cascade="all, delete-orphan")

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    log_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(String(36), ForeignKey("notification_templates.template_id", ondelete="SET NULL"), nullable=True)
    channel = Column(String(50), nullable=False) # 'EMAIL', 'SMS'
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING") # 'PENDING', 'SENT', 'FAILED'
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("NotificationTemplate", back_populates="logs")
