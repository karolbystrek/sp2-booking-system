# Appointment Booking System

REST API built with **Python + FastAPI + SQLite** based on the gold requirements and architecture.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

## Auth

All requests require an `X-User-Id` header with an integer user ID.

## Test Users (seeded on first start)

| ID | Name  | Role       |
|----|-------|------------|
| 1  | Alice | USER       |
| 2  | Bob   | USER       |
| 3  | Carol | SPECIALIST |
| 4  | Dave  | SPECIALIST |
| 5  | Eve   | ADMIN      |

## Endpoints

| Role       | Method | Path                  | Description            |
|------------|--------|-----------------------|------------------------|
| User       | GET    | /slots                | Browse available slots |
| User       | POST   | /bookings             | Book a slot            |
| User       | DELETE | /bookings/{id}        | Cancel a booking       |
| User       | GET    | /bookings/my          | My bookings            |
| Specialist | POST   | /slots                | Add a slot             |
| Specialist | DELETE | /slots/{id}           | Remove a free slot     |
| Specialist | PATCH  | /slots/{id}/block     | Block a slot           |
| Specialist | GET    | /slots/my             | My slots               |
| Admin      | GET    | /users                | All users              |
| Admin      | GET    | /bookings             | All bookings           |
| Admin      | GET    | /audit-log            | Full audit log         |
