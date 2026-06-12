import sqlite3
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.database import generate_uuid, utcnow

SECRET_KEY = "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, roles: list[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "roles": roles, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE email = ? AND status = 'ACTIVE'", (email,)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return dict(row)


def get_user_roles(conn: sqlite3.Connection, user_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = ?",
        (user_id,),
    ).fetchall()
    return [row["name"] for row in rows]


def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    user = dict(row)
    user["roles"] = get_user_roles(conn, user_id)
    return user


def get_users(conn: sqlite3.Connection, role: str | None = None, status: str | None = None,
              page: int = 0, size: int = 20) -> dict:
    query = "SELECT * FROM users WHERE 1=1"
    count_query = "SELECT COUNT(*) as total FROM users WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status)

    if role:
        query += " AND id IN (SELECT ur.user_id FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE r.name = ?)"
        count_query += " AND id IN (SELECT ur.user_id FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE r.name = ?)"
        params.append(role)

    total = conn.execute(count_query, params).fetchone()["total"]
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    rows = conn.execute(query, params).fetchall()

    users = []
    for row in rows:
        user = dict(row)
        user["roles"] = get_user_roles(conn, user["id"])
        users.append(user)

    return {"content": users, "page": page, "size": size, "totalElements": total}


def create_user(conn: sqlite3.Connection, email: str, name: str, password: str,
                phone: str | None = None, roles: list[str] = None) -> dict:
    user_id = generate_uuid()
    now = utcnow()
    conn.execute(
        "INSERT INTO users (id, email, name, phone, password_hash, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
        (user_id, email, name, phone, hash_password(password), now, now),
    )

    if roles:
        for role_name in roles:
            role_row = conn.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
            if role_row:
                conn.execute(
                    "INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                    (user_id, role_row["id"], now),
                )

    conn.commit()
    return get_user_by_id(conn, user_id)


def update_user(conn: sqlite3.Connection, user_id: str, name: str | None = None,
                phone: str | None = None) -> dict | None:
    user = get_user_by_id(conn, user_id)
    if not user:
        return None

    now = utcnow()
    new_name = name if name else user["name"]
    new_phone = phone if phone is not None else user["phone"]
    conn.execute(
        "UPDATE users SET name = ?, phone = ?, updated_at = ? WHERE id = ?",
        (new_name, new_phone, now, user_id),
    )
    conn.commit()
    return get_user_by_id(conn, user_id)


def deactivate_user(conn: sqlite3.Connection, user_id: str) -> dict | None:
    user = get_user_by_id(conn, user_id)
    if not user:
        return None
    now = utcnow()
    conn.execute("UPDATE users SET status = 'INACTIVE', updated_at = ? WHERE id = ?", (now, user_id))
    conn.commit()
    return get_user_by_id(conn, user_id)


def update_user_roles(conn: sqlite3.Connection, user_id: str, roles: list[str]) -> dict | None:
    user = get_user_by_id(conn, user_id)
    if not user:
        return None
    now = utcnow()
    conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
    for role_name in roles:
        role_row = conn.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
        if role_row:
            conn.execute(
                "INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                (user_id, role_row["id"], now),
            )
    conn.commit()
    return get_user_by_id(conn, user_id)


def get_specialist_by_user_id(conn: sqlite3.Connection, user_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM specialists WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    specialist = dict(row)
    specs = conn.execute(
        "SELECT specialization_code FROM specialist_specializations WHERE specialist_id = ?",
        (specialist["id"],),
    ).fetchall()
    specialist["specializations"] = [s["specialization_code"] for s in specs]
    return specialist
