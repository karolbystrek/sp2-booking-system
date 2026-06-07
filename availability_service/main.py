from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from models import SessionLocal, AvailableSlot, init_db
from datetime import datetime, timedelta
import dateutil.parser

app = FastAPI(title="Appointment Availability Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/internal/events")
async def handle_event(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    event_type = data.get("event_type")
    payload = data.get("payload")
    
    if event_type == "SpecialistScheduleUpdated":
        # Simplified: We just create 30-min slots from start to end if type is AVAILABLE
        if payload.get("block_type") == "AVAILABLE":
            start_time = dateutil.parser.parse(payload["start_time"])
            end_time = dateutil.parser.parse(payload["end_time"])
            current = start_time
            while current < end_time:
                slot_end = current + timedelta(minutes=30)
                if slot_end <= end_time:
                    slot = AvailableSlot(
                        specialist_id=payload["specialist_id"],
                        start_time=current,
                        end_time=slot_end
                    )
                    db.add(slot)
                current = slot_end
            db.commit()

    elif event_type == "ReservationCreated":
        # Mark slot as booked
        slot = db.query(AvailableSlot).filter(
            AvailableSlot.specialist_id == payload["specialist_id"],
            AvailableSlot.start_time == dateutil.parser.parse(payload["appointment_time"])
        ).first()
        if slot:
            slot.is_booked = True
            slot.reservation_id = payload["reservation_id"]
            db.commit()

    elif event_type == "ReservationCancelled":
        # Free slot
        slot = db.query(AvailableSlot).filter(
            AvailableSlot.reservation_id == payload["reservation_id"]
        ).first()
        if slot:
            slot.is_booked = False
            slot.reservation_id = None
            db.commit()

    return {"status": "processed"}

@app.get("/available-appointments")
def get_available_appointments(specialist_id: str = None, date: str = None, db: Session = Depends(get_db)):
    query = db.query(AvailableSlot).filter(AvailableSlot.is_booked == False)
    
    if specialist_id:
        query = query.filter(AvailableSlot.specialist_id == specialist_id)
        
    if date:
        # Simple string matching for date if formatted as YYYY-MM-DD
        # In a real app we'd do Proper Date filtering
        pass # Simplified for prototype
        
    slots = query.all()
    return slots
