from datetime import datetime, timedelta, timezone


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def test_active_policy_exposes_seeded_business_rules(client):
    response = client.get("/api/v1/policies")

    assert response.status_code == 200
    assert response.json()["maxActiveReservations"] == 3
    assert response.json()["cancellationWindowHours"] == 24
    assert response.json()["activeTo"] is None


def test_admin_can_version_booking_policy(
    client, admin, auth_headers, isolated_database
):
    response = client.put(
        "/api/v1/policies/booking",
        json={"maxActiveReservations": 5, "cancellationWindowHours": 48},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["maxActiveReservations"] == 5
    assert response.json()["cancellationWindowHours"] == 48

    with isolated_database.get_connection() as connection:
        policies = connection.execute(
            "SELECT active_to FROM booking_policies ORDER BY active_from"
        ).fetchall()
    assert len(policies) == 2
    assert sum(policy["active_to"] is None for policy in policies) == 1


def test_patient_cannot_update_booking_policy(
    client, patient, auth_headers
):
    response = client.put(
        "/api/v1/policies/booking",
        json={"maxActiveReservations": 5, "cancellationWindowHours": 48},
        headers=auth_headers(patient),
    )

    assert response.status_code == 403
    assert error_code(response) == "FORBIDDEN"


def test_policy_validation_rejects_nonpositive_limit(
    client, admin, auth_headers
):
    response = client.put(
        "/api/v1/policies/booking",
        json={"maxActiveReservations": 0, "cancellationWindowHours": 24},
        headers=auth_headers(admin),
    )

    assert response.status_code == 422


def test_conflict_exception_requires_specialist_or_slot_scope(
    client, admin, auth_headers
):
    start = datetime.now(timezone.utc)
    response = client.post(
        "/api/v1/conflict-exceptions",
        json={
            "reason": "No scope",
            "activeFrom": start.isoformat(),
            "activeTo": (start + timedelta(hours=1)).isoformat(),
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 400
    assert error_code(response) == "INVALID_EXCEPTION_SCOPE"


def test_conflict_exception_rejects_invalid_time_range(
    client, admin, auth_headers, slot_factory
):
    slot = slot_factory(status="BLOCKED")
    start = datetime.now(timezone.utc)
    response = client.post(
        "/api/v1/conflict-exceptions",
        json={
            "slotId": slot["id"],
            "reason": "Invalid range",
            "activeFrom": start.isoformat(),
            "activeTo": (start - timedelta(minutes=1)).isoformat(),
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 400
    assert error_code(response) == "INVALID_TIME_RANGE"


def test_admin_can_create_list_and_delete_conflict_exception(
    client, admin, auth_headers, slot_factory
):
    slot = slot_factory(status="BLOCKED")
    start = datetime.now(timezone.utc) - timedelta(minutes=1)
    create_response = client.post(
        "/api/v1/conflict-exceptions",
        json={
            "slotId": slot["id"],
            "reason": "Approved override",
            "activeFrom": start.isoformat(),
            "activeTo": (start + timedelta(hours=1)).isoformat(),
        },
        headers=auth_headers(admin),
    )

    assert create_response.status_code == 201
    exception = create_response.json()
    list_response = client.get(
        "/api/v1/conflict-exceptions", headers=auth_headers(admin)
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [exception["id"]]

    delete_response = client.delete(
        f"/api/v1/conflict-exceptions/{exception['id']}",
        headers=auth_headers(admin),
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"status": "deleted"}


def test_deleting_missing_conflict_exception_returns_domain_error(
    client, admin, auth_headers
):
    response = client.delete(
        "/api/v1/conflict-exceptions/missing-exception",
        headers=auth_headers(admin),
    )

    assert response.status_code == 404
    assert error_code(response) == "CONFLICT_EXCEPTION_NOT_FOUND"


def test_audit_log_filters_by_actor_and_entity(
    client, admin, auth_headers
):
    policy_response = client.put(
        "/api/v1/policies/booking",
        json={"maxActiveReservations": 4, "cancellationWindowHours": 24},
        headers=auth_headers(admin),
    )
    policy_id = policy_response.json()["id"]

    response = client.get(
        "/api/v1/audit-logs",
        params={
            "actorId": admin["id"],
            "entityType": "BookingPolicy",
            "entityId": policy_id,
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["eventType"] == "PolicyChanged"
    assert response.json()[0]["payload"] == {
        "maxActiveReservations": 4,
        "cancellationWindowHours": 24,
    }

