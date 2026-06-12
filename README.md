# Booking System API

Specialist appointment booking system built as a Modular Monolith with FastAPI and SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The server starts at `http://127.0.0.1:8000`. Database is created and seeded automatically on first start.

API documentation: `http://127.0.0.1:8000/docs`

## Test Users

| Email | Password | Role |
|-------|----------|------|
| admin@booking.com | admin123 | ADMINISTRATOR |
| jan.kowalski@email.com | user123 | USER |
| anna.nowak@email.com | user123 | USER |
| dr.smith@clinic.com | spec123 | SPECIALIST (Cardiology) |
| dr.jones@clinic.com | spec123 | SPECIALIST (Neurology) |

## Architecture

Modular Monolith with 5 bounded contexts:

- **Booking** (Core) — reservation lifecycle, conflict detection, cancellation policies
- **Availability** — specialist schedules, time slots, search/filter
- **Identity & Access** — users, roles, JWT authentication
- **Notification** — event-driven notifications (email/push)
- **Administration** — system config, conflict exceptions, audit logs, reports

Communication between modules uses an in-process Event Bus with the Outbox pattern.

## API Prefix

All endpoints are under `/api/v1/`. Authentication uses Bearer JWT tokens obtained via `/api/v1/auth/login`.
