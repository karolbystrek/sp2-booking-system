from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid
import datetime

Base = declarative_base()

class NotificationLog(Base):
    __tablename__ = 'notification_logs'
    log_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient = Column(String, nullable=False) # e.g. patient_id or email
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    status = Column(String(50), default="SENT")
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)

engine = create_engine('sqlite:///notifications.db', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
