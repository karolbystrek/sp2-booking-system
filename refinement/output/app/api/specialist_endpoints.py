from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db
from ..dependencies import get_current_user
from ..services import schedule_service

router = APIRouter(prefix="", tags=["Specialists"])

def require_specialist(user: models.User = Depends(get_current_user)):
    if user.role != "SPECIALIST":
        raise HTTPException(status_code=403, detail="Only specialists can perform this action")
    if not user.specialist:
        raise HTTPException(status_code=403, detail="Specialist profile not found")
    return user

@router.post("/slots", response_model=schemas.SlotResponse)
def create_slot(
    slot_in: schemas.SlotCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_specialist)
):
    return schedule_service.create_slot(
        db, 
        specialist_id=user.specialist.id, 
        start_time=slot_in.start_time, 
        end_time=slot_in.end_time
    )

@router.delete("/slots/{slot_id}")
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_specialist)
):
    slot = schedule_service.get_slot_by_id(db, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.specialist_id != user.specialist.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this slot")
    
    if schedule_service.delete_slot(db, slot_id):
        return {"detail": "Slot deleted successfully"}
    else:
        raise HTTPException(status_code=400, detail="Cannot delete slot, it is already booked or blocked")

@router.patch("/slots/{slot_id}/block", response_model=schemas.SlotResponse)
def block_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_specialist)
):
    slot = schedule_service.get_slot_by_id(db, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.specialist_id != user.specialist.id:
        raise HTTPException(status_code=403, detail="Not authorized to block this slot")
    
    return schedule_service.update_slot_status(db, slot_id, "BLOCKED")

@router.get("/slots/my", response_model=List[schemas.SlotResponse])
def get_my_slots(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_specialist)
):
    return schedule_service.get_slots(db, specialist_id=user.specialist.id)
