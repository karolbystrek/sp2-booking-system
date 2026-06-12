import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.shared.api import require_roles
from src.shared.database import get_connection, rows_to_list

router = APIRouter(prefix="/api/v1", tags=["audit"])


def audit_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "actorId": row["actor_id"],
        "eventType": row["event_type"],
        "entityType": row["entity_type"],
        "entityId": row["entity_id"],
        "payload": json.loads(row["payload"]),
        "createdAt": row["created_at"],
    }


@router.get("/audit-logs")
def get_audit_logs(
    actorId: str | None = None,
    entityType: str | None = None,
    entityId: str | None = None,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = None,
    _: dict[str, Any] = Depends(require_roles("ADMIN")),
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if actorId:
        clauses.append("actor_id = ?")
        params.append(actorId)
    if entityType:
        clauses.append("entity_type = ?")
        params.append(entityType)
    if entityId:
        clauses.append("entity_id = ?")
        params.append(entityId)
    if from_:
        clauses.append("created_at >= ?")
        params.append(from_.isoformat())
    if to:
        clauses.append("created_at <= ?")
        params.append(to.isoformat())

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM audit_logs {where_clause} ORDER BY created_at DESC LIMIT 100",
            params,
        ).fetchall()
    return [audit_response(row) for row in rows_to_list(rows)]
