from pydantic import BaseModel
from typing import Optional


class SlotResponse(BaseModel):
    slotId: str
    specialistId: str
    specialistName: str
    specialization: Optional[str] = None
    startTime: str
    endTime: str
    status: str


class SlotSearchResponse(BaseModel):
    content: list[SlotResponse]
    page: int
    size: int
    totalElements: int
    totalPages: int


class ScheduleResponse(BaseModel):
    id: str
    specialistId: str
    validFrom: str
    validTo: Optional[str] = None
    isActive: bool
    slots: list[SlotResponse] = []


class SlotCreateRequest(BaseModel):
    startTime: str
    endTime: str
    slotType: str = "STANDARD"


class SlotUpdateRequest(BaseModel):
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    status: Optional[str] = None


class SlotBlockRequest(BaseModel):
    reason: str
