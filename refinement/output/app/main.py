import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal
from app.exceptions import register_exception_handlers
from app.events import event_bus
from app.config import settings

# Import routers
from app.identity.router import router as identity_router
from app.schedule.router import router as schedule_router
from app.reservations.router import router as reservations_router
from app.availability.router import router as availability_router
from app.notifications.router import router as notifications_router

# Import services for event registrations and seeding
from app.notifications.service import setup_notification_listeners, ensure_default_templates
from app.identity.models import Role, User
from app.identity.auth import hash_password

# Setup logging
logging.basicConfig(
    level=logging.INFO if settings.LOG_LEVEL == "INFO" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Modular Booking System Backend",
    description="Production-ready FastAPI backend strictly matching architecture output.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(identity_router, tags=["Identity & Access"])
app.include_router(schedule_router, tags=["Schedule Management"])
app.include_router(reservations_router, tags=["Reservations"])
app.include_router(availability_router, tags=["Appointment Availability"])
app.include_router(notifications_router, tags=["Notifications"])

# Register global exception handlers
register_exception_handlers(app)

# Initialize Event-Driven Architecture (EDA) subscribers
setup_notification_listeners()

def seed_database(db):
    # 1. Seed Roles
    roles = ["Patient", "Specialist", "Admin"]
    role_objs = {}
    for r_name in roles:
        role = db.query(Role).filter(Role.name == r_name).first()
        if not role:
            role = Role(name=r_name)
            db.add(role)
            db.commit()
            db.refresh(role)
        role_objs[r_name] = role

    # 2. Seed Default Notification Templates
    ensure_default_templates(db)

    # 3. Seed Default Admin, Specialist and Patient for testing
    admin_email = "admin@example.com"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        admin = User(
            email=admin_email,
            password_hash=hash_password("adminpassword"),
            first_name="Admin",
            last_name="User"
        )
        admin.roles.append(role_objs["Admin"])
        db.add(admin)

    spec_email = "specialist@example.com"
    specialist = db.query(User).filter(User.email == spec_email).first()
    if not specialist:
        from app.identity.models import SpecialistDetails
        specialist = User(
            email=spec_email,
            password_hash=hash_password("specialistpassword"),
            first_name="Anna",
            last_name="Nowak"
        )
        specialist.roles.append(role_objs["Specialist"])
        db.add(specialist)
        db.commit()
        db.refresh(specialist)

        spec_details = SpecialistDetails(
            specialist_id=specialist.user_id,
            specialization="Kardiolog",
            default_appointment_duration_minutes=30,
            bio="Experienced cardiologist.",
            office_address="Kardiolog Office 101"
        )
        db.add(spec_details)

    pat_email = "patient@example.com"
    patient = db.query(User).filter(User.email == pat_email).first()
    if not patient:
        patient = User(
            email=pat_email,
            password_hash=hash_password("patientpassword"),
            first_name="Jan",
            last_name="Kowalski"
        )
        patient.roles.append(role_objs["Patient"])
        db.add(patient)

    db.commit()
    logger.info("Database seed completed successfully.")

@app.on_event("startup")
def on_startup():
    logger.info("Starting up application...")
    
    # In SQLite development, this ensures tables are created even without manual migrations
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        seed_database(db)
    except Exception as e:
        logger.error(f"Error seeding database: {e}", exc_info=True)
    finally:
        db.close()
