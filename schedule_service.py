from models import SlotStatus


class ScheduleError(Exception):
    pass


class ScheduleService:
    def __init__(self, repo):
        self.repo = repo

    def get_available_slots(self, specialist_id: int, date):
        result = []
        for slot in self.repo.slots.values():
            if (
                slot.specialist_id == specialist_id
                and slot.start_time.date() == date
                and slot.status == SlotStatus.AVAILABLE
            ):
                result.append(slot)
        return result

    def ensure_slot_available(self, slot_id: int):
        slot = self.repo.get_slot(slot_id)
        if not slot:
            raise ScheduleError("Slot does not exist")
        if slot.status != SlotStatus.AVAILABLE:
            raise ScheduleError("Slot is not available")
        return slot

    def has_time_conflict(self, user_id: int, candidate_slot):
        user_bookings = self.repo.get_user_active_bookings(user_id)
        for booking in user_bookings:
            booked_slot = self.repo.get_slot(booking.slot_id)
            if booked_slot is None:
                continue
            overlaps = not (
                candidate_slot.end_time <= booked_slot.start_time
                or candidate_slot.start_time >= booked_slot.end_time
            )
            if overlaps:
                return True
        return False

    def mark_slot_booked(self, slot):
        slot.status = SlotStatus.BOOKED
        self.repo.save_slot(slot)

    def restore_slot_after_cancellation(self, slot):
        if slot.status != SlotStatus.BLOCKED:
            slot.status = SlotStatus.AVAILABLE
        self.repo.save_slot(slot)
