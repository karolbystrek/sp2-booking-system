from pydantic import BaseModel
from typing import Optional


class SystemConfigResponse(BaseModel):
    minCancellationHours: int
    maxAdvanceBookingDays: int
    maxReservationsPerUser: int
    updatedBy: Optional[str] = None
    updatedAt: Optional[str] = None


class SystemConfigUpdateRequest(BaseModel):
    minCancellationHours: int = 24
    maxAdvanceBookingDays: int = 90
    maxReservationsPerUser: int = 5


class ConflictExceptionResponse(BaseModel):
    id: str
    type: str
    description: str
    maxOverlapping: int
    isActive: bool
    createdBy: str
    createdAt: str


class ConflictExceptionCreateRequest(BaseModel):
    type: str
    description: str
    maxOverlapping: int = 2


class AuditLogResponse(BaseModel):
    id: str
    action: str
    performedBy: str
    performedRole: Optional[str] = None
    entityType: str
    entityId: Optional[str] = None
    details: Optional[str] = None
    createdAt: str


class ReportResponse(BaseModel):
    type: str
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None
    data: dict
