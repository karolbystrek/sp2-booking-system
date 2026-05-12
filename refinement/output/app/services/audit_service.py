from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(db: Session, event_type: str, user_id: int | None = None, slot_id: int | None = None, details: str | None = None) -> None:
    entry = AuditLog(
        event_type=event_type,
        user_id=user_id,
        slot_id=slot_id,
        timestamp=datetime.utcnow(),
        details=details,
    )
    db.add(entry)
    db.flush()


def get_all_logs(db: Session) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
