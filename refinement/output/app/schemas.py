from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models import BookingStatus, SlotStatus, UserRole


# --- User ---

class UserOut(BaseModel):
    id: int
    name: str
    role: UserRole

    model_config = {"from_attributes": True}


# --- Specialist ---

class SpecialistOut(BaseModel):
    id: int
    user_id: int
    specialization: str

    model_config = {"from_attributes": True}


# --- Slot ---

class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class SlotOut(BaseModel):
    id: int
    specialist_id: int
    start_time: datetime
    end_time: datetime
    status: SlotStatus

    model_config = {"from_attributes": True}


# --- Booking ---

class BookingCreate(BaseModel):
    slot_id: int


class BookingOut(BaseModel):
    id: int
    user_id: int
    slot_id: int
    status: BookingStatus
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Audit ---

class AuditLogOut(BaseModel):
    id: int
    event_type: str
    user_id: Optional[int]
    slot_id: Optional[int]
    timestamp: datetime
    details: Optional[str]

    model_config = {"from_attributes": True}
