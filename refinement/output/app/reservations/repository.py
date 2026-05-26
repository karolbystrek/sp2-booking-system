from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.reservations.models import Reservation
from app.reservations.schemas import ReservationCreate, ReservationModify

class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, reservation_id: str) -> Optional[Reservation]:
        return self.db.query(Reservation).filter(Reservation.reservation_id == reservation_id).first()

    def get_active_count_for_patient(self, patient_id: str) -> int:
        # Limit 3 active reservations (PENDING or CONFIRMED)
        return self.db.query(Reservation).filter(
            and_(
                Reservation.patient_id == patient_id,
                Reservation.status.in_(["PENDING", "CONFIRMED"])
            )
        ).count()

    def get_overlapping_reservations(
        self,
        specialist_id: str,
        start_time: datetime,
        end_time: datetime,
        exclude_reservation_id: Optional[str] = None
    ) -> List[Reservation]:
        # To avoid SQLite datetime arithmetic limitations in SQL,
        # fetch active reservations for that specialist on the same day (+/- 1 day to be safe)
        day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        day_end = end_time.replace(hour=23, minute=59, second=59, microsecond=999999) + timedelta(days=1)
        
        query = self.db.query(Reservation).filter(
            and_(
                Reservation.specialist_id == specialist_id,
                Reservation.status.in_(["PENDING", "CONFIRMED"]),
                Reservation.appointment_time >= day_start,
                Reservation.appointment_time <= day_end
            )
        )
        if exclude_reservation_id:
            query = query.filter(Reservation.reservation_id != exclude_reservation_id)
            
        active_reservations = query.all()
        
        # Check overlaps in Python for reliability and flexibility
        overlapping = []
        for res in active_reservations:
            res_start = res.appointment_time
            res_end = res.appointment_time + timedelta(minutes=res.duration_minutes)
            
            # overlap condition: start1 < end2 and end1 > start2
            if start_time < res_end and end_time > res_start:
                overlapping.append(res)
                
        return overlapping

    def create_reservation(self, payload: ReservationCreate) -> Reservation:
        reservation = Reservation(
            patient_id=payload.patient_id,
            specialist_id=payload.specialist_id,
            appointment_time=payload.appointment_time,
            duration_minutes=payload.duration_minutes,
            status="CONFIRMED"  # Defaults to CONFIRMED as per standard flow
        )
        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        return reservation

    def update_reservation(self, reservation: Reservation) -> Reservation:
        self.db.commit()
        self.db.refresh(reservation)
        return reservation

    def get_reservations_by_patient(self, patient_id: str) -> List[Reservation]:
        return self.db.query(Reservation).filter(
            Reservation.patient_id == patient_id
        ).order_by(Reservation.appointment_time.asc()).all()

    def get_reservations_by_specialist(
        self, 
        specialist_id: str, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> List[Reservation]:
        query = self.db.query(Reservation).filter(Reservation.specialist_id == specialist_id)
        if start_time:
            query = query.filter(Reservation.appointment_time >= start_time)
        if end_time:
            query = query.filter(Reservation.appointment_time <= end_time)
        return query.order_by(Reservation.appointment_time.asc()).all()
