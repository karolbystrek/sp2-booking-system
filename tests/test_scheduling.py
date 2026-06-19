from datetime import date, timedelta

import pytest


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def test_specialist_can_read_own_schedule(client, specialist, auth_headers):
    response = client.get(
        "/api/v1/schedules/me", headers=auth_headers(specialist)
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 1
    assert len(payload["availabilitySlots"]) == 1
    assert payload["availabilitySlots"][0]["start_time"] == "09:00"


def test_patient_cannot_manage_specialist_schedule(
    client, patient, auth_headers
):
    response = client.get(
        "/api/v1/schedules/me", headers=auth_headers(patient)
    )

    assert response.status_code == 403
    assert error_code(response) == "FORBIDDEN"


def test_specialist_role_without_profile_returns_domain_error(
    client, new_user_factory, auth_headers
):
    orphan_specialist = new_user_factory(
        "orphan-specialist@example.com", roles=("SPECIALIST",)
    )

    response = client.get(
        "/api/v1/schedules/me", headers=auth_headers(orphan_specialist)
    )

    assert response.status_code == 404
    assert error_code(response) == "SPECIALIST_NOT_FOUND"


def test_schedule_rejects_invalid_time_range(
    client, specialist, auth_headers
):
    response = client.put(
        "/api/v1/schedules/me",
        json={
            "availabilitySlots": [
                {"dayOfWeek": 1, "startTime": "17:00", "endTime": "09:00"}
            ]
        },
        headers=auth_headers(specialist),
    )

    assert response.status_code == 400
    assert error_code(response) == "INVALID_TIME_RANGE"


def test_schedule_rejects_overlapping_availability_ranges(
    client, specialist, auth_headers
):
    response = client.put(
        "/api/v1/schedules/me",
        json={
            "availabilitySlots": [
                {"dayOfWeek": 1, "startTime": "09:00", "endTime": "12:00"},
                {"dayOfWeek": 1, "startTime": "11:00", "endTime": "14:00"},
            ]
        },
        headers=auth_headers(specialist),
    )

    assert response.status_code == 409
    assert error_code(response) == "SCHEDULE_OVERLAP"


def test_schedule_update_replaces_recurring_availability(
    client, specialist, auth_headers
):
    response = client.put(
        "/api/v1/schedules/me",
        json={
            "availabilitySlots": [
                {"dayOfWeek": 2, "startTime": "10:00", "endTime": "12:00"},
                {"dayOfWeek": 4, "startTime": "13:00", "endTime": "15:00"},
            ]
        },
        headers=auth_headers(specialist),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 2
    assert {
        (slot["day_of_week"], slot["start_time"], slot["end_time"])
        for slot in payload["availabilitySlots"]
    } == {(2, "10:00", "12:00"), (4, "13:00", "15:00")}


@pytest.mark.xfail(
    strict=True,
    reason="Known product defect: generated slots are not synchronized with schedule removal",
)
def test_removing_schedule_removes_future_available_slots(
    client, isolated_database, specialist, auth_headers
):
    """Gold Architecture: free slots are derived from the current schedule."""
    response = client.put(
        "/api/v1/schedules/me",
        json={"availabilitySlots": []},
        headers=auth_headers(specialist),
    )
    assert response.status_code == 200

    with isolated_database.get_connection() as connection:
        specialist_id = connection.execute(
            "SELECT id FROM specialists WHERE user_id = ?",
            (specialist["id"],),
        ).fetchone()["id"]
        remaining = connection.execute(
            """
            SELECT COUNT(*)
            FROM time_slots
            WHERE specialist_id = ? AND status = 'AVAILABLE'
            """,
            (specialist_id,),
        ).fetchone()[0]

    assert remaining == 0


def test_schedule_exception_rejects_invalid_range(
    client, specialist, auth_headers
):
    response = client.post(
        "/api/v1/schedules/me/exceptions",
        json={
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "startTime": "14:00",
            "endTime": "10:00",
            "type": "UNAVAILABLE",
        },
        headers=auth_headers(specialist),
    )

    assert response.status_code == 400
    assert error_code(response) == "INVALID_TIME_RANGE"


def test_schedule_exception_is_persisted(
    client, specialist, auth_headers
):
    exception_date = date.today() + timedelta(days=7)
    create_response = client.post(
        "/api/v1/schedules/me/exceptions",
        json={
            "date": exception_date.isoformat(),
            "startTime": "10:00",
            "endTime": "11:00",
            "type": "UNAVAILABLE",
        },
        headers=auth_headers(specialist),
    )

    assert create_response.status_code == 200
    schedule_response = client.get(
        "/api/v1/schedules/me", headers=auth_headers(specialist)
    )
    assert schedule_response.status_code == 200
    assert schedule_response.json()["exceptions"][0]["date"] == exception_date.isoformat()


def test_availability_returns_only_slots_in_requested_window(
    client, isolated_database
):
    with isolated_database.get_connection() as connection:
        first_slot = connection.execute(
            "SELECT specialist_id, start_at FROM time_slots ORDER BY start_at LIMIT 1"
        ).fetchone()
    slot_date = first_slot["start_at"][:10]

    response = client.get(
        "/api/v1/availability",
        params={
            "specialistId": first_slot["specialist_id"],
            "from": slot_date,
            "to": slot_date,
            "size": 100,
        },
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 8
    assert all(item["status"] == "AVAILABLE" for item in items)
    assert all(item["start_at"].startswith(slot_date) for item in items)

