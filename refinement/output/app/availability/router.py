from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from app.database import get_db
from app.availability.schemas import SpecialistAvailabilityResponse
from app.availability.service import AvailabilityService

router = APIRouter()

@router.get(
    "/available-appointments",
    response_model=List[SpecialistAvailabilityResponse]
)
def get_available_appointments(
    date: date = Query(..., description="Target date to query available slots (YYYY-MM-DD)"),
    specialization: Optional[str] = Query(None, description="Filter by specialist specialization"),
    specialistId: Optional[str] = Query(None, description="Filter by specialist ID"),
    minDuration: int = Query(30, description="Minimum slot duration in minutes"),
    db: Session = Depends(get_db)
):
    service = AvailabilityService(db)
    return service.get_available_appointments(
        query_date=date,
        specialization=specialization,
        specialist_id=specialistId,
        min_duration=minDuration
    )
