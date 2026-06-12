import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.notification import service
from app.modules.notification.schemas import NotificationPreferencesRequest

router = APIRouter()


@router.get("/notifications")
def list_notifications(read: bool | None = None, page: int = 0, size: int = 20,
                       current_user: dict = Depends(get_current_user),
                       conn: sqlite3.Connection = Depends(get_db)):
    return service.get_user_notifications(conn, current_user["id"], read=read, page=page, size=size)


@router.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: str,
              current_user: dict = Depends(get_current_user),
              conn: sqlite3.Connection = Depends(get_db)):
    if not service.mark_as_read(conn, notification_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


@router.put("/notifications/preferences")
def update_preferences(request: NotificationPreferencesRequest,
                       current_user: dict = Depends(get_current_user),
                       conn: sqlite3.Connection = Depends(get_db)):
    return service.update_preferences(conn, current_user["id"],
                                      request.emailEnabled, request.pushEnabled)
