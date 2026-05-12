from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.dependencies import require_role
from app.models import AuditLog
from app.models import Booking
from app.models import User
from app.models import UserRole
from app.schemas import AuditLogResponse
from app.schemas import BookingResponse
from app.schemas import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    return db.query(User).all()


@router.get("/bookings", response_model=list[BookingResponse])
def get_bookings(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    return db.query(Booking).all()


@router.get("/audit-log", response_model=list[AuditLogResponse])
def get_audit_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    return db.query(AuditLog).all()