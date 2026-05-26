from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.database import get_db
from app.identity.auth import get_current_user, RequireRole
from app.identity.models import User
from app.exceptions import ForbiddenException
from app.schedule.schemas import ScheduleBlockCreate, ScheduleBlockUpdate, ScheduleBlockRead
from app.schedule.service import ScheduleService

router = APIRouter()

def _check_specialist_permission(specialist_id: str, current_user: User):
    is_admin = any(r.name in ["Admin", "Administrator"] for r in current_user.roles)
    if not is_admin and current_user.user_id != specialist_id:
        raise ForbiddenException("You can only manage your own schedule blocks")

@router.post(
    "/specialists/{specialistId}/schedule/blocks",
    response_model=ScheduleBlockRead,
    status_code=status.HTTP_201_CREATED
)
async def create_block(
    specialistId: str,
    payload: ScheduleBlockCreate,
    current_user: User = Depends(RequireRole(["Specialist"])),
    db: Session = Depends(get_db)
):
    _check_specialist_permission(specialistId, current_user)
    service = ScheduleService(db)
    return await service.create_schedule_block(specialistId, payload)

@router.get(
    "/specialists/{specialistId}/schedule",
    response_model=List[ScheduleBlockRead]
)
async def get_schedule(
    specialistId: str,
    startDate: Optional[datetime] = Query(None, description="Filter from start date"),
    endDate: Optional[datetime] = Query(None, description="Filter to end date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ScheduleService(db)
    return service.get_specialist_schedule(specialistId, startDate, endDate)

@router.put(
    "/specialists/{specialistId}/schedule/blocks/{blockId}",
    response_model=ScheduleBlockRead
)
async def update_block(
    specialistId: str,
    blockId: str,
    payload: ScheduleBlockUpdate,
    current_user: User = Depends(RequireRole(["Specialist"])),
    db: Session = Depends(get_db)
):
    _check_specialist_permission(specialistId, current_user)
    service = ScheduleService(db)
    return await service.update_schedule_block(specialistId, blockId, payload)

@router.delete(
    "/specialists/{specialistId}/schedule/blocks/{blockId}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_block(
    specialistId: str,
    blockId: str,
    current_user: User = Depends(RequireRole(["Specialist"])),
    db: Session = Depends(get_db)
):
    _check_specialist_permission(specialistId, current_user)
    service = ScheduleService(db)
    await service.delete_schedule_block(specialistId, blockId)
    return None
