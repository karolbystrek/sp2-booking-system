from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from models import SessionLocal, NotificationLog, init_db

app = FastAPI(title="Notifications Service")

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
    
    if event_type == "ReservationCreated":
        log = NotificationLog(
            recipient=payload["patient_id"],
            subject="Reservation Confirmed",
            body=f"Your reservation for {payload['appointment_time']} with {payload['specialist_id']} is confirmed."
        )
        db.add(log)
        db.commit()
    elif event_type == "ReservationCancelled":
        log = NotificationLog(
            recipient=payload.get("patient_id", "Unknown"),
            subject="Reservation Cancelled",
            body=f"Your reservation {payload['reservation_id']} was cancelled."
        )
        db.add(log)
        db.commit()

    return {"status": "processed"}

@app.get("/notifications")
def get_notifications(db: Session = Depends(get_db)):
    return db.query(NotificationLog).all()
