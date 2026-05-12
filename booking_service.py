from datetime import datetime, timedelta

from models import BookingStatus
from schedule_service import ScheduleError


class BookingError(Exception):
    pass


class BookingService:
    def __init__(self, repo, schedule_service, audit_service):
        self.repo = repo
        self.schedule_service = schedule_service
        self.audit_service = audit_service

    def get_available_slots(self, specialist_id: int, date):
        return self.schedule_service.get_available_slots(specialist_id, date)

    def get_user_bookings(self, user_id: int):
        return self.repo.get_user_bookings(user_id)

    def book_slot(self, user_id: int, slot_id: int):
        try:
            slot = self.schedule_service.ensure_slot_available(slot_id)
        except ScheduleError as e:
            self.audit_service.log_booking_rejected(user_id, slot_id, str(e))
            raise BookingError(str(e))

        active_bookings = self.repo.get_user_active_bookings(user_id)
        if len(active_bookings) >= 3:
            self.audit_service.log_booking_rejected(
                user_id, slot_id, "User reached booking limit"
            )
            raise BookingError("User reached booking limit")

        if self.schedule_service.has_time_conflict(user_id, slot):
            self.audit_service.log_booking_rejected(
                user_id, slot_id, "Time conflict detected"
            )
            raise BookingError("User already has overlapping booking")

        self.schedule_service.mark_slot_booked(slot)
        booking = self.repo.create_booking(user_id, slot_id)
        self.audit_service.log_booking_created(user_id, slot_id)
        return booking

    def cancel_booking(self, user_id: int, booking_id: int):
        booking = self.repo.get_booking(booking_id)
        if not booking:
            raise BookingError("Booking does not exist")

        if booking.user_id != user_id:
            raise BookingError("User cannot cancel another user's booking")

        if booking.status != BookingStatus.BOOKED:
            raise BookingError("Booking is not active")

        slot = self.repo.get_slot(booking.slot_id)
        if not slot:
            raise BookingError("Related slot does not exist")

        if slot.start_time - datetime.utcnow() <= timedelta(hours=24):
            raise BookingError("Cancellation too late")

        booking.status = BookingStatus.CANCELLED
        self.repo.save_booking(booking)
        self.schedule_service.restore_slot_after_cancellation(slot)
        self.audit_service.log_booking_cancelled(user_id, slot.id)
        return booking
