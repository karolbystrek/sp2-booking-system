import pytest

from booking_service import BookingError
from models import SlotStatus


def test_successful_booking_and_cancellation_are_audited_in_order(
    service, repo, slot_factory
):
    slot = slot_factory(slot_id=1, hours_from_now=48)
    repo.add_slot(slot)

    booking = service.book_slot(user_id=1, slot_id=1)
    service.cancel_booking(user_id=1, booking_id=booking.id)

    events = repo.get_audit_events()
    assert [event.event_type for event in events] == [
        "BOOKING_CREATED",
        "BOOKING_CANCELLED",
    ]
    assert [event.user_id for event in events] == [1, 1]
    assert [event.slot_id for event in events] == [1, 1]


def test_rejected_booking_for_missing_slot_is_audited(service, repo):
    with pytest.raises(BookingError, match="Slot does not exist"):
        service.book_slot(user_id=1, slot_id=999)

    events = repo.get_audit_events()
    assert len(events) == 1
    assert events[0].event_type == "BOOKING_REJECTED"
    assert events[0].user_id == 1
    assert events[0].slot_id == 999
    assert events[0].details == "Slot does not exist"


def test_rejected_booking_by_limit_is_audited(service, repo, slot_factory):
    for slot_id in range(1, 5):
        repo.add_slot(slot_factory(slot_id=slot_id, hours_from_now=48 + slot_id))
    for slot_id in range(1, 4):
        service.book_slot(user_id=1, slot_id=slot_id)

    with pytest.raises(BookingError, match="User reached booking limit"):
        service.book_slot(user_id=1, slot_id=4)

    events = repo.get_audit_events()
    assert events[-1].event_type == "BOOKING_REJECTED"
    assert events[-1].slot_id == 4
    assert events[-1].details == "User reached booking limit"
    assert repo.get_slot(4).status == SlotStatus.AVAILABLE


def test_rejected_booking_by_time_conflict_is_audited(service, repo, slot_factory):
    first_slot = slot_factory(slot_id=1, hours_from_now=48)
    overlapping_slot = slot_factory(slot_id=2, hours_from_now=48, minutes_from_now=15)
    repo.add_slot(first_slot)
    repo.add_slot(overlapping_slot)
    service.book_slot(user_id=1, slot_id=1)

    with pytest.raises(BookingError, match="overlapping booking"):
        service.book_slot(user_id=1, slot_id=2)

    events = repo.get_audit_events()
    assert events[-1].event_type == "BOOKING_REJECTED"
    assert events[-1].user_id == 1
    assert events[-1].slot_id == 2
    assert events[-1].details == "Time conflict detected"
    assert repo.get_slot(2).status == SlotStatus.AVAILABLE


def test_audit_service_returns_repository_audit_log(
    service, audit_service, repo, slot_factory
):
    slot = slot_factory(slot_id=1)
    repo.add_slot(slot)
    service.book_slot(user_id=1, slot_id=1)

    assert audit_service.get_audit_log() == repo.get_audit_events()
