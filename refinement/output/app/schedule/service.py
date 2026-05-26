import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.exceptions import ConflictException, NotFoundException, ForbiddenException
from app.schedule.repository import ScheduleRepository
from app.schedule.schemas import ScheduleBlockCreate, ScheduleBlockUpdate
from app.schedule.models import SpecialistSchedule
from app.events import event_bus
from app.identity.models import User

logger = logging.getLogger(__name__)

class ScheduleService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ScheduleRepository(db)

    def _verify_is_specialist(self, specialist_id: str):
        user = self.db.query(User).filter(User.user_id == specialist_id).first()
        if not user:
            raise NotFoundException("Specialist not found")
        roles = [r.name for r in user.roles]
        if "Specialist" not in roles and "Admin" not in roles and "Administrator" not in roles:
            raise ForbiddenException("User is not registered as a Specialist")

    async def create_schedule_block(self, specialist_id: str, payload: ScheduleBlockCreate) -> SpecialistSchedule:
        logger.info(f"Creating schedule block for specialist {specialist_id}")
        self._verify_is_specialist(specialist_id)

        # Check for overlaps with blocks of the same type
        has_overlap = self.repo.check_overlap(
            specialist_id=specialist_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            block_type=payload.block_type.value
        )
        if has_overlap:
            raise ConflictException(f"This block overlaps with an existing {payload.block_type.value} block for the specialist.")

        block = self.repo.create_block(specialist_id, payload)
        
        # Publish event for Availability read model
        await event_bus.publish("SpecialistScheduleUpdated", {
            "specialist_id": specialist_id,
            "block_id": block.block_id,
            "action": "CREATE",
            "block_type": block.block_type,
            "start_time": block.start_time.isoformat(),
            "end_time": block.end_time.isoformat()
        })
        
        return block

    def get_specialist_schedule(
        self, 
        specialist_id: str, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> List[SpecialistSchedule]:
        self._verify_is_specialist(specialist_id)
        return self.repo.get_blocks_by_specialist(specialist_id, start_time, end_time)

    async def update_schedule_block(
        self, 
        specialist_id: str, 
        block_id: str, 
        payload: ScheduleBlockUpdate
    ) -> SpecialistSchedule:
        logger.info(f"Updating schedule block {block_id} for specialist {specialist_id}")
        self._verify_is_specialist(specialist_id)

        block = self.repo.get_by_id(block_id)
        if not block:
            raise NotFoundException("Schedule block not found")
        if block.specialist_id != specialist_id:
            raise ForbiddenException("You do not have permission to modify this schedule block")

        # Resolve times for overlap check
        new_start = payload.start_time if payload.start_time is not None else block.start_time
        new_end = payload.end_time if payload.end_time is not None else block.end_time
        new_type = payload.block_type.value if payload.block_type is not None else block.block_type

        has_overlap = self.repo.check_overlap(
            specialist_id=specialist_id,
            start_time=new_start,
            end_time=new_end,
            block_type=new_type,
            exclude_block_id=block_id
        )
        if has_overlap:
            raise ConflictException(f"The updated block would overlap with an existing {new_type} block.")

        updated_block = self.repo.update_block(block, payload)

        await event_bus.publish("SpecialistScheduleUpdated", {
            "specialist_id": specialist_id,
            "block_id": updated_block.block_id,
            "action": "UPDATE",
            "block_type": updated_block.block_type,
            "start_time": updated_block.start_time.isoformat(),
            "end_time": updated_block.end_time.isoformat()
        })

        return updated_block

    async def delete_schedule_block(self, specialist_id: str, block_id: str) -> None:
        logger.info(f"Deleting schedule block {block_id} for specialist {specialist_id}")
        self._verify_is_specialist(specialist_id)

        block = self.repo.get_by_id(block_id)
        if not block:
            raise NotFoundException("Schedule block not found")
        if block.specialist_id != specialist_id:
            raise ForbiddenException("You do not have permission to delete this schedule block")

        self.repo.delete_block(block)

        await event_bus.publish("SpecialistScheduleUpdated", {
            "specialist_id": specialist_id,
            "block_id": block_id,
            "action": "DELETE",
            "block_type": block.block_type,
            "start_time": block.start_time.isoformat(),
            "end_time": block.end_time.isoformat()
        })
