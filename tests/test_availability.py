import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from availability_service.main import app, get_db
from availability_service.models import Base, AvailableSlot

from sqlalchemy.pool import StaticPool
# Setup in-memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_handle_specialist_schedule_event():
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2) # 4 slots of 30 min
    
    response = client.post("/internal/events", json={
        "event_type": "SpecialistScheduleUpdated",
        "payload": {
            "specialist_id": "spec-availability-1",
            "block_id": "block-1",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "block_type": "AVAILABLE"
        }
    })
    
    assert response.status_code == 200
    
    # Check if slots are created
    slots_res = client.get("/available-appointments?specialist_id=spec-availability-1")
    assert slots_res.status_code == 200
    slots = slots_res.json()
    assert len(slots) == 4

def test_handle_reservation_created_event():
    # Setup a slot
    start_time = datetime.now().replace(microsecond=0)
    end_time = start_time + timedelta(hours=1)
    
    client.post("/internal/events", json={
        "event_type": "SpecialistScheduleUpdated",
        "payload": {
            "specialist_id": "spec-availability-2",
            "block_id": "block-2",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "block_type": "AVAILABLE"
        }
    })
    
    # Before reservation, 2 slots
    slots_res = client.get("/available-appointments?specialist_id=spec-availability-2")
    assert len(slots_res.json()) == 2
    
    # Send reservation created event
    response = client.post("/internal/events", json={
        "event_type": "ReservationCreated",
        "payload": {
            "reservation_id": "res-1",
            "specialist_id": "spec-availability-2",
            "patient_id": "pat-1",
            "appointment_time": start_time.isoformat(),
            "status": "CONFIRMED"
        }
    })
    
    assert response.status_code == 200
    
    # After reservation, 1 slot left
    slots_res = client.get("/available-appointments?specialist_id=spec-availability-2")
    assert len(slots_res.json()) == 1

def test_handle_reservation_cancelled_event():
    # Cancel the previous reservation
    response = client.post("/internal/events", json={
        "event_type": "ReservationCancelled",
        "payload": {
            "reservation_id": "res-1",
            "status": "CANCELLED"
        }
    })
    
    assert response.status_code == 200
    
    # After cancellation, 2 slots again
    slots_res = client.get("/available-appointments?specialist_id=spec-availability-2")
    assert len(slots_res.json()) == 2
