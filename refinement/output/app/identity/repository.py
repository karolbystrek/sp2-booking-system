from typing import Optional, List
from sqlalchemy.orm import Session
from app.identity.models import User, Role, SpecialistDetails
from app.identity.schemas import UserRegister, UserUpdate

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.user_id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_role_by_name(self, name: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.name == name).first()

    def create_role(self, name: str) -> Role:
        role = Role(name=name)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def get_all_users(self) -> List[User]:
        return self.db.query(User).all()

    def create_user(self, payload: UserRegister, password_hash: str, role_obj: Role) -> User:
        user = User(
            email=payload.email,
            password_hash=password_hash,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone_number=payload.phone_number,
            date_of_birth=payload.date_of_birth
        )
        user.roles.append(role_obj)
        
        self.db.add(user)
        self.db.commit() # Commits user to get ID for specialist details if needed
        self.db.refresh(user)

        if payload.role.lower() == "specialist" and payload.specialist_details:
            spec_det = SpecialistDetails(
                specialist_id=user.user_id,
                specialization=payload.specialist_details.specialization,
                default_appointment_duration_minutes=payload.specialist_details.default_appointment_duration_minutes,
                bio=payload.specialist_details.bio,
                office_address=payload.specialist_details.office_address
            )
            self.db.add(spec_det)
            self.db.commit()
            self.db.refresh(user)

        return user

    def update_user(self, user: User, payload: UserUpdate) -> User:
        if payload.first_name is not None:
            user.first_name = payload.first_name
        if payload.last_name is not None:
            user.last_name = payload.last_name
        if payload.phone_number is not None:
            user.phone_number = payload.phone_number
        if payload.date_of_birth is not None:
            user.date_of_birth = payload.date_of_birth

        # Handle specialist details update if user is a specialist
        if payload.specialist_details is not None:
            if user.specialist_details:
                user.specialist_details.specialization = payload.specialist_details.specialization
                user.specialist_details.default_appointment_duration_minutes = payload.specialist_details.default_appointment_duration_minutes
                user.specialist_details.bio = payload.specialist_details.bio
                user.specialist_details.office_address = payload.specialist_details.office_address
            else:
                # If they didn't have details yet but now have them
                spec_det = SpecialistDetails(
                    specialist_id=user.user_id,
                    specialization=payload.specialist_details.specialization,
                    default_appointment_duration_minutes=payload.specialist_details.default_appointment_duration_minutes,
                    bio=payload.specialist_details.bio,
                    office_address=payload.specialist_details.office_address
                )
                self.db.add(spec_det)
                
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()

    def assign_role(self, user: User, role_obj: Role) -> User:
        if role_obj not in user.roles:
            user.roles.append(role_obj)
            self.db.commit()
            self.db.refresh(user)
        return user

    def remove_role(self, user: User, role_obj: Role) -> User:
        if role_obj in user.roles:
            user.roles.remove(role_obj)
            self.db.commit()
            self.db.refresh(user)
        return user
