from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.models import UserRole


ROLE_HIERARCHY = {
    UserRole.USER: 1,
    UserRole.SPECIALIST: 2,
    UserRole.ADMIN: 3,
}


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_current_user(
    x_user_id: int = Header(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == x_user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_role(required_role: UserRole):
    def role_checker(user: User = Depends(get_current_user)):
        if ROLE_HIERARCHY[user.role] < ROLE_HIERARCHY[required_role]:
            raise HTTPException(status_code=403, detail="Access denied")

        return user

    return role_checker