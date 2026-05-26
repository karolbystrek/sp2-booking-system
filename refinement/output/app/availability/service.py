from datetime import datetime, date, time, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.identity.models import User, Role, SpecialistDetails
from app.schedule.models import SpecialistSchedule
from app.reservations.models import Reservation
from app.availability.schemas import SpecialistAvailabilityResponse, AvailableSlot

class AvailabilityService:
    def __init__(self, db: Session):
        self.db = db

    def get_available_appointments(
        self,
        query_date: date,
        specialization: Optional[str] = None,
        specialist_id: Optional[str] = None,
        min_duration: int = 30
    ) -> List[SpecialistAvailabilityResponse]:
        
        # 1. Resolve specialists
        spec_query = self.db.query(User).join(User.roles).filter(Role.name == "Specialist")
        
        if specialist_id:
            spec_query = spec_query.filter(User.user_id == specialist_id)
        if specialization:
            spec_query = spec_query.join(User.specialist_details).filter(
                SpecialistDetails.specialization.ilike(f"%{specialization}%")
            )
            
        specialists = spec_query.all()
        
        # Define the target date range
        day_start = datetime.combine(query_date, time.min)
        day_end = datetime.combine(query_date, time.max)
        now = datetime.utcnow()

        response = []

        for specialist in specialists:
            spec_details = specialist.specialist_details
            spec_name = f"{specialist.first_name} {specialist.last_name}".strip() or specialist.email
            spec_specialization = spec_details.specialization if spec_details else "General"
            
            # Fetch all schedule blocks for this specialist on the target date
            blocks = self.db.query(SpecialistSchedule).filter(
                and_(
                    SpecialistSchedule.specialist_id == specialist.user_id,
                    SpecialistSchedule.end_time >= day_start,
                    SpecialistSchedule.start_time <= day_end
                )
            ).all()

            # Fetch active bookings for this specialist on the target date
            active_bookings = self.db.query(Reservation).filter(
                and_(
                    Reservation.specialist_id == specialist.user_id,
                    Reservation.status.in_(["PENDING", "CONFIRMED"]),
                    Reservation.appointment_time >= day_start - timedelta(days=1),  # Buffer to cover spanning bookings
                    Reservation.appointment_time <= day_end + timedelta(days=1)
                )
            ).all()

            available_slots = []

            # 2. Iterate through available schedule blocks
            available_blocks = [b for b in blocks if b.block_type == "AVAILABLE"]
            
            for block in available_blocks:
                # Truncate block to target date bounds
                block_start = max(block.start_time, day_start)
                block_end = min(block.end_time, day_end)

                # Generate slots of length min_duration
                current_time = block_start
                while current_time + timedelta(minutes=min_duration) <= block_end:
                    slot_start = current_time
                    slot_end = current_time + timedelta(minutes=min_duration)
                    current_time += timedelta(minutes=min_duration)  # Step by duration or step by slot increment (e.g. 30min)

                    # Do not offer slots in the past
                    if slot_start < now:
                        continue

                    # Check overlaps with BREAK, HOLIDAY, UNAVAILABLE blocks
                    has_block_overlap = False
                    for b in blocks:
                        if b.block_type in ["BREAK", "HOLIDAY", "UNAVAILABLE"]:
                            if slot_start < b.end_time and slot_end > b.start_time:
                                has_block_overlap = True
                                break
                    if has_block_overlap:
                        continue

                    # Check overlaps with existing bookings
                    has_booking_overlap = False
                    for booking in active_bookings:
                        booking_end = booking.appointment_time + timedelta(minutes=booking.duration_minutes)
                        if slot_start < booking_end and slot_end > booking.appointment_time:
                            has_booking_overlap = True
                            break
                    if has_booking_overlap:
                        continue

                    # If no overlap, it's a valid slot!
                    available_slots.append(AvailableSlot(
                        start_time=slot_start,
                        end_time=slot_end
                    ))

            response.append(SpecialistAvailabilityResponse(
                specialist_id=specialist.user_id,
                specialist_name=spec_name,
                specialization=spec_specialization,
                available_slots=available_slots
            ))

        return response
