# handles user registration, login, and profile endpoints
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
from datetime import date
from pydantic import BaseModel

from database.database import get_db
from database.models import User
from password_hashing import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    created_at: date

    class Config:
        orm_mode = True

@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # registers a new user in the system
    hashed_password = hash_password(user.password)

    db_user = User(
        id=uuid.uuid4(),
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        created_at=date.today()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
def login_user(user: UserCreate, db: Session = Depends(get_db)):
    # authenticates user and returns profile on success
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return UserResponse.model_validate(db_user)

@router.get("/profile/{user_id}", response_model=UserResponse)
def get_user_profile(user_id: UUID, db: Session = Depends(get_db)):
    # retrieves user profile by their id
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.model_validate(db_user)
