from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

booking = pytest.importorskip(
    "src.booking.api.routes",
    reason="The code/e2/gpt implementation has not been integrated yet.",
)


def test_fourth_active_reservation_is_rejected(patient, slot_factory):
    start = datetime.now(timezone.utc) + timedelta(days=7)
    slots = [slot_factory(start_at=start + timedelta(hours=2 * index)) for index in range(4)]

    for slot in slots[:3]:
        booking.create_reservation(
            booking.CreateReservationRequest(slotId=slot["id"]),
            user=patient,
        )

    with pytest.raises(HTTPException) as error:
        booking.create_reservation(
            booking.CreateReservationRequest(slotId=slots[3]["id"]),
            user=patient,
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "ACTIVE_RESERVATION_LIMIT"


def test_overlapping_reservation_for_same_user_is_rejected(patient, slot_factory):
    start = datetime.now(timezone.utc) + timedelta(days=7)
    first = slot_factory(start_at=start, duration_minutes=60)
    overlapping = slot_factory(
        start_at=start + timedelta(minutes=30),
        duration_minutes=60,
    )
    booking.create_reservation(
        booking.CreateReservationRequest(slotId=first["id"]),
        user=patient,
    )

    with pytest.raises(HTTPException) as error:
        booking.create_reservation(
            booking.CreateReservationRequest(slotId=overlapping["id"]),
            user=patient,
        )

    assert error.value.status_code == 409


def test_cancelling_does_not_reopen_a_blocked_slot(
    isolated_database,
    patient,
    slot_factory,
):
    slot = slot_factory(
        start_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    reservation = booking.create_reservation(
        booking.CreateReservationRequest(slotId=slot["id"]),
        user=patient,
    )

    with isolated_database.get_connection() as connection:
        connection.execute(
            "UPDATE time_slots SET status = 'BLOCKED' WHERE id = ?",
            (slot["id"],),
        )

    cancelled = booking.cancel_reservation(reservation["id"], user=patient)

    with isolated_database.get_connection() as connection:
        status = connection.execute(
            "SELECT status FROM time_slots WHERE id = ?",
            (slot["id"],),
        ).fetchone()["status"]

    assert cancelled["status"] == "CANCELLED"
    assert status == "BLOCKED"
