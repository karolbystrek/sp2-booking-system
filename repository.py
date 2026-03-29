from datetime import datetime
from models import Slot, Booking, SlotStatus, BookingStatus


class InMemoryRepository:
    def __init__(self):
        self.slots = {}
        self.bookings = {}
        self._booking_id = 1

    def add_slot(self, slot: Slot):
        self.slots[slot.id] = slot

    def get_slot(self, slot_id: int):
        return self.slots.get(slot_id)

    def get_available_slots(self, specialist_id: int, date):
        result = []
        for slot in self.slots.values():
            if (
                slot.specialist_id == specialist_id
                and slot.start_time.date() == date
                and slot.status == SlotStatus.AVAILABLE
            ):
                result.append(slot)
        return result

    def count_active_bookings_for_user(self, user_id: int):
        return sum(
            1
            for b in self.bookings.values()
            if b.user_id == user_id and b.status == BookingStatus.BOOKED
        )

    def create_booking(self, user_id: int, slot_id: int):
        booking = Booking(
            id=self._booking_id,
            user_id=user_id,
            slot_id=slot_id,
            status=BookingStatus.BOOKED,
            created_at=datetime.utcnow(),
        )
        self.bookings[self._booking_id] = booking
        self._booking_id += 1
        return booking

    def get_booking(self, booking_id: int):
        return self.bookings.get(booking_id)

    def save_slot(self, slot: Slot):
        self.slots[slot.id] = slot

    def save_booking(self, booking: Booking):
        self.bookings[booking.id] = booking
