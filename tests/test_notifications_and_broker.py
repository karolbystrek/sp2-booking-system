import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
from datetime import datetime
import asyncio

from notifications_service.main import app, get_db
from notifications_service.models import Base, NotificationLog

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

def test_handle_reservation_created_notification():
    response = client.post("/internal/events", json={
        "event_type": "ReservationCreated",
        "payload": {
            "reservation_id": "res-123",
            "patient_id": "pat-123",
            "specialist_id": "spec-123",
            "appointment_time": datetime.now().isoformat(),
            "status": "CONFIRMED"
        }
    })
    
    assert response.status_code == 200
    
    # Check if notification was logged
    notif_res = client.get("/notifications")
    assert notif_res.status_code == 200
    notifications = notif_res.json()
    assert len(notifications) == 1
    assert notifications[0]["subject"] == "Reservation Confirmed"
    assert notifications[0]["recipient"] == "pat-123"

def test_handle_reservation_cancelled_notification():
    response = client.post("/internal/events", json={
        "event_type": "ReservationCancelled",
        "payload": {
            "reservation_id": "res-123",
            "patient_id": "pat-123",
            "status": "CANCELLED"
        }
    })
    
    assert response.status_code == 200
    
    notif_res = client.get("/notifications")
    assert notif_res.status_code == 200
    notifications = notif_res.json()
    assert len(notifications) == 2
    assert notifications[1]["subject"] == "Reservation Cancelled"
