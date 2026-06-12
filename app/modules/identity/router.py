import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.modules.identity.schemas import (
    LoginRequest, TokenResponse, UserResponse, UserCreateRequest,
    UserUpdateRequest, RoleUpdateRequest,
)
from app.modules.identity import service

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    user = service.authenticate_user(conn, request.email, request.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    roles = service.get_user_roles(conn, user["id"])
    token = service.create_access_token(user["id"], roles)
    return TokenResponse(access_token=token)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(current_user: dict = Depends(get_current_user),
                  conn: sqlite3.Connection = Depends(get_db)):
    roles = service.get_user_roles(conn, current_user["id"])
    token = service.create_access_token(current_user["id"], roles)
    return TokenResponse(access_token=token)


@router.get("/users/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user),
           conn: sqlite3.Connection = Depends(get_db)):
    user = service.get_user_by_id(conn, current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user["id"], email=user["email"], name=user["name"],
        phone=user["phone"], status=user["status"],
        roles=user["roles"], created_at=user["created_at"],
    )


@router.get("/admin/users")
def list_users(role: str | None = None, status: str | None = None,
               page: int = 0, size: int = 20,
               current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
               conn: sqlite3.Connection = Depends(get_db)):
    return service.get_users(conn, role=role, status=status, page=page, size=size)


@router.post("/admin/users", response_model=UserResponse, status_code=201)
def create_user(request: UserCreateRequest,
                current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                conn: sqlite3.Connection = Depends(get_db)):
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (request.email,)).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = service.create_user(conn, request.email, request.name, request.password,
                               request.phone, request.roles)
    return UserResponse(
        id=user["id"], email=user["email"], name=user["name"],
        phone=user["phone"], status=user["status"],
        roles=user["roles"], created_at=user["created_at"],
    )


@router.put("/admin/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, request: UserUpdateRequest,
                current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                conn: sqlite3.Connection = Depends(get_db)):
    user = service.update_user(conn, user_id, name=request.name, phone=request.phone)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user["id"], email=user["email"], name=user["name"],
        phone=user["phone"], status=user["status"],
        roles=user["roles"], created_at=user["created_at"],
    )


@router.patch("/admin/users/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: str,
                    current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                    conn: sqlite3.Connection = Depends(get_db)):
    user = service.deactivate_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user["id"], email=user["email"], name=user["name"],
        phone=user["phone"], status=user["status"],
        roles=user["roles"], created_at=user["created_at"],
    )


@router.put("/admin/users/{user_id}/roles", response_model=UserResponse)
def update_roles(user_id: str, request: RoleUpdateRequest,
                 current_user: dict = Depends(require_roles(["ADMINISTRATOR"])),
                 conn: sqlite3.Connection = Depends(get_db)):
    user = service.update_user_roles(conn, user_id, request.roles)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user["id"], email=user["email"], name=user["name"],
        phone=user["phone"], status=user["status"],
        roles=user["roles"], created_at=user["created_at"],
    )
