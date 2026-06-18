from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .models import SessionLocal, SpecialistSchedule, init_db
import httpx
from datetime import datetime

app = FastAPI(title="Schedule Management Service")

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

class BlockRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    block_type: str

async def publish_event(event_type: str, payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(EVENT_BROKER_URL, params={"event_type": event_type}, json=payload)
        except Exception as e:
            print(f"Failed to publish event: {e}")

@app.post("/specialists/{specialist_id}/schedule/blocks")
def add_block(specialist_id: str, req: BlockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if req.end_time <= req.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
        
    block = SpecialistSchedule(
        specialist_id=specialist_id,
        start_time=req.start_time,
        end_time=req.end_time,
        block_type=req.block_type
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    
    # Emit event
    payload = {
        "specialist_id": specialist_id,
        "block_id": block.block_id,
        "start_time": block.start_time.isoformat(),
        "end_time": block.end_time.isoformat(),
        "block_type": block.block_type
    }
    background_tasks.add_task(publish_event, "SpecialistScheduleUpdated", payload)
    
    return {"block_id": block.block_id}

@app.get("/specialists/{specialist_id}/schedule")
def get_schedule(specialist_id: str, db: Session = Depends(get_db)):
    blocks = db.query(SpecialistSchedule).filter(SpecialistSchedule.specialist_id == specialist_id).all()
    return blocks
