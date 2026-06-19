from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def test_patient_can_create_and_read_reservation(
    client, patient, auth_headers, slot_factory, book_slot
):
    slot = slot_factory()

    created = book_slot(patient, slot)
    reservation = created.json()

    assert reservation["slotId"] == slot["id"]
    assert reservation["userId"] == patient["id"]
    assert reservation["status"] == "CREATED"

    fetched = client.get(
        f"/api/v1/reservations/{reservation['id']}",
        headers=auth_headers(patient),
    )
    assert fetched.status_code == 200
    assert fetched.json() == reservation


def test_booking_nonexistent_slot_returns_domain_error(
    client, patient, auth_headers
):
    response = client.post(
        "/api/v1/reservations",
        json={"slotId": "missing-slot"},
        headers=auth_headers(patient),
    )

    assert response.status_code == 404
    assert error_code(response) == "SLOT_NOT_FOUND"


def test_fourth_active_reservation_is_rejected(
    client, patient, auth_headers, slot_factory, book_slot
):
    start = datetime.now(timezone.utc) + timedelta(days=7)
    slots = [
        slot_factory(start_at=start + timedelta(hours=2 * index))
        for index in range(4)
    ]
    for slot in slots[:3]:
        book_slot(patient, slot)

    response = client.post(
        "/api/v1/reservations",
        json={"slotId": slots[3]["id"]},
        headers=auth_headers(patient),
    )

    assert response.status_code == 409
    assert error_code(response) == "ACTIVE_RESERVATION_LIMIT"


def test_second_booking_for_same_slot_is_rejected(
    client,
    patient,
    new_user_factory,
    auth_headers,
    slot_factory,
    book_slot,
):
    another_patient = new_user_factory("another-patient@example.com")
    slot = slot_factory()
    book_slot(patient, slot)

    response = client.post(
        "/api/v1/reservations",
        json={"slotId": slot["id"]},
        headers=auth_headers(another_patient),
    )

    assert response.status_code == 409
    assert error_code(response) == "SLOT_ALREADY_BOOKED"


def test_concurrent_booking_allows_exactly_one_active_reservation(
    client,
    patient,
    new_user_factory,
    auth_headers,
    slot_factory,
    isolated_database,
):
    another_patient = new_user_factory("concurrent-patient@example.com")
    slot = slot_factory()

    def reserve(user):
        return client.post(
            "/api/v1/reservations",
            json={"slotId": slot["id"]},
            headers=auth_headers(user),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(reserve, [patient, another_patient]))

    assert sorted(response.status_code for response in responses) == [201, 409]
    with isolated_database.get_connection() as connection:
        active_count = connection.execute(
            """
            SELECT COUNT(*) FROM reservations
            WHERE slot_id = ? AND status IN ('CREATED', 'CONFIRMED')
            """,
            (slot["id"],),
        ).fetchone()[0]
    assert active_count == 1


@pytest.mark.xfail(
    strict=True,
    reason="Known product defect: conflicting reservations are not rejected",
)
def test_overlapping_reservation_for_same_user_is_rejected(
    client, patient, auth_headers, slot_factory, book_slot
):
    """Gold Architecture: a conflicting reservation must be rejected."""
    start = datetime.now(timezone.utc) + timedelta(days=7)
    first = slot_factory(start_at=start, duration_minutes=60)
    overlapping = slot_factory(
        start_at=start + timedelta(minutes=30), duration_minutes=60
    )
    book_slot(patient, first)

    response = client.post(
        "/api/v1/reservations",
        json={"slotId": overlapping["id"]},
        headers=auth_headers(patient),
    )

    assert response.status_code == 409
    assert error_code(response) == "CONFLICT_DETECTED"


def test_booking_blocked_slot_is_rejected(
    client, patient, auth_headers, slot_factory
):
    slot = slot_factory(status="BLOCKED")

    response = client.post(
        "/api/v1/reservations",
        json={"slotId": slot["id"]},
        headers=auth_headers(patient),
    )

    assert response.status_code == 409
    assert error_code(response) == "CONFLICT_DETECTED"


