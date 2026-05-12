from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import User, UserRole
from app.schemas import AuditLogOut, BookingOut, UserOut
from app.services import audit_service, booking_service, user_service

router = APIRouter(tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    return user_service.get_all_users(db)


@router.get("/bookings", response_model=list[BookingOut])
def list_all_bookings(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    return booking_service.get_all_bookings(db)


@router.get("/audit-log", response_model=list[AuditLogOut])
def get_audit_log(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    return audit_service.get_all_logs(db)
