import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from identity_service.main import app, get_db
from identity_service.models import Base, Role

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

# Populate roles for tests
db = TestingSessionLocal()
if not db.query(Role).filter_by(name="Patient").first():
    db.add(Role(name="Patient"))
if not db.query(Role).filter_by(name="Specialist").first():
    db.add(Role(name="Specialist"))
db.commit()
db.close()

client = TestClient(app)

def test_register_patient():
    response = client.post("/auth/register", json={
        "email": "patient@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
        "role": "Patient"
    })
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert data["message"] == "User registered successfully"

def test_register_duplicate_patient():
    client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
        "role": "Patient"
    })
    response = client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
        "role": "Patient"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_success():
    client.post("/auth/register", json={
        "email": "login@example.com",
        "password": "password123",
        "first_name": "Jane",
        "last_name": "Doe",
        "role": "Patient"
    })
    response = client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure():
    response = client.post("/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "password123"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_get_user():
    reg = client.post("/auth/register", json={
        "email": "get@example.com",
        "password": "password123",
        "first_name": "Get",
        "last_name": "User",
        "role": "Patient"
    })
    user_id = reg.json()["user_id"]
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "get@example.com"
    assert data["first_name"] == "Get"
    assert "Patient" in data["roles"]
