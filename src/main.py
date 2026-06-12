from fastapi import FastAPI

from src.audit.api.routes import router as audit_router
from src.booking.api.routes import router as booking_router
from src.conflict_management.api.routes import router as conflict_router
from src.identity_access.api.routes import router as identity_router
from src.policy_configuration.api.routes import router as policy_router
from src.scheduling.api.routes import router as scheduling_router
from src.shared.database import init_database

app = FastAPI(title="Booking System", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    init_database()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(identity_router)
app.include_router(scheduling_router)
app.include_router(booking_router)
app.include_router(policy_router)
app.include_router(conflict_router)
app.include_router(audit_router)
