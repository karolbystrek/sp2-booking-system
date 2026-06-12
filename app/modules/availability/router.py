import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.modules.availability import service
from app.modules.availability.schemas import (
    SlotSearchResponse, SlotCreateRequest, SlotUpdateRequest, SlotBlockRequest,
)

router = APIRouter()


@router.get("/availability/slots", response_model=SlotSearchResponse)
def search_slots(specialization: str | None = None,
                 dateFrom: str | None = None, dateTo: str | None = None,
                 timeFrom: str | None = None, timeTo: str | None = None,
                 page: int = 0, size: int = 20,
                 current_user: dict = Depends(get_current_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    result = service.search_available_slots(
        conn, specialization=specialization,
        date_from=dateFrom, date_to=dateTo,
        time_from=timeFrom, time_to=timeTo,
        page=page, size=size,
    )
    return result


@router.get("/availability/specialists/{specialist_id}/slots")
def get_specialist_slots(specialist_id: str,
                         date_from: str | None = None, date_to: str | None = None,
                         current_user: dict = Depends(get_current_user),
                         conn: sqlite3.Connection = Depends(get_db)):
    return service.get_specialist_slots(conn, specialist_id, date_from, date_to)


@router.get("/schedules")
def get_my_schedule(current_user: dict = Depends(require_roles(["SPECIALIST"])),
                    conn: sqlite3.Connection = Depends(get_db)):
    specialist_id = service.get_specialist_id_for_user(conn, current_user["id"])
    if not specialist_id:
        raise HTTPException(status_code=404, detail="Specialist profile not found")
    schedule = service.get_schedule(conn, specialist_id)
    if not schedule:
        return {"id": None, "specialistId": specialist_id, "slots": []}
    return schedule


@router.post("/schedules/slots", status_code=201)
def create_slot(request: SlotCreateRequest,
                current_user: dict = Depends(require_roles(["SPECIALIST"])),
                conn: sqlite3.Connection = Depends(get_db)):
    specialist_id = service.get_specialist_id_for_user(conn, current_user["id"])
    if not specialist_id:
        raise HTTPException(status_code=404, detail="Specialist profile not found")
    return service.create_slot(conn, specialist_id, request.startTime, request.endTime, request.slotType)


@router.put("/schedules/slots/{slot_id}")
def update_slot(slot_id: str, request: SlotUpdateRequest,
                current_user: dict = Depends(require_roles(["SPECIALIST"])),
                conn: sqlite3.Connection = Depends(get_db)):
    specialist_id = service.get_specialist_id_for_user(conn, current_user["id"])
    if not specialist_id:
        raise HTTPException(status_code=404, detail="Specialist profile not found")
    result = service.update_slot(conn, slot_id, specialist_id,
                                 start_time=request.startTime, end_time=request.endTime,
                                 new_status=request.status)
    if not result:
        raise HTTPException(status_code=404, detail="Slot not found")
    return result


@router.delete("/schedules/slots/{slot_id}", status_code=204)
def delete_slot(slot_id: str,
                current_user: dict = Depends(require_roles(["SPECIALIST"])),
                conn: sqlite3.Connection = Depends(get_db)):
    specialist_id = service.get_specialist_id_for_user(conn, current_user["id"])
    if not specialist_id:
        raise HTTPException(status_code=404, detail="Specialist profile not found")
    if not service.delete_slot(conn, slot_id, specialist_id):
        raise HTTPException(status_code=404, detail="Slot not found")


@router.post("/schedules/slots/{slot_id}/block", status_code=200)
def block_slot(slot_id: str, request: SlotBlockRequest,
               current_user: dict = Depends(require_roles(["SPECIALIST"])),
               conn: sqlite3.Connection = Depends(get_db)):
    specialist_id = service.get_specialist_id_for_user(conn, current_user["id"])
    if not specialist_id:
        raise HTTPException(status_code=404, detail="Specialist profile not found")
    if not service.block_slot(conn, slot_id, specialist_id, request.reason):
        raise HTTPException(status_code=404, detail="Slot not found")
    return {"message": "Slot blocked"}


@router.delete("/schedules/slots/{slot_id}/block", status_code=200)
def unblock_slot(slot_id: str,
                 current_user: dict = Depends(require_roles(["SPECIALIST"])),
                 conn: sqlite3.Connection = Depends(get_db)):
    specialist_id = service.get_specialist_id_for_user(conn, current_user["id"])
    if not specialist_id:
        raise HTTPException(status_code=404, detail="Specialist profile not found")
    if not service.unblock_slot(conn, slot_id, specialist_id):
        raise HTTPException(status_code=404, detail="Slot not found or not blocked")
    return {"message": "Slot unblocked"}
