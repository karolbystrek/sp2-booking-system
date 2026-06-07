from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid

Base = declarative_base()

class SpecialistSchedule(Base):
    __tablename__ = 'specialist_schedule'
    block_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    specialist_id = Column(String, index=True, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    block_type = Column(String(50), nullable=False) # 'AVAILABLE', 'BREAK', 'HOLIDAY'

engine = create_engine('sqlite:///schedule.db', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
