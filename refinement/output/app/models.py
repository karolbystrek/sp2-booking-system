import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    USER = "USER"
    SPECIALIST = "SPECIALIST"
    ADMIN = "ADMIN"


class SlotStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class BookingStatus(str, enum.Enum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    bookings = relationship("Booking", back_populates="user")
    specialist = relationship("Specialist", back_populates="user", uselist=False)


class Specialist(Base):
    __tablename__ = "specialists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    specialization = Column(String, nullable=False)

    user = relationship("User", back_populates="specialist")
    slots = relationship("Slot", back_populates="specialist")


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True)
    specialist_id = Column(Integer, ForeignKey("specialists.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(SlotStatus), nullable=False, default=SlotStatus.AVAILABLE)

    specialist = relationship("Specialist", back_populates="slots")
    booking = relationship("Booking", back_populates="slot", uselist=False)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.BOOKED)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    slot = relationship("Slot", back_populates="booking")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(String, nullable=True)
