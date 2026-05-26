from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

class AvailableSlot(BaseModel):
    start_time: datetime = Field(..., serialization_alias="startTime")
    end_time: datetime = Field(..., serialization_alias="endTime")

    class Config:
        populate_by_name = True

class SpecialistAvailabilityResponse(BaseModel):
    specialist_id: str = Field(..., serialization_alias="specialistId")
    specialist_name: str = Field(..., serialization_alias="specialistName")
    specialization: str = Field(..., serialization_alias="specialization")
    available_slots: List[AvailableSlot] = Field(..., serialization_alias="availableSlots")

    class Config:
        populate_by_name = True
