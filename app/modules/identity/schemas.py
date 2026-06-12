from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: Optional[str] = None
    status: str
    roles: list[str] = []
    created_at: str


class UserCreateRequest(BaseModel):
    email: str
    name: str
    phone: Optional[str] = None
    password: str
    roles: list[str] = ["USER"]


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class RoleUpdateRequest(BaseModel):
    roles: list[str]


class SpecialistResponse(BaseModel):
    id: str
    user_id: str
    bio: Optional[str] = None
    office_location: Optional[str] = None
    specializations: list[str] = []
