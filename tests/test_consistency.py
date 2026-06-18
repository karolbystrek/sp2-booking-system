import pytest

from booking_service import BookingError
from models import BookingStatus, SlotStatus


def test_booking_is_consistent_between_booking_slot_and_repository(
    service, repo, slot_factory
):
    slot = slot_factory(slot_id=1)
    repo.add_slot(slot)

    booking = service.book_slot(user_id=1, slot_id=1)

    assert repo.get_booking(booking.id) == booking
    assert repo.get_slot(booking.slot_id).status == SlotStatus.BOOKED
    assert booking in repo.get_user_bookings(1)
    assert booking in repo.get_user_active_bookings(1)


def test_user_booking_list_is_scoped_to_requested_user(service, repo, slot_factory):
    first_user_slot = slot_factory(slot_id=1, hours_from_now=48)
    second_user_slot = slot_factory(slot_id=2, hours_from_now=49)
    repo.add_slot(first_user_slot)
    repo.add_slot(second_user_slot)

    first_user_booking = service.book_slot(user_id=1, slot_id=1)
    second_user_booking = service.book_slot(user_id=2, slot_id=2)

    assert service.get_user_bookings(1) == [first_user_booking]
    assert service.get_user_bookings(2) == [second_user_booking]


def test_cancelled_booking_is_removed_from_active_bookings(service, repo, slot_factory):
    slot = slot_factory(slot_id=1, hours_from_now=48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)

    service.cancel_booking(user_id=1, booking_id=booking.id)

    assert repo.get_booking(booking.id).status == BookingStatus.CANCELLED
    assert repo.get_user_active_bookings(1) == []
    assert service.get_user_bookings(1) == [repo.get_booking(booking.id)]


def test_failed_double_booking_does_not_create_second_booking(
    service, repo, slot_factory
):
    slot = slot_factory(slot_id=1)
    repo.add_slot(slot)
    first_booking = service.book_slot(user_id=1, slot_id=1)

    with pytest.raises(BookingError):
        service.book_slot(user_id=2, slot_id=1)

    assert list(repo.bookings.values()) == [first_booking]
    assert repo.get_user_active_bookings(2) == []
    assert repo.get_slot(1).status == SlotStatus.BOOKED


def test_booking_ids_are_incremental_and_stable(service, repo, slot_factory):
    for slot_id in range(1, 4):
        repo.add_slot(slot_factory(slot_id=slot_id, hours_from_now=48 + slot_id))

    bookings = [service.book_slot(user_id=slot_id, slot_id=slot_id) for slot_id in range(1, 4)]

    assert [booking.id for booking in bookings] == [1, 2, 3]
    assert sorted(repo.bookings.keys()) == [1, 2, 3]
