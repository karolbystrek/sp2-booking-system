import pytest
from fastapi import HTTPException

identity = pytest.importorskip(
    "src.identity_access.api.routes",
    reason="The code/e2/gpt implementation has not been integrated yet.",
)
scheduling = pytest.importorskip(
    "src.scheduling.api.routes",
    reason="The code/e2/gpt implementation has not been integrated yet.",
)
shared_api = pytest.importorskip(
    "src.shared.api",
    reason="The code/e2/gpt implementation has not been integrated yet.",
)


def test_patient_cannot_use_admin_role_guard(patient):
    require_admin = shared_api.require_roles("ADMIN")

    with pytest.raises(HTTPException) as error:
        require_admin(user=patient)

    assert error.value.status_code == 403
    assert error.value.detail["code"] == "FORBIDDEN"


def test_removing_schedule_removes_future_available_slots(
    isolated_database,
    specialist,
):
    scheduling.update_my_schedule(
        scheduling.ScheduleUpdateRequest(availabilitySlots=[]),
        user=specialist,
    )

    with isolated_database.get_connection() as connection:
        specialist_id = connection.execute(
            "SELECT id FROM specialists WHERE user_id = ?",
            (specialist["id"],),
        ).fetchone()["id"]
        available_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM time_slots
            WHERE specialist_id = ? AND status = 'AVAILABLE'
            """,
            (specialist_id,),
        ).fetchone()[0]

    assert available_count == 0


def test_duplicate_roles_are_rejected(
    isolated_database,
    patient,
    admin,
):
    request = identity.AssignRolesRequest(roles=["PATIENT", "PATIENT"])

    with pytest.raises(HTTPException) as error:
        identity.assign_roles(patient["id"], request, actor=admin)

    assert error.value.status_code == 400
    assert error.value.detail["code"] == "UNKNOWN_ROLE"

    with isolated_database.get_connection() as connection:
        assigned_roles = connection.execute(
            """
            SELECT r.name
            FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = ?
            """,
            (patient["id"],),
        ).fetchall()

    assert [role["name"] for role in assigned_roles] == ["PATIENT"]
