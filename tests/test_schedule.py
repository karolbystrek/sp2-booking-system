import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from schedule_service.main import app, get_db
from schedule_service.models import Base

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

def test_add_schedule_block():
    start_time = datetime.now().isoformat()
    end_time = (datetime.now() + timedelta(hours=8)).isoformat()
    
    response = client.post("/specialists/spec-1/schedule/blocks", json={
        "start_time": start_time,
        "end_time": end_time,
        "block_type": "AVAILABLE"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "block_id" in data

def test_add_schedule_block_invalid_times():
    start_time = datetime.now().isoformat()
    end_time = (datetime.now() - timedelta(hours=1)).isoformat() # end before start
    
    response = client.post("/specialists/spec-1/schedule/blocks", json={
        "start_time": start_time,
        "end_time": end_time,
        "block_type": "AVAILABLE"
    })
    
    assert response.status_code == 400
    assert response.json()["detail"] == "end_time must be after start_time"

def test_get_schedule():
    start_time = datetime.now().isoformat()
    end_time = (datetime.now() + timedelta(hours=4)).isoformat()
    
    client.post("/specialists/spec-get/schedule/blocks", json={
        "start_time": start_time,
        "end_time": end_time,
        "block_type": "AVAILABLE"
    })
    
    response = client.get("/specialists/spec-get/schedule")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["block_type"] == "AVAILABLE"
