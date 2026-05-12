from datetime import date

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.dependencies import get_db
from app.dependencies import require_role
from app.models import Slot
from app.models import SlotStatus
from app.models import Specialist
from app.models import User
from app.models import UserRole
from app.schemas import SlotCreate
from app.schemas import SlotResponse
from app.services.schedule_service import ScheduleService
from app.services.user_access_service import UserAccessService

router = APIRouter(prefix="/slots", tags=["Slots"])


@router.get("", response_model=list[SlotResponse])
def get_available_slots(
    specialist_id: int,
    selected_date: date,
    db: Session = Depends(get_db),
):
    return ScheduleService.get_available_slots(
        db,
        specialist_id,
        selected_date,
    )


@router.post("", response_model=SlotResponse)
def create_slot(
    payload: SlotCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.SPECIALIST)),
):
    specialist = db.query(Specialist).filter(Specialist.user_id == user.id).first()

    slot = Slot(
        specialist_id=specialist.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=SlotStatus.AVAILABLE,
    )

    db.add(slot)
    db.commit()
    db.refresh(slot)

    return slot


@router.delete("/{slot_id}")
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.SPECIALIST)),
):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    specialist = (
        db.query(Specialist)
        .filter(Specialist.id == slot.specialist_id)
        .first()
    )

    UserAccessService.validate_slot_access(user, slot, specialist)

    if slot.status == SlotStatus.BOOKED:
        raise HTTPException(status_code=400, detail="Booked slot cannot be deleted")

    db.delete(slot)
    db.commit()

    return {"message": "Slot deleted"}


@router.patch("/{slot_id}/block", response_model=SlotResponse)
def block_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.SPECIALIST)),
):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    specialist = (
        db.query(Specialist)
        .filter(Specialist.id == slot.specialist_id)
        .first()
    )

    UserAccessService.validate_slot_access(user, slot, specialist)

    slot.status = SlotStatus.BLOCKED

    db.commit()
    db.refresh(slot)

    return slot


@router.get("/my", response_model=list[SlotResponse])
def get_my_slots(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    specialist = db.query(Specialist).filter(Specialist.user_id == user.id).first()

    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")

    return db.query(Slot).filter(Slot.specialist_id == specialist.id).all()