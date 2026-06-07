from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models import SessionLocal, User, Role, SpecialistDetails, init_db
import jwt
from datetime import datetime, timedelta
import hashlib

app = FastAPI(title="Identity & Access Service")

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=1)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: str # "Patient" or "Specialist"

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    roles = [r.name for r in user.roles]
    access_token = create_access_token(data={"sub": user.user_id, "roles": roles})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    role = db.query(Role).filter(Role.name == req.role).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")

    new_user = User(
        email=req.email,
        password_hash=get_password_hash(req.password),
        first_name=req.first_name,
        last_name=req.last_name,
        roles=[role]
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    if req.role == "Specialist":
        details = SpecialistDetails(specialist_id=new_user.user_id)
        db.add(details)
        db.commit()
        
    return {"user_id": new_user.user_id, "message": "User registered successfully"}

@app.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.user_id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "roles": [r.name for r in user.roles]
    }
