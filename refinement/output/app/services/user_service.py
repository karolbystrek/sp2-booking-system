from sqlalchemy.orm import Session
from ..models import User, Specialist

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session):
    return db.query(User).all()

def is_admin(user: User):
    return user.role == "ADMIN"

def is_specialist(user: User):
    return user.role == "SPECIALIST"
