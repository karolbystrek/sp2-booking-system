import logging
from sqlalchemy.orm import Session
from app.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.identity.repository import UserRepository
from app.identity.schemas import UserRegister, UserLogin, Token, UserUpdate
from app.identity.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.identity.models import User
from app.events import event_bus

logger = logging.getLogger(__name__)

class IdentityService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    async def register_user(self, payload: UserRegister) -> User:
        logger.info(f"Attempting to register user: {payload.email}")
        
        # Check if user already exists
        existing = self.repo.get_by_email(payload.email)
        if existing:
            raise ConflictException("A user with this email already exists")

        # Map role string to model, creating role if it doesn't exist
        # Supporting Patient, Specialist, Administrator roles
        # Note: mapping 'admin' or 'administrator' to Admin, etc.
        role_name = payload.role
        if role_name.lower() == "admin":
            role_name = "Admin"
        elif role_name.lower() == "specialist":
            role_name = "Specialist"
        else:
            role_name = "Patient"
            
        role_obj = self.repo.get_role_by_name(role_name)
        if not role_obj:
            role_obj = self.repo.create_role(role_name)

        hashed = hash_password(payload.password)
        
        user = self.repo.create_user(payload, hashed, role_obj)
        
        # Publish UserRegistered event for Event-Driven Architecture (EDA)
        await event_bus.publish("UserRegistered", {
            "user_id": user.user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "roles": [r.name for r in user.roles]
        })
        
        return user

    def login_user(self, payload: UserLogin) -> Token:
        user = self.repo.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedException("Incorrect email or password")

        roles = [role.name for role in user.roles]
        
        access_token = create_access_token(data={"sub": user.user_id, "roles": roles})
        refresh_token = create_refresh_token(data={"sub": user.user_id, "roles": roles})

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600
        )

    def refresh_tokens(self, refresh_token: str) -> Token:
        payload = decode_token(refresh_token, is_refresh=True)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid refresh token payload")
            
        user = self.repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedException("User not found")
            
        roles = [role.name for role in user.roles]
        
        access_token = create_access_token(data={"sub": user.user_id, "roles": roles})
        new_refresh_token = create_refresh_token(data={"sub": user.user_id, "roles": roles})

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=3600
        )

    def get_user_profile(self, user_id: str) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    def update_user_profile(self, user_id: str, payload: UserUpdate) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return self.repo.update_user(user, payload)

    def delete_user(self, user_id: str) -> None:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        self.repo.delete_user(user)

    async def assign_user_role(self, user_id: str, role_name: str) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
            
        role_obj = self.repo.get_role_by_name(role_name)
        if not role_obj:
            role_obj = self.repo.create_role(role_name)
            
        updated_user = self.repo.assign_role(user, role_obj)
        
        await event_bus.publish("UserRoleAssigned", {
            "user_id": updated_user.user_id,
            "roles": [r.name for r in updated_user.roles]
        })
        
        return updated_user

    async def remove_user_role(self, user_id: str, role_name: str) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
            
        role_obj = self.repo.get_role_by_name(role_name)
        if not role_obj:
            raise NotFoundException("Role not found")
            
        updated_user = self.repo.remove_role(user, role_obj)
        
        await event_bus.publish("UserRoleRemoved", {
            "user_id": updated_user.user_id,
            "roles": [r.name for r in updated_user.roles]
        })
        
        return updated_user
