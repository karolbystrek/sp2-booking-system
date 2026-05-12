from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from .database import get_db
from .models import User

def get_current_user(x_user_id: Optional[int] = Header(None), db: Session = Depends(get_db)):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header missing")
    user = db.query(User).filter(User.id == x_user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
