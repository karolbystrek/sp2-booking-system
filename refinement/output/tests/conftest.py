import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set testing environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_booking.db"
os.environ["JWT_SECRET_KEY"] = "testsecretkeypleasechangemeinproduction1234567890123"
os.environ["JWT_REFRESH_SECRET_KEY"] = "testsecretrefreshkeypleasechangemeinproduction1234567890123"

from app.database import Base, get_db
from app.main import app

# Create test database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_booking.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after session
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_booking.db"):
        try:
            os.remove("test_booking.db")
        except Exception:
            pass

@pytest.fixture(autouse=True)
def clean_db(db):
    # Clean database tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()

# Override FastAPI get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def db():
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()

@pytest.fixture
def client():
    # Returns test client for requests
    with TestClient(app) as c:
        yield c
