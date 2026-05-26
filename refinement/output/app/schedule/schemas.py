from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum

class BlockType(str, Enum):
    AVAILABLE = "AVAILABLE"
    BREAK = "BREAK"
    HOLIDAY = "HOLIDAY"
    UNAVAILABLE = "UNAVAILABLE"

class ScheduleBlockBase(BaseModel):
    start_time: datetime
    end_time: datetime
    block_type: BlockType = BlockType.AVAILABLE

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be strictly after start_time")
        return self

class ScheduleBlockCreate(ScheduleBlockBase):
    pass

class ScheduleBlockUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    block_type: Optional[BlockType] = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be strictly after start_time")
        return self

class ScheduleBlockRead(ScheduleBlockBase):
    block_id: str
    specialist_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
