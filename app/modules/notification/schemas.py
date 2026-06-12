from pydantic import BaseModel
from typing import Optional


class NotificationResponse(BaseModel):
    id: str
    recipientId: str
    channel: str
    type: str
    payload: str
    status: str
    sentAt: Optional[str] = None
    createdAt: str


class NotificationPreferencesRequest(BaseModel):
    emailEnabled: bool = True
    pushEnabled: bool = True


class NotificationPreferencesResponse(BaseModel):
    userId: str
    emailEnabled: bool
    pushEnabled: bool
    updatedAt: str
