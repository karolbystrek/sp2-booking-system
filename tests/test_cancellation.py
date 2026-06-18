import pytest

from booking_service import BookingError
from models import BookingStatus, SlotStatus


def test_successful_cancellation_changes_booking_status_and_restores_slot(
    service, repo, slot_factory
):
    slot = slot_factory(slot_id=1, hours_from_now=48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)

    cancelled_booking = service.cancel_booking(user_id=1, booking_id=booking.id)

    assert cancelled_booking.status == BookingStatus.CANCELLED
    assert repo.get_booking(booking.id).status == BookingStatus.CANCELLED
    assert repo.get_slot(1).status == SlotStatus.AVAILABLE


def test_late_cancellation_is_rejected_without_state_change(service, repo, slot_factory):
    slot = slot_factory(slot_id=1, hours_from_now=12)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)

    with pytest.raises(BookingError, match="Cancellation too late"):
        service.cancel_booking(user_id=1, booking_id=booking.id)

    assert repo.get_booking(booking.id).status == BookingStatus.BOOKED
    assert repo.get_slot(1).status == SlotStatus.BOOKED


def test_user_cannot_cancel_foreign_booking(service, repo, slot_factory):
    slot = slot_factory(slot_id=1, hours_from_now=48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)

    with pytest.raises(BookingError, match="another user's booking"):
        service.cancel_booking(user_id=2, booking_id=booking.id)

    assert repo.get_booking(booking.id).status == BookingStatus.BOOKED
    assert repo.get_slot(1).status == SlotStatus.BOOKED


def test_cancelling_non_existing_booking_is_rejected(service):
    with pytest.raises(BookingError, match="Booking does not exist"):
        service.cancel_booking(user_id=1, booking_id=999)


def test_cannot_cancel_same_booking_twice(service, repo, slot_factory):
    slot = slot_factory(slot_id=1, hours_from_now=48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    service.cancel_booking(user_id=1, booking_id=booking.id)

    with pytest.raises(BookingError, match="Booking is not active"):
        service.cancel_booking(user_id=1, booking_id=booking.id)

    assert repo.get_booking(booking.id).status == BookingStatus.CANCELLED
    assert repo.get_slot(1).status == SlotStatus.AVAILABLE


def test_cancellation_is_rejected_when_related_slot_is_missing(
    service, repo, slot_factory
):
    slot = slot_factory(slot_id=1, hours_from_now=48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    del repo.slots[1]

    with pytest.raises(BookingError, match="Related slot does not exist"):
        service.cancel_booking(user_id=1, booking_id=booking.id)

    assert repo.get_booking(booking.id).status == BookingStatus.BOOKED


def test_blocked_slot_stays_blocked_after_cancellation(service, repo, slot_factory):
    slot = slot_factory(slot_id=1, hours_from_now=48)
    repo.add_slot(slot)
    booking = service.book_slot(user_id=1, slot_id=1)
    repo.get_slot(1).status = SlotStatus.BLOCKED

    cancelled_booking = service.cancel_booking(user_id=1, booking_id=booking.id)

    assert cancelled_booking.status == BookingStatus.CANCELLED
    assert repo.get_slot(1).status == SlotStatus.BLOCKED


def test_cancelled_slot_can_be_booked_again_by_another_user(service, repo, slot_factory):
    slot = slot_factory(slot_id=1, hours_from_now=48)
    repo.add_slot(slot)
    first_booking = service.book_slot(user_id=1, slot_id=1)
    service.cancel_booking(user_id=1, booking_id=first_booking.id)

    second_booking = service.book_slot(user_id=2, slot_id=1)

    assert second_booking.user_id == 2
    assert second_booking.slot_id == 1
    assert repo.get_slot(1).status == SlotStatus.BOOKED
