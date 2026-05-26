from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.identity.auth import get_current_user, RequireRole
from app.identity.models import User
from app.exceptions import ForbiddenException
from app.notifications.schemas import NotificationTemplateCreate, NotificationTemplateRead, NotificationLogRead
from app.notifications.service import NotificationService

router = APIRouter()

@router.post(
    "/notification-templates",
    response_model=NotificationTemplateRead,
    status_code=status.HTTP_201_CREATED
)
def create_template(
    payload: NotificationTemplateCreate,
    current_user: User = Depends(RequireRole(["Admin", "Administrator"])),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    return service.create_template(payload)

@router.get(
    "/notification-templates",
    response_model=List[NotificationTemplateRead]
)
def get_templates(
    current_user: User = Depends(RequireRole(["Admin", "Administrator"])),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    return service.get_templates()

@router.get(
    "/notifications",
    response_model=List[NotificationLogRead]
)
def get_notifications(
    userId: Optional[str] = Query(None, description="Filter logs by user ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = any(r.name in ["Admin", "Administrator"] for r in current_user.roles)
    
    # Enforce permissions: users can only see their own logs unless admin
    if userId is not None and userId != current_user.user_id and not is_admin:
        raise ForbiddenException("You can only view your own notification logs.")
    
    target_user_id = userId if is_admin else current_user.user_id
    
    service = NotificationService(db)
    return service.get_logs(user_id=target_user_id)
