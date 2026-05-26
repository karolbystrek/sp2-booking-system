import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Date, Integer, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base

# Association table for User <-> Role (Many-to-Many)
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)
)

class Role(Base):
    __tablename__ = "roles"

    role_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False)

    users = relationship("User", secondary=user_roles, back_populates="roles")

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = relationship("Role", secondary=user_roles, back_populates="users", lazy="joined")
    specialist_details = relationship("SpecialistDetails", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="joined")

class SpecialistDetails(Base):
    __tablename__ = "specialist_details"

    specialist_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    specialization = Column(String(100), nullable=False)
    default_appointment_duration_minutes = Column(Integer, default=30)
    bio = Column(Text, nullable=True)
    office_address = Column(String(255), nullable=True)

    user = relationship("User", back_populates="specialist_details")
