from sqlalchemy.orm import Session
from ..models import AuditLog

def log_event(db: Session, event_type: str, user_id: int = None, slot_id: int = None, details: str = None):
    audit_log = AuditLog(
        event_type=event_type,
        user_id=user_id,
        slot_id=slot_id,
        details=details
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log
