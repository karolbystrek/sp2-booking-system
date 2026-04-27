from datetime import datetime, timedelta

import pytest

from models import Slot, SlotStatus
from repository import InMemoryRepository
from audit_service import AuditService
from booking_service import BookingError, BookingService
from schedule_service import ScheduleService


@pytest.fixture
def repo():
    return InMemoryRepository()


@pytest.fixture
def service(repo):
    schedule_service = ScheduleService(repo)
    audit_service = AuditService(repo)
    return BookingService(repo, schedule_service, audit_service)


def make_slot(
    slot_id: int, specialist_id: int, hours_from_now: int, minutes_from_now: int = 0
):
    start = datetime.utcnow() + timedelta(
        hours=hours_from_now, minutes=minutes_from_now
    )
    end = start + timedelta(minutes=30)
    return Slot(
        id=slot_id,
        specialist_id=specialist_id,
        start_time=start,
        end_time=end,
        status=SlotStatus.AVAILABLE,
    )


def test_get_available_slots_returns_only_available(service, repo):
    s1 = make_slot(1, 10, 48)
    s2 = make_slot(2, 10, 72)
    s2.status = SlotStatus.BOOKED
    repo.add_slot(s1)
    repo.add_slot(s2)
    slots = service.get_available_slots(10, s1.start_time.date())
    assert len(slots) == 1
    assert slots[0].id == 1


def test_successful_booking(service, repo):
    slot = make_slot(1, 10, 48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    assert booking.user_id == 1
    assert booking.slot_id == 1
    assert repo.get_slot(1).status == SlotStatus.BOOKED


def test_booking_limit_enforced(service, repo):
    for i in range(1, 5):
        slot = make_slot(i, 10, 48 + i)
        repo.add_slot(slot)
    service.book_slot(user_id=1, slot_id=1)
    service.book_slot(user_id=1, slot_id=2)
    service.book_slot(user_id=1, slot_id=3)
    with pytest.raises(BookingError):
        service.book_slot(user_id=1, slot_id=4)


def test_double_booking_prevented(service, repo):
    slot = make_slot(1, 10, 48)
    repo.add_slot(slot)
    service.book_slot(user_id=1, slot_id=1)
    with pytest.raises(BookingError):
        service.book_slot(user_id=2, slot_id=1)


def test_successful_cancellation(service, repo):
    slot = make_slot(1, 10, 48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    result = service.cancel_booking(user_id=1, booking_id=booking.id)
    assert result.status.value == "CANCELLED"
    assert repo.get_slot(1).status == SlotStatus.AVAILABLE


def test_late_cancellation_rejected(service, repo):
    slot = make_slot(1, 10, 12)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    with pytest.raises(BookingError):
        service.cancel_booking(user_id=1, booking_id=booking.id)


def test_cannot_cancel_foreign_booking(service, repo):
    slot = make_slot(1, 10, 48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    with pytest.raises(BookingError):
        service.cancel_booking(user_id=2, booking_id=booking.id)


def test_slot_restored_after_cancellation(service, repo):
    slot = make_slot(1, 10, 48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    service.cancel_booking(user_id=1, booking_id=booking.id)
    restored_slot = repo.get_slot(1)
    assert restored_slot.status == SlotStatus.AVAILABLE


def test_overlapping_booking_for_same_user_rejected(service, repo):
    first = make_slot(1, 10, 48)
    overlapping = make_slot(2, 10, 48, 15)
    repo.add_slot(first)
    repo.add_slot(overlapping)
    service.book_slot(user_id=1, slot_id=1)
    with pytest.raises(BookingError, match="overlapping"):
        service.book_slot(user_id=1, slot_id=2)


def test_audit_events_record_booking_and_cancellation(service, repo):
    slot = make_slot(1, 10, 48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    service.cancel_booking(user_id=1, booking_id=booking.id)
    events = repo.get_audit_events()
    assert [event.event_type for event in events] == [
        "BOOKING_CREATED",
        "BOOKING_CANCELLED",
    ]


def test_rejected_booking_is_audited(service, repo):
    with pytest.raises(BookingError):
        service.book_slot(user_id=1, slot_id=999)
    events = repo.get_audit_events()
    assert len(events) == 1
    assert events[0].event_type == "BOOKING_REJECTED"
    assert events[0].details == "Slot does not exist"


def test_blocked_slot_stays_blocked_after_cancellation(service, repo):
    slot = make_slot(1, 10, 48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    repo.get_slot(1).status = SlotStatus.BLOCKED
    service.cancel_booking(user_id=1, booking_id=booking.id)
    assert repo.get_slot(1).status == SlotStatus.BLOCKED
