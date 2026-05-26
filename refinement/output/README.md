# Modular Booking Backend System

A production-ready, clean architecture modular monolithic backend application for an appointment booking system, built with Python, FastAPI, SQLite, and SQLAlchemy.

## Tech Stack
- **Framework**: FastAPI (Async)
- **Database**: SQLite + SQLAlchemy ORM
- **Migration Tool**: Alembic
- **Environment & Dependency Manager**: `uv`
- **Security**: JWT Authentication (Access + Refresh tokens) & RBAC

## Project Structure
- `app/` - Core application logic separated into bounded domains:
  - `identity/` - User registration, role authorization, and JWT logic.
  - `schedule/` - Managing specialist availability hours, breaks, and holidays.
  - `reservations/` - Patient booking lifecycle, active reservation limits, and double-booking conflict checks.
  - `availability/` - CQRS Read Model generating available booking slots on-the-fly.
  - `notifications/` - Simulated email/SMS alerts triggered via an internal Event Bus.
- `tests/` - Core domain and API endpoints unit tests.

## Setup Instructions

### 1. Prerequisites
- Python >= 3.10
- `uv` package manager installed

### 2. Running Locally
Initialize the virtual environment:
```bash
uv venv
```

Install dependencies:
```bash
uv pip install fastapi uvicorn sqlalchemy alembic pydantic pydantic-settings pyjwt passlib bcrypt python-multipart python-dotenv email-validator pytest pytest-asyncio httpx
```

Run the application:
```bash
uv run uvicorn app.main:app --reload
```

The API documentation will be available at `http://127.0.0.1:8000/docs`.

### 3. Testing & Authentication
The database is pre-seeded with default test accounts for each role:

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@example.com` | `adminpassword` |
| **Specialist** | `specialist@example.com` | `specialistpassword` |
| **Patient** | `patient@example.com` | `patientpassword` |

#### How to authorize requests in Swagger UI (`/docs`):
You can authorize requests directly using the standard Swagger **"Authorize"** button:
1. Click the **"Authorize"** button in the top right corner of the `/docs` page.
2. Under the **OAuth2PasswordBearer** section, enter the email of the desired role in the `username` field (e.g., `admin@example.com`).
3. Enter the corresponding password in the `password` field (e.g., `adminpassword`).
4. Click **"Authorize"** and then **"Close"**.

*(Note: The `/auth/login` endpoint accepts both JSON payloads and standard form-data urlencoded requests to support both API clients and Swagger UI's native authorization form.)*

### 4. Running Tests
Run all unit tests using pytest:
```bash
uv run pytest
```
