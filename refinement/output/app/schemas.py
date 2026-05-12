from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    role: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class SlotBase(BaseModel):
    start_time: datetime
    end_time: datetime

class SlotCreate(SlotBase):
    pass

class SlotResponse(SlotBase):
    id: int
    specialist_id: int
    status: str

    class Config:
        from_attributes = True

class BookingBase(BaseModel):
    slot_id: int

class BookingCreate(BookingBase):
    pass

class BookingResponse(BookingBase):
    id: int
    user_id: int
    slot_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    user_id: Optional[int]
    slot_id: Optional[int]
    timestamp: datetime
    details: Optional[str]

    class Config:
        from_attributes = True
