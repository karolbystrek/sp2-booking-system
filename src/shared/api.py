from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.shared.database import get_connection, row_to_dict, rows_to_list
from src.shared.security import decode_access_token

bearer_scheme = HTTPBearer()


def api_error(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "details": details or {}})


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict[str, Any]:
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "Invalid or expired access token.")

    with get_connection() as connection:
        user = row_to_dict(
            connection.execute("SELECT * FROM users WHERE id = ? AND status = 'ACTIVE'", (payload["sub"],)).fetchone()
        )
        if not user:
            raise api_error(status.HTTP_401_UNAUTHORIZED, "USER_NOT_FOUND", "Authenticated user was not found.")
        roles = rows_to_list(
            connection.execute(
                """
                SELECT r.name
                FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = ?
                """,
                (user["id"],),
            ).fetchall()
        )

    user["roles"] = [role["name"] for role in roles]
    return user


def require_roles(*allowed_roles: str):
    def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if not set(user["roles"]).intersection(allowed_roles):
            raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Insufficient permissions.")
        return user

    return dependency
