from sqlalchemy.orm import Session

from app.models import AuditLog


class AuditService:
    @staticmethod
    def log(
        db: Session,
        event_type: str,
        details: str,
        user_id: int | None = None,
        slot_id: int | None = None,
    ):
        audit_log = AuditLog(
            event_type=event_type,
            details=details,
            user_id=user_id,
            slot_id=slot_id,
        )

        db.add(audit_log)
        db.commit()