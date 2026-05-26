from typing import List, Optional
from datetime import datetime
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.schedule.models import SpecialistSchedule
from app.schedule.schemas import ScheduleBlockCreate, ScheduleBlockUpdate

class ScheduleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, block_id: str) -> Optional[SpecialistSchedule]:
        return self.db.query(SpecialistSchedule).filter(SpecialistSchedule.block_id == block_id).first()

    def get_blocks_by_specialist(
        self, 
        specialist_id: str, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> List[SpecialistSchedule]:
        query = self.db.query(SpecialistSchedule).filter(SpecialistSchedule.specialist_id == specialist_id)
        if start_time:
            query = query.filter(SpecialistSchedule.end_time >= start_time)
        if end_time:
            query = query.filter(SpecialistSchedule.start_time <= end_time)
        return query.order_by(SpecialistSchedule.start_time.asc()).all()

    def create_block(self, specialist_id: str, payload: ScheduleBlockCreate) -> SpecialistSchedule:
        block = SpecialistSchedule(
            specialist_id=specialist_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            block_type=payload.block_type.value
        )
        self.db.add(block)
        self.db.commit()
        self.db.refresh(block)
        return block

    def update_block(self, block: SpecialistSchedule, payload: ScheduleBlockUpdate) -> SpecialistSchedule:
        if payload.start_time is not None:
            block.start_time = payload.start_time
        if payload.end_time is not None:
            block.end_time = payload.end_time
        if payload.block_type is not None:
            block.block_type = payload.block_type.value

        self.db.commit()
        self.db.refresh(block)
        return block

    def delete_block(self, block: SpecialistSchedule) -> None:
        self.db.delete(block)
        self.db.commit()

    def check_overlap(
        self, 
        specialist_id: str, 
        start_time: datetime, 
        end_time: datetime, 
        block_type: str,
        exclude_block_id: Optional[str] = None
    ) -> bool:
        # Check overlapping blocks of the same type or general conflicts
        # Overlap happens if: start1 < end2 AND end1 > start2
        query = self.db.query(SpecialistSchedule).filter(
            and_(
                SpecialistSchedule.specialist_id == specialist_id,
                SpecialistSchedule.block_type == block_type,
                SpecialistSchedule.start_time < end_time,
                SpecialistSchedule.end_time > start_time
            )
        )
        if exclude_block_id:
            query = query.filter(SpecialistSchedule.block_id != exclude_block_id)
            
        return query.first() is not None
