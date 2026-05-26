from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

class ReservationCreate(BaseModel):
    patient_id: str
    specialist_id: str
    appointment_time: datetime
    duration_minutes: Optional[int] = Field(30, description="Duration in minutes")

class ReservationModify(BaseModel):
    appointment_time: datetime
    duration_minutes: Optional[int] = Field(30, description="Duration in minutes")

class ReservationRead(BaseModel):
    reservation_id: str
    patient_id: str
    specialist_id: str
    appointment_time: datetime
    duration_minutes: int
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
