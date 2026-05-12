from fastapi import FastAPI
from .database import engine, Base, SessionLocal
from .models import User, Specialist
from .api import user_endpoints, specialist_endpoints, admin_endpoints

# Create all tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Appointment Booking System")

app.include_router(user_endpoints.router)
app.include_router(specialist_endpoints.router)
app.include_router(admin_endpoints.router)

@app.on_event("startup")
def populate_test_data():
    db = SessionLocal()
    try:
        # Check if users already exist
        if not db.query(User).first():
            # Create Test Admin
            admin = User(name="Admin User", role="ADMIN")
            db.add(admin)
            
            # Create Test User
            user = User(name="Regular User", role="USER")
            db.add(user)
            
            # Create Test Specialist
            spec_user = User(name="Doctor Smith", role="SPECIALIST")
            db.add(spec_user)
            db.commit()
            
            # Add Specialist profile
            db.refresh(spec_user)
            specialist = Specialist(user_id=spec_user.id, specialization="Cardiology")
            db.add(specialist)
            db.commit()
    finally:
        db.close()
