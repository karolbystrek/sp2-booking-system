from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime

class RoleRead(BaseModel):
    role_id: str
    name: str

    class Config:
        from_attributes = True

class SpecialistDetailsBase(BaseModel):
    specialization: str
    default_appointment_duration_minutes: Optional[int] = 30
    bio: Optional[str] = None
    office_address: Optional[str] = None

class SpecialistDetailsCreate(SpecialistDetailsBase):
    pass

class SpecialistDetailsRead(SpecialistDetailsBase):
    specialist_id: str

    class Config:
        from_attributes = True

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    role: str = Field("Patient", description="Patient, Specialist, or Admin")
    specialist_details: Optional[SpecialistDetailsCreate] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenRefresh(BaseModel):
    refresh_token: str

class UserRead(BaseModel):
    user_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    roles: List[RoleRead]
    specialist_details: Optional[SpecialistDetailsRead] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    specialist_details: Optional[SpecialistDetailsBase] = None

class AssignRolePayload(BaseModel):
    role_name: str
