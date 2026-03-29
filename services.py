from datetime import datetime, timedelta
from models import SlotStatus, BookingStatus


class BookingError(Exception):
    pass


class BookingService:
    def __init__(self, repo):
        self.repo = repo

    def get_available_slots(self, specialist_id: int, date):
        return self.repo.get_available_slots(specialist_id, date)

    def book_slot(self, user_id: int, slot_id: int):
        slot = self.repo.get_slot(slot_id)
        if not slot:
            raise BookingError("Slot does not exist")
        if slot.status != SlotStatus.AVAILABLE:
            raise BookingError("Slot is not available")
        active = self.repo.count_active_bookings_for_user(user_id)
        if active >= 3:
            raise BookingError("User reached booking limit")
        slot.status = SlotStatus.BOOKED
        self.repo.save_slot(slot)
        booking = self.repo.create_booking(user_id, slot_id)
        return booking

    def cancel_booking(self, user_id: int, booking_id: int):
        booking = self.repo.get_booking(booking_id)
        if not booking:
            raise BookingError("Booking does not exist")
        if booking.user_id != user_id:
            raise BookingError("User cannot cancel чужую booking")
        if booking.status != BookingStatus.BOOKED:
            raise BookingError("Booking is not active")
        slot = self.repo.get_slot(booking.slot_id)
        if not slot:
            raise BookingError("Related slot does not exist")
        if slot.start_time - datetime.utcnow() < timedelta(hours=24):
            raise BookingError("Cancellation too late")
        booking.status = BookingStatus.CANCELLED
        slot.status = SlotStatus.AVAILABLE
        self.repo.save_booking(booking)
        self.repo.save_slot(slot)
        return booking
