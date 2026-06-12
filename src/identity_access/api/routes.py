from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.shared.api import api_error, current_user, require_roles
from src.shared.database import get_connection, row_to_dict, rows_to_list, write_audit_log
from src.shared.security import create_access_token, verify_password

router = APIRouter(prefix="/api/v1", tags=["identity-access"])


class LoginRequest(BaseModel):
    email: str
    password: str


class AssignRolesRequest(BaseModel):
    roles: list[str] = Field(min_length=1)


def user_response(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "firstName": user["first_name"],
        "lastName": user["last_name"],
        "status": user["status"],
        "roles": user.get("roles", []),
    }


def load_roles(connection, user_id: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT r.name
        FROM roles r
        JOIN user_roles ur ON ur.role_id = r.id
        WHERE ur.user_id = ?
        ORDER BY r.name
        """,
        (user_id,),
    ).fetchall()
    return [row["name"] for row in rows]


@router.post("/auth/login")
def login(request: LoginRequest) -> dict[str, Any]:
    with get_connection() as connection:
        user = row_to_dict(connection.execute("SELECT * FROM users WHERE email = ?", (request.email,)).fetchone())
        if not user or not verify_password(request.password, user["password_hash"]):
            raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Invalid email or password.")
        roles = load_roles(connection, user["id"])

    return {"accessToken": create_access_token(user["id"], roles), "tokenType": "bearer", "user": user_response({**user, "roles": roles})}


@router.get("/auth/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return user_response(user)


@router.get("/specialists")
def list_specialists() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT s.id, s.specialization, s.active, u.first_name, u.last_name, u.email
            FROM specialists s
            JOIN users u ON u.id = s.user_id
            WHERE s.active = 1
            ORDER BY u.last_name, u.first_name
            """
        ).fetchall()
    return rows_to_list(rows)


@router.get("/specialists/{specialist_id}")
def get_specialist(specialist_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        specialist = row_to_dict(
            connection.execute(
                """
                SELECT s.id, s.specialization, s.active, u.first_name, u.last_name, u.email
                FROM specialists s
                JOIN users u ON u.id = s.user_id
                WHERE s.id = ?
                """,
                (specialist_id,),
            ).fetchone()
        )
    if not specialist:
        raise api_error(status.HTTP_404_NOT_FOUND, "SPECIALIST_NOT_FOUND", "Specialist was not found.")
    return specialist


@router.get("/users")
def list_users(_: dict[str, Any] = Depends(require_roles("ADMIN"))) -> list[dict[str, Any]]:
    with get_connection() as connection:
        users = rows_to_list(connection.execute("SELECT * FROM users ORDER BY created_at").fetchall())
        for user in users:
            user["roles"] = load_roles(connection, user["id"])
    return [user_response(user) for user in users]


@router.get("/users/{user_id}")
def get_user(user_id: str, _: dict[str, Any] = Depends(require_roles("ADMIN"))) -> dict[str, Any]:
    with get_connection() as connection:
        user = row_to_dict(connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
        if not user:
            raise api_error(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "User was not found.")
        user["roles"] = load_roles(connection, user["id"])
    return user_response(user)


@router.put("/users/{user_id}/roles")
def assign_roles(
    user_id: str,
    request: AssignRolesRequest,
    actor: dict[str, Any] = Depends(require_roles("ADMIN")),
) -> dict[str, Any]:
    with get_connection() as connection:
        user = row_to_dict(connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
        if not user:
            raise api_error(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "User was not found.")

        roles = rows_to_list(
            connection.execute(
                f"SELECT id, name FROM roles WHERE name IN ({','.join('?' for _ in request.roles)})",
                request.roles,
            ).fetchall()
        )
        if len(roles) != len(set(request.roles)):
            raise api_error(status.HTTP_400_BAD_REQUEST, "UNKNOWN_ROLE", "One or more roles do not exist.")

        connection.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        for role in roles:
            connection.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role["id"]))

        user["roles"] = [role["name"] for role in roles]
        write_audit_log(connection, actor["id"], "RoleAssigned", "User", user_id, {"roles": user["roles"]})

    return user_response(user)
