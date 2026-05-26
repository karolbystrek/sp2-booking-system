from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.identity.auth import get_current_user, RequireRole
from app.identity.models import User
from app.identity.schemas import (
    UserRegister, UserLogin, Token, TokenRefresh, UserRead, UserUpdate, AssignRolePayload, RoleRead
)
from app.identity.service import IdentityService
from app.exceptions import ForbiddenException

router = APIRouter()

@router.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    service = IdentityService(db)
    return await service.register_user(payload)

@router.post("/auth/login", response_model=Token)
async def login(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            payload = UserLogin(**body)
        except Exception:
            from app.exceptions import ValidationException
            raise ValidationException("Invalid JSON credentials")
    else:
        try:
            form_data = await request.form()
            email = form_data.get("username")
            password = form_data.get("password")
            if not email or not password:
                raise Exception()
            payload = UserLogin(email=email, password=password)
        except Exception:
            from app.exceptions import ValidationException
            raise ValidationException("Invalid form data credentials")

    service = IdentityService(db)
    return service.login_user(payload)

@router.post("/auth/refresh", response_model=Token)
async def refresh(payload: TokenRefresh, db: Session = Depends(get_db)):
    service = IdentityService(db)
    return service.refresh_tokens(payload.refresh_token)

@router.get("/auth/verify-token")
async def verify_token(current_user: User = Depends(get_current_user)):
    return {
        "isValid": True,
        "userId": current_user.user_id,
        "roles": [role.name for role in current_user.roles]
    }

@router.get("/users/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/users/me", response_model=UserRead)
async def update_me(payload: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = IdentityService(db)
    return service.update_user_profile(current_user.user_id, payload)

# Admin or Owner
@router.get("/users/{userId}", response_model=UserRead)
async def get_user(
    userId: str, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Allow self or admin
    is_admin = any(r.name in ["Admin", "Administrator"] for r in current_user.roles)
    if current_user.user_id != userId and not is_admin:
        raise ForbiddenException("Access denied")
        
    service = IdentityService(db)
    return service.get_user_profile(userId)

# Admin or Owner
@router.put("/users/{userId}", response_model=UserRead)
async def update_user(
    userId: str,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = any(r.name in ["Admin", "Administrator"] for r in current_user.roles)
    if current_user.user_id != userId and not is_admin:
        raise ForbiddenException("Access denied")
        
    service = IdentityService(db)
    return service.update_user_profile(userId, payload)

# Admin or Owner
@router.delete("/users/{userId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    userId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = any(r.name in ["Admin", "Administrator"] for r in current_user.roles)
    if current_user.user_id != userId and not is_admin:
        raise ForbiddenException("Access denied")
        
    service = IdentityService(db)
    service.delete_user(userId)
    return None

# Admin only
@router.get("/users/{userId}/roles", response_model=List[RoleRead])
async def get_user_roles(
    userId: str,
    current_user: User = Depends(RequireRole(["Admin", "Administrator"])),
    db: Session = Depends(get_db)
):
    service = IdentityService(db)
    user = service.get_user_profile(userId)
    return user.roles

# Admin only
@router.post("/users/{userId}/roles", response_model=UserRead)
async def assign_role(
    userId: str,
    payload: AssignRolePayload,
    current_user: User = Depends(RequireRole(["Admin", "Administrator"])),
    db: Session = Depends(get_db)
):
    service = IdentityService(db)
    return await service.assign_user_role(userId, payload.role_name)

# Admin only
@router.delete("/users/{userId}/roles/{roleId}", response_model=UserRead)
async def remove_role(
    userId: str,
    roleId: str,
    current_user: User = Depends(RequireRole(["Admin", "Administrator"])),
    db: Session = Depends(get_db)
):
    service = IdentityService(db)
    # Find role by role_id to get the name
    role_obj = db.query(service.repo.get_role_by_name("Dummy").__class__).filter_by(role_id=roleId).first()
    if not role_obj:
        from app.exceptions import NotFoundException
        raise NotFoundException("Role not found")
        
    return await service.remove_user_role(userId, role_obj.name)
