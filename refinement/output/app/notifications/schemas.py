from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NotificationTemplateCreate(BaseModel):
    name: str
    subject_template: str
    body_template: str
    channel: str

class NotificationTemplateRead(BaseModel):
    template_id: str
    name: str
    subject_template: str
    body_template: str
    channel: str

    class Config:
        from_attributes = True

class NotificationLogRead(BaseModel):
    log_id: str
    user_id: Optional[str] = None
    template_id: Optional[str] = None
    channel: str
    recipient: str
    subject: Optional[str] = None
    body: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
