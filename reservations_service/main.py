from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .models import SessionLocal, Reservation, init_db
import httpx
from datetime import datetime

app = FastAPI(title="Reservations Service")

EVENT_BROKER_URL = "http://localhost:8006/publish"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    init_db()

class ReservationRequest(BaseModel):
    patient_id: str
    specialist_id: str
    appointment_time: datetime
    duration_minutes: int = 30

async def publish_event(event_type: str, payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(EVENT_BROKER_URL, params={"event_type": event_type}, json=payload)
        except Exception as e:
            print(f"Failed to publish event: {e}")

@app.post("/reservations")
def create_reservation(req: ReservationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Simple limit validation (could be more complex like checking active reservations)
    active_count = db.query(Reservation).filter(
        Reservation.patient_id == req.patient_id, 
        Reservation.status.in_(['PENDING', 'CONFIRMED'])
    ).count()
    if active_count >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 active reservations allowed")

    reservation = Reservation(
        patient_id=req.patient_id,
        specialist_id=req.specialist_id,
        appointment_time=req.appointment_time,
        duration_minutes=req.duration_minutes,
        status="CONFIRMED"
    )
    db.add(reservation)
    
    try:
        db.commit()
        db.refresh(reservation)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Time slot already booked for this specialist")
    
    payload = {
        "reservation_id": reservation.reservation_id,
        "patient_id": reservation.patient_id,
        "specialist_id": reservation.specialist_id,
        "appointment_time": reservation.appointment_time.isoformat(),
        "status": reservation.status
    }
    background_tasks.add_task(publish_event, "ReservationCreated", payload)
    
    return {"reservation_id": reservation.reservation_id, "status": reservation.status}

@app.put("/reservations/{reservation_id}/cancel")
def cancel_reservation(reservation_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    reservation = db.query(Reservation).filter(Reservation.reservation_id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
        
    reservation.status = "CANCELLED"
    db.commit()
    
    payload = {"reservation_id": reservation.reservation_id, "status": "CANCELLED"}
    background_tasks.add_task(publish_event, "ReservationCancelled", payload)
    
    return {"message": "Reservation cancelled"}
