import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from reservations_service.main import app, get_db
from reservations_service.models import Base, Reservation

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

def test_create_reservation():
    appointment_time = (datetime.now() + timedelta(days=1)).isoformat()
    response = client.post("/reservations", json={
        "patient_id": "patient-1",
        "specialist_id": "specialist-1",
        "appointment_time": appointment_time,
        "duration_minutes": 30
    })
    assert response.status_code == 200
    data = response.json()
    assert "reservation_id" in data
    assert data["status"] == "CONFIRMED"

def test_create_duplicate_reservation_same_time():
    appointment_time = (datetime.now() + timedelta(days=2)).isoformat()
    # First reservation
    client.post("/reservations", json={
        "patient_id": "patient-1",
        "specialist_id": "specialist-2",
        "appointment_time": appointment_time,
        "duration_minutes": 30
    })
    # Second reservation for same specialist and time
    response = client.post("/reservations", json={
        "patient_id": "patient-2",
        "specialist_id": "specialist-2",
        "appointment_time": appointment_time,
        "duration_minutes": 30
    })
    assert response.status_code == 409
    assert response.json()["detail"] == "Time slot already booked for this specialist"

def test_create_reservation_limit():
    # User can't have more than 3 active reservations
    appointment_time = datetime.now() + timedelta(days=3)
    for i in range(3):
        res = client.post("/reservations", json={
            "patient_id": "patient-limit",
            "specialist_id": f"specialist-limit-{i}",
            "appointment_time": (appointment_time + timedelta(hours=i)).isoformat(),
            "duration_minutes": 30
        })
        assert res.status_code == 200

    # 4th reservation should fail
    res = client.post("/reservations", json={
        "patient_id": "patient-limit",
        "specialist_id": "specialist-limit-4",
        "appointment_time": (appointment_time + timedelta(hours=4)).isoformat(),
        "duration_minutes": 30
    })
    assert res.status_code == 400
    assert res.json()["detail"] == "Maximum 3 active reservations allowed"

def test_cancel_reservation():
    appointment_time = (datetime.now() + timedelta(days=4)).isoformat()
    res = client.post("/reservations", json={
        "patient_id": "patient-cancel",
        "specialist_id": "specialist-cancel",
        "appointment_time": appointment_time,
        "duration_minutes": 30
    })
    reservation_id = res.json()["reservation_id"]
    
    cancel_res = client.put(f"/reservations/{reservation_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["message"] == "Reservation cancelled"
