from datetime import datetime, timedelta

import pytest

from audit_service import AuditService
from booking_service import BookingService
from models import Slot, SlotStatus
from repository import InMemoryRepository
from schedule_service import ScheduleService


DEFAULT_SPECIALIST_ID = 10
DEFAULT_USER_ID = 1


@pytest.fixture()
def repo():
    """Create a fresh in-memory repository for every test."""
    return InMemoryRepository()


@pytest.fixture()
def schedule_service(repo):
    """Create the scheduling service used by BookingService."""
    return ScheduleService(repo)


@pytest.fixture()
def audit_service(repo):
    """Create the audit service used by BookingService."""
    return AuditService(repo)


@pytest.fixture()
def service(repo, schedule_service, audit_service):
    """Create BookingService with real collaborators and isolated state."""
    return BookingService(repo, schedule_service, audit_service)


@pytest.fixture()
def slot_factory():
    """Factory for deterministic, readable slot test data."""

    def create_slot(
        slot_id: int,
        specialist_id: int = DEFAULT_SPECIALIST_ID,
        hours_from_now: int = 48,
        minutes_from_now: int = 0,
        duration_minutes: int = 30,
        status: SlotStatus = SlotStatus.AVAILABLE,
    ) -> Slot:
        start = datetime.utcnow() + timedelta(
            hours=hours_from_now,
            minutes=minutes_from_now,
        )
        end = start + timedelta(minutes=duration_minutes)
        return Slot(
            id=slot_id,
            specialist_id=specialist_id,
            start_time=start,
            end_time=end,
            status=status,
        )

    return create_slot
