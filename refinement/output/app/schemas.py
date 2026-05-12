from datetime import datetime

from pydantic import BaseModel

from app.models import BookingStatus
from app.models import SlotStatus
from app.models import UserRole


class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class BookingCreate(BaseModel):
    slot_id: int


class SlotResponse(BaseModel):
    id: int
    specialist_id: int
    start_time: datetime
    end_time: datetime
    status: SlotStatus

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    id: int
    user_id: int
    slot_id: int
    status: BookingStatus

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    name: str
    role: UserRole

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    user_id: int | None
    slot_id: int | None
    timestamp: datetime
    details: str

    class Config:
        from_attributes = True