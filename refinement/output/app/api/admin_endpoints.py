from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db
from ..dependencies import get_current_user
from ..services import user_service, booking_service

router = APIRouter(prefix="", tags=["Admin"])

def require_admin(user: models.User = Depends(get_current_user)):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can perform this action")
    return user

@router.get("/users", response_model=List[schemas.UserResponse])
def get_users(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin)
):
    return user_service.get_users(db)

@router.get("/admin/bookings", response_model=List[schemas.BookingResponse])
def get_all_bookings(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin)
):
    return booking_service.get_all_bookings(db)

@router.get("/audit-log", response_model=List[schemas.AuditLogResponse])
def get_audit_log(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin)
):
    return db.query(models.AuditLog).all()
