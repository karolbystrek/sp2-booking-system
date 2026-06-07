from sqlalchemy.orm import Session
from models import SessionLocal, User, Role, SpecialistDetails, init_db
import hashlib

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def populate_test_users():
    init_db()
    db = SessionLocal()
    
    # Check if roles exist
    if db.query(Role).first():
        print("Database already initialized.")
        db.close()
        return

    # Add roles
    role_patient = Role(name="Patient")
    role_specialist = Role(name="Specialist")
    role_admin = Role(name="Admin")
    db.add_all([role_patient, role_specialist, role_admin])
    db.commit()

    # Add Test Patient
    patient = User(
        email="patient@example.com",
        password_hash=get_password_hash("password123"),
        first_name="John",
        last_name="Doe",
        roles=[role_patient]
    )
    db.add(patient)

    # Add Test Specialist
    specialist = User(
        email="specialist@example.com",
        password_hash=get_password_hash("password123"),
        first_name="Jane",
        last_name="Smith",
        roles=[role_specialist]
    )
    db.add(specialist)
    db.commit()

    # Add Specialist Details
    details = SpecialistDetails(
        specialist_id=specialist.user_id,
        specialization="Cardiologist",
        default_appointment_duration_minutes=30
    )
    db.add(details)
    
    # Add Test Admin
    admin = User(
        email="admin@example.com",
        password_hash=get_password_hash("admin123"),
        first_name="Admin",
        last_name="User",
        roles=[role_admin]
    )
    db.add(admin)

    db.commit()
    print("Test users populated successfully.")
    print(f"Patient ID: {patient.user_id}")
    print(f"Specialist ID: {specialist.user_id}")
    db.close()

if __name__ == "__main__":
    populate_test_users()
