from sqlalchemy import create_engine, Column, String, Integer, Date, ForeignKey, Table, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import uuid

Base = declarative_base()

user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.user_id'), primary_key=True),
    Column('role_id', String, ForeignKey('roles.role_id'), primary_key=True)
)

class Role(Base):
    __tablename__ = 'roles'
    role_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False)

class User(Base):
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone_number = Column(String(20))
    
    roles = relationship('Role', secondary=user_roles)
    specialist_details = relationship('SpecialistDetails', back_populates='user', uselist=False)

class SpecialistDetails(Base):
    __tablename__ = 'specialist_details'
    specialist_id = Column(String, ForeignKey('users.user_id'), primary_key=True)
    specialization = Column(String(100))
    default_appointment_duration_minutes = Column(Integer, default=30)
    bio = Column(Text)
    office_address = Column(String(255))
    
    user = relationship('User', back_populates='specialist_details')

engine = create_engine('sqlite:///identity.db', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
