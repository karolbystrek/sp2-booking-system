from datetime import datetime
from models import Slot, Booking, AuditEvent, BookingStatus


class InMemoryRepository:
    def __init__(self):
        self.slots = {}
        self.bookings = {}
        self.audit_events = {}
        self._booking_id = 1
        self._audit_id = 1

    def add_slot(self, slot: Slot):
        self.slots[slot.id] = slot

    def get_slot(self, slot_id: int):
        return self.slots.get(slot_id)

    def save_slot(self, slot: Slot):
        self.slots[slot.id] = slot

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

    def save_booking(self, booking: Booking):
        self.bookings[booking.id] = booking

    def get_user_active_bookings(self, user_id: int):
        return [
            b
            for b in self.bookings.values()
            if b.user_id == user_id and b.status == BookingStatus.BOOKED
        ]

    def get_user_bookings(self, user_id: int):
        return [b for b in self.bookings.values() if b.user_id == user_id]

    def add_audit_event(
        self, event_type: str, user_id: int, slot_id: int, details: str = ""
    ):
        event = AuditEvent(
            id=self._audit_id,
            event_type=event_type,
            user_id=user_id,
            slot_id=slot_id,
            timestamp=datetime.utcnow(),
            details=details,
        )
        self.audit_events[self._audit_id] = event
        self._audit_id += 1
        return event

    def get_audit_events(self):
        return list(self.audit_events.values())
