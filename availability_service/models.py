from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid

Base = declarative_base()

class AvailableSlot(Base):
    __tablename__ = 'available_slots'
    slot_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    specialist_id = Column(String, index=True, nullable=False)
    start_time = Column(DateTime(timezone=True), index=True, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    is_booked = Column(Boolean, default=False)
    reservation_id = Column(String, nullable=True) # To track which reservation took it

engine = create_engine('sqlite:///availability.db', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
