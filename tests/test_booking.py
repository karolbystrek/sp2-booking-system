import pytest

from booking_service import BookingError
from models import SlotStatus


def test_successful_booking_creates_booking_and_marks_slot(service, repo, slot_factory):
    slot = slot_factory(slot_id=1)
    repo.add_slot(slot)

    booking = service.book_slot(user_id=1, slot_id=1)

    assert booking.user_id == 1
    assert booking.slot_id == 1
    assert booking.status.value == "BOOKED"
    assert repo.get_slot(1).status == SlotStatus.BOOKED
    assert repo.get_booking(booking.id) == booking


def test_double_booking_same_slot_is_rejected(service, repo, slot_factory):
    slot = slot_factory(slot_id=1)
    repo.add_slot(slot)
    first_booking = service.book_slot(user_id=1, slot_id=1)

    with pytest.raises(BookingError, match="Slot is not available"):
        service.book_slot(user_id=2, slot_id=1)

    assert repo.get_slot(1).status == SlotStatus.BOOKED
    assert repo.get_booking(first_booking.id).user_id == 1
    assert len(repo.get_user_active_bookings(2)) == 0


def test_booking_limit_allows_exactly_three_active_bookings(service, repo, slot_factory):
    for slot_id in range(1, 4):
        repo.add_slot(slot_factory(slot_id=slot_id, hours_from_now=48 + slot_id))

    bookings = [service.book_slot(user_id=1, slot_id=slot_id) for slot_id in range(1, 4)]

    assert len(bookings) == 3
    assert len(repo.get_user_active_bookings(1)) == 3
    assert {booking.slot_id for booking in bookings} == {1, 2, 3}


def test_booking_limit_rejects_fourth_booking_without_side_effects(
    service, repo, slot_factory
):
    for slot_id in range(1, 5):
        repo.add_slot(slot_factory(slot_id=slot_id, hours_from_now=48 + slot_id))

    for slot_id in range(1, 4):
        service.book_slot(user_id=1, slot_id=slot_id)

    with pytest.raises(BookingError, match="User reached booking limit"):
        service.book_slot(user_id=1, slot_id=4)

    assert len(repo.get_user_active_bookings(1)) == 3
    assert repo.get_slot(4).status == SlotStatus.AVAILABLE


def test_booking_non_existing_slot_is_rejected(service, repo):
    with pytest.raises(BookingError, match="Slot does not exist"):
        service.book_slot(user_id=1, slot_id=999)

    assert len(repo.get_user_active_bookings(1)) == 0


@pytest.mark.parametrize(
    "slot_status",
    [SlotStatus.BOOKED, SlotStatus.BLOCKED, SlotStatus.COMPLETED],
)
def test_booking_unavailable_slot_status_is_rejected(
    service, repo, slot_factory, slot_status
):
    slot = slot_factory(slot_id=1, status=slot_status)
    repo.add_slot(slot)

    with pytest.raises(BookingError, match="Slot is not available"):
        service.book_slot(user_id=1, slot_id=1)

    assert repo.get_slot(1).status == slot_status
    assert len(repo.get_user_active_bookings(1)) == 0


def test_overlapping_booking_for_same_user_is_rejected(service, repo, slot_factory):
    first_slot = slot_factory(slot_id=1, hours_from_now=48, duration_minutes=30)
    overlapping_slot = slot_factory(slot_id=2, hours_from_now=48, minutes_from_now=15)
    repo.add_slot(first_slot)
    repo.add_slot(overlapping_slot)

    service.book_slot(user_id=1, slot_id=1)

    with pytest.raises(BookingError, match="overlapping booking"):
        service.book_slot(user_id=1, slot_id=2)

    assert repo.get_slot(2).status == SlotStatus.AVAILABLE
    assert len(repo.get_user_active_bookings(1)) == 1


def test_non_overlapping_booking_for_same_user_is_allowed(service, repo, slot_factory):
    first_slot = slot_factory(slot_id=1, hours_from_now=48, duration_minutes=30)
    second_slot = slot_factory(slot_id=2, hours_from_now=49, duration_minutes=30)
    repo.add_slot(first_slot)
    repo.add_slot(second_slot)

    first_booking = service.book_slot(user_id=1, slot_id=1)
    second_booking = service.book_slot(user_id=1, slot_id=2)

    assert first_booking.slot_id == 1
    assert second_booking.slot_id == 2
    assert len(repo.get_user_active_bookings(1)) == 2
