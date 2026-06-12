from fastapi import FastAPI

from app.database import init_db
from app.modules.identity.router import router as identity_router
from app.modules.availability.router import router as availability_router
from app.modules.booking.router import router as booking_router
from app.modules.notification.router import router as notification_router
from app.modules.administration.router import router as administration_router
from app.modules.notification.service import register_event_handlers as register_notification_handlers
from app.modules.administration.service import register_event_handlers as register_admin_handlers

app = FastAPI(
    title="Booking System API",
    description="Specialist appointment booking system - Modular Monolith",
    version="1.0.0",
)

app.include_router(identity_router, prefix="/api/v1", tags=["Identity & Access"])
app.include_router(availability_router, prefix="/api/v1", tags=["Availability"])
app.include_router(booking_router, prefix="/api/v1", tags=["Booking"])
app.include_router(notification_router, prefix="/api/v1", tags=["Notification"])
app.include_router(administration_router, prefix="/api/v1", tags=["Administration"])


@app.on_event("startup")
def startup():
    init_db()
    register_notification_handlers()
    register_admin_handlers()

    from app.seed import seed_test_data
    seed_test_data()


@app.get("/health")
def health_check():
    return {"status": "healthy"}
