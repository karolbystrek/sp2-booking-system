from fastapi import FastAPI, BackgroundTasks
import httpx
import logging

app = FastAPI(title="Event Broker")
logging.basicConfig(level=logging.INFO)

SUBSCRIBERS = {
    "SpecialistScheduleUpdated": [
        "http://localhost:8004/internal/events" # Availability Service
    ],
    "ReservationCreated": [
        "http://localhost:8004/internal/events", # Availability Service
        "http://localhost:8005/internal/events"  # Notifications Service
    ],
    "ReservationCancelled": [
        "http://localhost:8004/internal/events",
        "http://localhost:8005/internal/events"
    ],
    "ReservationModified": [
        "http://localhost:8004/internal/events",
        "http://localhost:8005/internal/events"
    ]
}

async def forward_event(url: str, event_type: str, payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"event_type": event_type, "payload": payload})
            response.raise_for_status()
            logging.info(f"Successfully forwarded {event_type} to {url}")
        except Exception as e:
            logging.error(f"Failed to forward {event_type} to {url}: {e}")

@app.post("/publish")
async def publish_event(event_type: str, payload: dict, background_tasks: BackgroundTasks):
    logging.info(f"Received event: {event_type}")
    if event_type in SUBSCRIBERS:
        for url in SUBSCRIBERS[event_type]:
            background_tasks.add_task(forward_event, url, event_type, payload)
    return {"status": "Event accepted"}
