from sqlalchemy.orm import Session

from app.models import User, UserRole


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_all_users(db: Session) -> list[User]:
    return db.query(User).all()


def is_specialist(user: User) -> bool:
    return user.role == UserRole.SPECIALIST


def is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN
