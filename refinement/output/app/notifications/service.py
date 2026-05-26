import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.exceptions import NotFoundException, ConflictException
from app.notifications.models import NotificationTemplate, NotificationLog
from app.notifications.schemas import NotificationTemplateCreate
from app.identity.models import User
from app.events import event_bus
from app.database import SessionLocal

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_template(self, payload: NotificationTemplateCreate) -> NotificationTemplate:
        existing = self.db.query(NotificationTemplate).filter(NotificationTemplate.name == payload.name).first()
        if existing:
            raise ConflictException(f"Template with name {payload.name} already exists.")
            
        template = NotificationTemplate(
            name=payload.name,
            subject_template=payload.subject_template,
            body_template=payload.body_template,
            channel=payload.channel
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_templates(self) -> List[NotificationTemplate]:
        return self.db.query(NotificationTemplate).all()

    def get_logs(self, user_id: Optional[str] = None) -> List[NotificationLog]:
        query = self.db.query(NotificationLog)
        if user_id:
            query = query.filter(NotificationLog.user_id == user_id)
        return query.order_by(NotificationLog.created_at.desc()).all()

# Helper function to generate default templates if they don't exist
def ensure_default_templates(db: Session):
    defaults = [
        {
            "name": "ReservationCreated",
            "subject_template": "Booking Confirmed - Specialist {specialist_name}",
            "body_template": "Dear {patient_name}, your booking with specialist {specialist_name} on {time} is confirmed.",
            "channel": "EMAIL"
        },
        {
            "name": "ReservationCancelled",
            "subject_template": "Booking Cancelled - Specialist {specialist_name}",
            "body_template": "Dear {patient_name}, your booking with specialist {specialist_name} on {time} has been cancelled.",
            "channel": "EMAIL"
        },
        {
            "name": "ReservationModified",
            "subject_template": "Booking Rescheduled - Specialist {specialist_name}",
            "body_template": "Dear {patient_name}, your booking with specialist {specialist_name} has been rescheduled to {time}.",
            "channel": "EMAIL"
        }
    ]
    for d in defaults:
        existing = db.query(NotificationTemplate).filter(NotificationTemplate.name == d["name"]).first()
        if not existing:
            template = NotificationTemplate(**d)
            db.add(template)
    db.commit()

# Event listeners
async def process_reservation_event(event_name: str, data: dict):
    logger.info(f"Processing event {event_name} inside Notification module")
    db = SessionLocal()
    try:
        ensure_default_templates(db)
        
        patient_id = data.get("patient_id")
        specialist_id = data.get("specialist_id")
        appointment_time = data.get("appointment_time")
        
        # Get patient details
        patient = db.query(User).filter(User.user_id == patient_id).first()
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
        recipient = patient.email if patient else "unknown@patient.com"

        # Get specialist details
        specialist = db.query(User).filter(User.user_id == specialist_id).first()
        specialist_name = f"{specialist.first_name} {specialist.last_name}" if specialist else "Specialist"

        # Look up template
        template = db.query(NotificationTemplate).filter(NotificationTemplate.name == event_name).first()
        
        subject = f"Booking Alert: {event_name}"
        body = f"Alert for booking with specialist {specialist_name} at {appointment_time}"
        template_id = None
        channel = "EMAIL"

        if template:
            template_id = template.template_id
            channel = template.channel
            try:
                subject = template.subject_template.format(
                    patient_name=patient_name,
                    specialist_name=specialist_name,
                    time=appointment_time
                )
                body = template.body_template.format(
                    patient_name=patient_name,
                    specialist_name=specialist_name,
                    time=appointment_time
                )
            except Exception as format_err:
                logger.error(f"Failed to format template: {format_err}")
                # Use defaults as fallback

        # Log simulated notification send
        log = NotificationLog(
            user_id=patient_id,
            template_id=template_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            status="SENT",
            sent_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        logger.info(f"Successfully sent simulated {channel} notification to {recipient} for reservation {data.get('reservation_id')}")

    except Exception as e:
        logger.error(f"Error processing notification event {event_name}: {e}", exc_info=True)
    finally:
        db.close()

async def on_reservation_created(data: dict):
    await process_reservation_event("ReservationCreated", data)

async def on_reservation_cancelled(data: dict):
    await process_reservation_event("ReservationCancelled", data)

async def on_reservation_modified(data: dict):
    await process_reservation_event("ReservationModified", data)

def setup_notification_listeners():
    event_bus.subscribe("ReservationCreated", on_reservation_created)
    event_bus.subscribe("ReservationCancelled", on_reservation_cancelled)
    event_bus.subscribe("ReservationModified", on_reservation_modified)
