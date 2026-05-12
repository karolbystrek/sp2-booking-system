from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String, nullable=False) # 'USER', 'SPECIALIST', 'ADMIN'
    
    specialist = relationship("Specialist", back_populates="user", uselist=False)
    bookings = relationship("Booking", back_populates="user")

class Specialist(Base):
    __tablename__ = "specialists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    specialization = Column(String, nullable=False)

    user = relationship("User", back_populates="specialist")
    slots = relationship("Slot", back_populates="specialist")

class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    specialist_id = Column(Integer, ForeignKey("specialists.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="AVAILABLE") # 'AVAILABLE', 'BOOKED', 'BLOCKED', 'COMPLETED'

    specialist = relationship("Specialist", back_populates="slots")
    bookings = relationship("Booking", back_populates="slot")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    status = Column(String, nullable=False, default="BOOKED") # 'BOOKED', 'CANCELLED'
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    slot = relationship("Slot", back_populates="bookings")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    user_id = Column(Integer, nullable=True)
    slot_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(String, nullable=True)
