class AuditService:
    def __init__(self, repo):
        self.repo = repo

    def log_booking_created(self, user_id: int, slot_id: int):
        self.repo.add_audit_event(
            event_type="BOOKING_CREATED",
            user_id=user_id,
            slot_id=slot_id,
            details="Booking successfully created",
        )

    def log_booking_cancelled(self, user_id: int, slot_id: int):
        self.repo.add_audit_event(
            event_type="BOOKING_CANCELLED",
            user_id=user_id,
            slot_id=slot_id,
            details="Booking successfully cancelled",
        )

    def log_booking_rejected(self, user_id: int, slot_id: int, reason: str):
        self.repo.add_audit_event(
            event_type="BOOKING_REJECTED",
            user_id=user_id,
            slot_id=slot_id,
            details=reason,
        )

    def get_audit_log(self):
        return self.repo.get_audit_events()