def test_active_conflict_exception_allows_blocked_slot(
    client, patient, admin, auth_headers, slot_factory
):
    slot = slot_factory(status="BLOCKED")
    now = datetime.now(timezone.utc)
    exception = client.post(
        "/api/v1/conflict-exceptions",
        json={
            "slotId": slot["id"],
            "reason": "Approved conflict override",
            "activeFrom": (now - timedelta(minutes=1)).isoformat(),
            "activeTo": (now + timedelta(hours=1)).isoformat(),
        },
        headers=auth_headers(admin),
    )
    assert exception.status_code == 201

    response = client.post(
        "/api/v1/reservations",
        json={"slotId": slot["id"]},
        headers=auth_headers(patient),
    )

    assert response.status_code == 201
    assert response.json()["slotId"] == slot["id"]


def test_cancellation_restores_slot_and_writes_audit_events(
    client,
    patient,
    admin,
    auth_headers,
    slot_factory,
    book_slot,
    isolated_database,
):
    slot = slot_factory(start_at=datetime.now(timezone.utc) + timedelta(days=7))
    reservation = book_slot(patient, slot).json()

    cancelled = client.delete(
        f"/api/v1/reservations/{reservation['id']}",
        headers=auth_headers(patient),
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    with isolated_database.get_connection() as connection:
        status = connection.execute(
            "SELECT status FROM time_slots WHERE id = ?", (slot["id"],)
        ).fetchone()["status"]
    assert status == "AVAILABLE"

    audit = client.get(
        "/api/v1/audit-logs",
        params={"entityId": reservation["id"]},
        headers=auth_headers(admin),
    )
    assert audit.status_code == 200
    assert [event["eventType"] for event in reversed(audit.json())] == [
        "ReservationCreated",
        "ReservationCancelled",
    ]


def test_cancellation_inside_policy_window_is_rejected(
    client, patient, auth_headers, slot_factory, book_slot
):
    slot = slot_factory(start_at=datetime.now(timezone.utc) + timedelta(hours=12))
    reservation = book_slot(patient, slot).json()

    response = client.delete(
        f"/api/v1/reservations/{reservation['id']}",
        headers=auth_headers(patient),
    )

    assert response.status_code == 409
    assert error_code(response) == "CANCELLATION_WINDOW_CLOSED"


def test_admin_can_cancel_other_users_reservation_inside_policy_window(
    client, patient, admin, auth_headers, slot_factory, book_slot
):
    slot = slot_factory(start_at=datetime.now(timezone.utc) + timedelta(hours=12))
    reservation = book_slot(patient, slot).json()

    response = client.delete(
        f"/api/v1/reservations/{reservation['id']}",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_created_reservation_can_be_confirmed_once(
    client, patient, auth_headers, slot_factory, book_slot
):
    reservation = book_slot(patient, slot_factory()).json()

    first = client.post(
        f"/api/v1/reservations/{reservation['id']}/confirm",
        headers=auth_headers(patient),
    )
    second = client.post(
        f"/api/v1/reservations/{reservation['id']}/confirm",
        headers=auth_headers(patient),
    )

    assert first.status_code == 200
    assert first.json()["status"] == "CONFIRMED"
    assert second.status_code == 409
    assert error_code(second) == "INVALID_RESERVATION_STATUS"


def test_missing_reservation_returns_domain_error(
    client, patient, auth_headers
):
    response = client.get(
        "/api/v1/reservations/missing-reservation",
        headers=auth_headers(patient),
    )

    assert response.status_code == 404
    assert error_code(response) == "RESERVATION_NOT_FOUND"


def test_other_patient_cannot_read_or_cancel_reservation(
    client,
    patient,
    new_user_factory,
    auth_headers,
    slot_factory,
    book_slot,
):
    another_patient = new_user_factory("unauthorized-patient@example.com")
    reservation = book_slot(patient, slot_factory()).json()

    read_response = client.get(
        f"/api/v1/reservations/{reservation['id']}",
        headers=auth_headers(another_patient),
    )
    cancel_response = client.delete(
        f"/api/v1/reservations/{reservation['id']}",
        headers=auth_headers(another_patient),
    )

    assert read_response.status_code == 403
    assert cancel_response.status_code == 403
    assert error_code(read_response) == "FORBIDDEN"
    assert error_code(cancel_response) == "FORBIDDEN"


def test_user_reservation_list_is_isolated(
    client,
    patient,
    new_user_factory,
    auth_headers,
    slot_factory,
    book_slot,
):
    another_patient = new_user_factory("list-patient@example.com")
    own_reservation = book_slot(patient, slot_factory()).json()
    book_slot(another_patient, slot_factory())

    response = client.get(
        "/api/v1/users/me/reservations",
        headers=auth_headers(patient),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own_reservation["id"]]

