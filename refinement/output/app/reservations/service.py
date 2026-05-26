import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.exceptions import ConflictException, NotFoundException, ForbiddenException
from app.reservations.repository import ReservationRepository
from app.reservations.models import Reservation
from app.reservations.schemas import ReservationCreate, ReservationModify
from app.schedule.repository import ScheduleRepository
from app.identity.models import User
from app.events import event_bus

logger = logging.getLogger(__name__)

class ReservationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReservationRepository(db)
        self.schedule_repo = ScheduleRepository(db)

    def _verify_user_exists(self, user_id: str, role_needed: Optional[str] = None) -> User:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise NotFoundException(f"User {user_id} not found")
        if role_needed:
            roles = [r.name for r in user.roles]
            if role_needed not in roles and "Admin" not in roles and "Administrator" not in roles:
                raise ForbiddenException(f"User must have role {role_needed}")
        return user

    def _validate_availability(
        self, 
        specialist_id: str, 
        start_time: datetime, 
        duration_minutes: int,
        exclude_reservation_id: Optional[str] = None
    ):
        end_time = start_time + timedelta(minutes=duration_minutes)

        # 1. Enforce no overlapping bookings (active reservations only)
        overlapping_bookings = self.repo.get_overlapping_reservations(
            specialist_id=specialist_id,
            start_time=start_time,
            end_time=end_time,
            exclude_reservation_id=exclude_reservation_id
        )
        if overlapping_bookings:
            raise ConflictException("This slot is already booked by another reservation.")

        # 2. Check specialist's schedule blocks
        # Fetch blocks for the date of the reservation
        blocks = self.schedule_repo.get_blocks_by_specialist(specialist_id)
        
        # Check if there is an AVAILABLE block that completely contains the booking
        has_available_block = False
        for block in blocks:
            if block.block_type == "AVAILABLE":
                if block.start_time <= start_time and block.end_time >= end_time:
                    has_available_block = True
                    break
                    
        if not has_available_block:
            raise ConflictException("Specialist is not scheduled to be available at this time.")

        # Check if any BREAK, HOLIDAY or UNAVAILABLE block overlaps with the booking
        for block in blocks:
            if block.block_type in ["BREAK", "HOLIDAY", "UNAVAILABLE"]:
                # overlap if start1 < end2 and end1 > start2
                if start_time < block.end_time and end_time > block.start_time:
                    raise ConflictException(f"Specialist has a conflicting block ({block.block_type}) during this time.")

    async def create_reservation(self, payload: ReservationCreate) -> Reservation:
        logger.info(f"Creating reservation for patient {payload.patient_id} with specialist {payload.specialist_id}")

        self._verify_user_exists(payload.patient_id)
        self._verify_user_exists(payload.specialist_id, role_needed="Specialist")

        # Check max 3 active reservations limit
        active_count = self.repo.get_active_count_for_patient(payload.patient_id)
        if active_count >= 3:
            raise ConflictException("Patient has reached the limit of 3 active reservations.")

        # Validate schedule availability and collision check
        self._validate_availability(payload.specialist_id, payload.appointment_time, payload.duration_minutes)

        # Create reservation
        reservation = self.repo.create_reservation(payload)

        # Publish EDA event
        await event_bus.publish("ReservationCreated", {
            "reservation_id": reservation.reservation_id,
            "patient_id": reservation.patient_id,
            "specialist_id": reservation.specialist_id,
            "appointment_time": reservation.appointment_time.isoformat(),
            "duration_minutes": reservation.duration_minutes,
            "status": reservation.status
        })

        return reservation

    def get_reservation(self, reservation_id: str) -> Reservation:
        reservation = self.repo.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundException("Reservation not found")
        return reservation

    async def cancel_reservation(self, reservation_id: str, request_user_id: str) -> Reservation:
        logger.info(f"Cancelling reservation {reservation_id} by user {request_user_id}")
        reservation = self.repo.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundException("Reservation not found")

        # Access check: only patient, specialist, or admin can cancel
        request_user = self._verify_user_exists(request_user_id)
        is_admin = any(r.name in ["Admin", "Administrator"] for r in request_user.roles)
        if not is_admin and request_user_id not in [reservation.patient_id, reservation.specialist_id]:
            raise ForbiddenException("You do not have permission to cancel this reservation")

        if reservation.status == "CANCELLED":
            raise ConflictException("Reservation is already cancelled")

        reservation.status = "CANCELLED"
        updated_res = self.repo.update_reservation(reservation)

        # Publish EDA event
        await event_bus.publish("ReservationCancelled", {
            "reservation_id": updated_res.reservation_id,
            "patient_id": updated_res.patient_id,
            "specialist_id": updated_res.specialist_id,
            "appointment_time": updated_res.appointment_time.isoformat(),
            "status": updated_res.status
        })

        return updated_res

    async def modify_reservation(
        self, 
        reservation_id: str, 
        payload: ReservationModify,
        request_user_id: str
    ) -> Reservation:
        logger.info(f"Modifying reservation {reservation_id} by user {request_user_id}")
        reservation = self.repo.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundException("Reservation not found")

        # Only Specialist or Admin can modify
        request_user = self._verify_user_exists(request_user_id)
        is_admin = any(r.name in ["Admin", "Administrator"] for r in request_user.roles)
        is_specialist = any(r.name == "Specialist" for r in request_user.roles)
        
        if not is_admin and (not is_specialist or request_user_id != reservation.specialist_id):
            raise ForbiddenException("Only the assigned specialist or an administrator can modify a reservation")

        if reservation.status == "CANCELLED":
            raise ConflictException("Cannot modify a cancelled reservation")

        # Validate schedule availability for new parameters
        self._validate_availability(
            specialist_id=reservation.specialist_id,
            start_time=payload.appointment_time,
            duration_minutes=payload.duration_minutes,
            exclude_reservation_id=reservation_id
        )

        reservation.appointment_time = payload.appointment_time
        reservation.duration_minutes = payload.duration_minutes
        
        updated_res = self.repo.update_reservation(reservation)

        # Publish EDA event
        await event_bus.publish("ReservationModified", {
            "reservation_id": updated_res.reservation_id,
            "patient_id": updated_res.patient_id,
            "specialist_id": updated_res.specialist_id,
            "appointment_time": updated_res.appointment_time.isoformat(),
            "duration_minutes": updated_res.duration_minutes,
            "status": updated_res.status
        })

        return updated_res

    def get_patient_reservations(self, patient_id: str, request_user_id: str) -> List[Reservation]:
        request_user = self._verify_user_exists(request_user_id)
        is_admin = any(r.name in ["Admin", "Administrator"] for r in request_user.roles)
        if not is_admin and request_user_id != patient_id:
            raise ForbiddenException("You cannot access another patient's reservations")
        return self.repo.get_reservations_by_patient(patient_id)

    def get_specialist_reservations(
        self, 
        specialist_id: str, 
        request_user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Reservation]:
        request_user = self._verify_user_exists(request_user_id)
        is_admin = any(r.name in ["Admin", "Administrator"] for r in request_user.roles)
        if not is_admin and request_user_id != specialist_id:
            raise ForbiddenException("You cannot access another specialist's reservations")
        return self.repo.get_reservations_by_specialist(specialist_id, start_time, end_time)
