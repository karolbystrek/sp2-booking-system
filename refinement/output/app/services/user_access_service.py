from fastapi import HTTPException

from app.models import Booking
from app.models import Slot
from app.models import Specialist
from app.models import User
from app.models import UserRole


class UserAccessService:
    @staticmethod
    def validate_specialist_ownership(user: User, specialist: Specialist):
        if user.role != UserRole.SPECIALIST:
            raise HTTPException(status_code=403, detail="Specialist access required")

        if specialist.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    @staticmethod
    def validate_booking_access(user: User, booking: Booking):
        if user.role == UserRole.ADMIN:
            return

        if booking.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    @staticmethod
    def validate_slot_access(user: User, slot: Slot, specialist: Specialist):
        if user.role == UserRole.ADMIN:
            return

        if specialist.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")