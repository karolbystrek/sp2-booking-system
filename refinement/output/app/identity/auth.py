import logging
from datetime import datetime, timedelta
from typing import List, Optional
import jwt
import bcrypt
from fastapi import Depends, Security
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.exceptions import UnauthorizedException, ForbiddenException
from app.identity.models import User

logger = logging.getLogger(__name__)

# JWT authentication scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def decode_token(token: str, is_refresh: bool = False) -> dict:
    try:
        secret = settings.JWT_REFRESH_SECRET_KEY if is_refresh else settings.JWT_SECRET_KEY
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Verify type matches
        expected_type = "refresh" if is_refresh else "access"
        if payload.get("type") != expected_type:
            raise UnauthorizedException("Invalid token type")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Could not validate credentials")

def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    if not token:
        raise UnauthorizedException("Not authenticated")
    
    payload = decode_token(token, is_refresh=False)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")
        
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise UnauthorizedException("User not found")
        
    return user

class RequireRole:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_roles = [r.name for r in current_user.roles]
        # Admins bypass role checks
        if "Admin" in user_roles or "Administrator" in user_roles:
            return current_user
            
        for role in self.allowed_roles:
            if role in user_roles:
                return current_user
                
        raise ForbiddenException("You do not have permission to access this resource")
