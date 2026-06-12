from pydantic import BaseModel
from typing import Optional


class CreateReservationRequest(BaseModel):
    specialistId: str
    timeSlotId: str
    notes: Optional[str] = None


class ReservationResponse(BaseModel):
    id: str
    userId: str
    specialistId: str
    timeSlotId: str
    status: str
    startTime: str
    endTime: str
    specialistName: str
    notes: Optional[str] = None
    cancellationReason: Optional[str] = None
    createdAt: str


class CancelBySpecialistRequest(BaseModel):
    reason: str


class RescheduleRequest(BaseModel):
    newTimeSlotId: str


class ReservationHistoryEntry(BaseModel):
    id: str
    reservationId: str
    action: str
    performedBy: str
    performedRole: str
    details: Optional[str] = None
    createdAt: str


class AdminResolveRequest(BaseModel):
    action: str
    reason: Optional[str] = None
