from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import User, UserRole
from app.schemas import SlotCreate, SlotOut
from app.services import audit_service, schedule_service

router = APIRouter(tags=["specialist"])


@router.get("/slots/my", response_model=list[SlotOut])
def my_slots(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SPECIALIST)),
):
    specialist = schedule_service.get_specialist_by_user(db, current_user.id)
    return schedule_service.get_specialist_slots(db, specialist.id)


@router.post("/slots", response_model=SlotOut, status_code=201)
def add_slot(
    payload: SlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SPECIALIST)),
):
    specialist = schedule_service.get_specialist_by_user(db, current_user.id)
    slot = schedule_service.add_slot(db, specialist.id, payload.start_time, payload.end_time)
    audit_service.log_event(db, "SLOT_ADDED", user_id=current_user.id, slot_id=slot.id)
    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SPECIALIST)),
):
    specialist = schedule_service.get_specialist_by_user(db, current_user.id)
    slot = schedule_service.get_slot(db, slot_id)

    if slot.specialist_id != specialist.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not your slot")

    schedule_service.delete_slot(db, slot)
    audit_service.log_event(db, "SLOT_DELETED", user_id=current_user.id, slot_id=slot_id)
    db.commit()


@router.patch("/slots/{slot_id}/block", response_model=SlotOut)
def block_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SPECIALIST)),
):
    specialist = schedule_service.get_specialist_by_user(db, current_user.id)
    slot = schedule_service.get_slot(db, slot_id)

    if slot.specialist_id != specialist.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not your slot")

    slot = schedule_service.block_slot(db, slot)
    audit_service.log_event(db, "SLOT_BLOCKED", user_id=current_user.id, slot_id=slot_id)
    db.commit()
    db.refresh(slot)
    return slot
