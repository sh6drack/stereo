from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
from datetime import date
from pydantic import BaseModel

from database.database import get_db
from database.models import Album, Rating

router = APIRouter(prefix="/ratings", tags=["ratings"])


class RatingCreate(BaseModel):
    album_id: UUID
    user_id: UUID
    rating: int

class RatingResponse(BaseModel):
    id: UUID
    album_id: UUID
    user_id: UUID
    rating: int

    class Config:
        orm_mode = True

@router.get("/{album_id}", response_model=List[RatingResponse])
def get_ratings(album_id: UUID, db: Session = Depends(get_db)):
    # retrieves all ratings for a specific album by its id
    ratings = db.query(Rating).filter(Rating.album_id == album_id).all()
    if not ratings:
        raise HTTPException(status_code=404, detail="No ratings found for this album")
    return ratings

@router.post("/", response_model=RatingResponse)
def create_rating(rating: RatingCreate, db: Session = Depends(get_db)):
    # creates new rating for an album
    db_rating = Rating(
        id=uuid.uuid4(),
        album_id=rating.album_id,
        user_id=rating.user_id,
        rating=rating.rating,
        created_at=date.today()
    )
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating

@router.put("/{rating_id}", response_model=RatingResponse)
def update_rating(rating_id: UUID, rating: RatingCreate, db: Session = Depends(get_db)):
    # updates existing rating by its id
    db_rating = db.query(Rating).filter(Rating.id == rating_id).first()
    if not db_rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    setattr(db_rating, 'album_id', rating.album_id)
    setattr(db_rating, 'user_id', rating.user_id)
    setattr(db_rating, 'rating', rating.rating)
    setattr(db_rating, 'updated_at', date.today())
    
    db.commit()
    db.refresh(db_rating)
    return db_rating


@router.post("/albums/{album_id}/rate", response_model=RatingResponse)
def rate_album(album_id: UUID, rating_value: int, user_id: UUID, db: Session = Depends(get_db)):
    # rates an album with simplified endpoint
    # rating must be between 1-10
    if rating_value < 1 or rating_value > 10:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")
    
    # check if album exists
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # check if user already rated this album
    existing_rating = db.query(Rating).filter(
        Rating.album_id == album_id,
        Rating.user_id == user_id
    ).first()
    
    if existing_rating:
        # update existing rating
        setattr(existing_rating, 'rating', rating_value)
        setattr(existing_rating, 'updated_at', date.today())
        db.commit()
        db.refresh(existing_rating)
        return existing_rating
    else:
        # create new rating
        new_rating = Rating(
            id=uuid.uuid4(),
            album_id=album_id,
            user_id=user_id,
            rating=rating_value,
            created_at=date.today()
        )
        db.add(new_rating)
        db.commit()
        db.refresh(new_rating)
        return new_rating