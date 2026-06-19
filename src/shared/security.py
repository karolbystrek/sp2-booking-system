import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

JWT_ALGORITHM = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "development-secret-change-before-production")
PASSWORD_SALT = os.getenv("PASSWORD_SALT", "booking-system-salt").encode()


def hash_password(password: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), PASSWORD_SALT, 100_000)
    return base64.b64encode(digest).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def create_access_token(user_id: str, roles: list[str]) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=8)
    payload: dict[str, Any] = {"sub": user_id, "roles": roles, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
