from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SlotStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class BookingStatus(str, Enum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"


@dataclass
class Slot:
    id: int
    specialist_id: int
    start_time: datetime
    end_time: datetime
    status: SlotStatus = SlotStatus.AVAILABLE


@dataclass
class Booking:
    id: int
    user_id: int
    slot_id: int
    status: BookingStatus
    created_at: datetime
