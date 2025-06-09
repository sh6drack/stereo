# need post register, post login, and get user profile endpoints
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models
from uuid import UUID
import uuid

from database.database import get_db
from models import Album, TrendingAlbum, Rating, Review
from pydantic import BaseModel
from typing import List
from datetime import date

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
        orm_mode = True #

@router.post("/register", response_model= UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user in the system.
    """

    hashed_password = hash_password(user.password)

    db_user = models.User(
        id=uuid.uuid4(),
        username=user.username,
        email=user.email,
        password_hash = hashed_password,
        created_at=date.today()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
def login_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    authenticate a user and return a user profile on success
    """
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return UserResponse.from_orm(db_user) 
    # ^this means we are returning the user profile in the same format as UserResponse model

@router.get("/profile/{user_id}", response_model=UserResponse)
def get_user_profile(user_id: UUID, db: Session = Depends(get_db)):
    """
    retrieve a user's profile by their ID.
    """

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")