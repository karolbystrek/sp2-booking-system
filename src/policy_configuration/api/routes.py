from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.shared.api import require_roles
from src.shared.database import get_connection, new_id, now_iso, row_to_dict, write_audit_log

router = APIRouter(prefix="/api/v1", tags=["policy-configuration"])


class BookingPolicyRequest(BaseModel):
    maxActiveReservations: int = Field(gt=0)
    cancellationWindowHours: int = Field(ge=0)


def policy_response(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": policy["id"],
        "maxActiveReservations": policy["max_active_reservations"],
        "cancellationWindowHours": policy["cancellation_window_hours"],
        "activeFrom": policy["active_from"],
        "activeTo": policy["active_to"],
    }


@router.get("/policies")
def get_active_policy() -> dict[str, Any]:
    with get_connection() as connection:
        policy = row_to_dict(
            connection.execute(
                "SELECT * FROM booking_policies WHERE active_to IS NULL ORDER BY active_from DESC LIMIT 1"
            ).fetchone()
        )
    return policy_response(policy)


@router.put("/policies/booking")
def update_booking_policy(
    request: BookingPolicyRequest,
    actor: dict[str, Any] = Depends(require_roles("ADMIN")),
) -> dict[str, Any]:
    policy_id = new_id()
    current_time = now_iso()
    with get_connection() as connection:
        connection.execute("UPDATE booking_policies SET active_to = ? WHERE active_to IS NULL", (current_time,))
        connection.execute(
            """
            INSERT INTO booking_policies (
                id, max_active_reservations, cancellation_window_hours, active_from, active_to
            )
            VALUES (?, ?, ?, ?, NULL)
            """,
            (policy_id, request.maxActiveReservations, request.cancellationWindowHours, current_time),
        )
        write_audit_log(connection, actor["id"], "PolicyChanged", "BookingPolicy", policy_id, request.model_dump())
        policy = row_to_dict(connection.execute("SELECT * FROM booking_policies WHERE id = ?", (policy_id,)).fetchone())

    return policy_response(policy)
