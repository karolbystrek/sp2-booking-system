from sqlalchemy import create_engine, Column, String, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid

Base = declarative_base()

class Reservation(Base):
    __tablename__ = 'reservations'
    reservation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, index=True, nullable=False)
    specialist_id = Column(String, index=True, nullable=False)
    appointment_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default='PENDING') # 'PENDING', 'CONFIRMED', 'CANCELLED'

    __table_args__ = (
        UniqueConstraint('specialist_id', 'appointment_time', name='uix_specialist_time'),
    )

engine = create_engine('sqlite:///reservations.db', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
