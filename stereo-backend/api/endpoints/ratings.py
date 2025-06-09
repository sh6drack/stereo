from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models
from uuid import UUID
import uuid

from database.database import get_db
from database.models import Album, TrendingAlbum, Rating, Review
from pydantic import BaseModel
from typing import List
from datetime import date

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

#get /ratings
@router.get("/{album_id}", response_model=List[RatingResponse])
def get_ratings(album_id: UUID, db: Session = Depends(get_db)):
    """
    retrieve all ratings for a specific album by its ID
    """
    ratings = db.query(models.Rating).filter(models.Rating.album_id == album_id).all()
    if not ratings:
        raise HTTPException(status_code=404, detail="No ratings found for this album")
    return ratings

#post /ratings
@router.post("/", response_model=RatingResponse)
def create_rating(rating: RatingCreate, db: Session = Depends(get_db)):
    """
    Create a new rating for an album
    """
    db_rating = models.Rating(
        id=uuid.uuid4(),
        album_id=rating.album_id,
        user_id=rating.user_id,
        rating=rating.rating,
        created_at = date.today(),    )
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating

#update /ratings/{rating_id}
@router.put("/{rating_id}", response_model=RatingResponse)
def update_rating(rating_id: UUID, rating: RatingCreate, db: Session = Depends(get_db)):
    """
    Update an existing rating by its ID
    """
    db_rating = db.query(models.Rating).filter(models.Rating.id == rating_id).first()
    if not db_rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    db_rating.album_id = rating.album_id
    db_rating.user_id = rating.user_id
    db_rating.rating = rating.rating
    db_rating.updated_at = date.today()
    
    db.commit()
    db.refresh(db_rating)
    return db_rating


@router.post("/albums/{album_id}/rate", response_model=RatingResponse)
def rate_album(album_id: UUID, rating_value: int, user_id: UUID, db: Session = Depends(get_db)):
    """
    Rate an album with a simplified endpoint
    """
    # rating is between 1-10
    if rating_value < 1 or rating_value > 10:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")
    
    # checking if album exists
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # has the user already rated this album?
    existing_rating = db.query(Rating).filter(
        Rating.album_id == album_id,
        Rating.user_id == user_id
    ).first()
    
    if existing_rating:
        # update existing rating
        existing_rating.rating = rating_value
        existing_rating.updated_at = date.today()
        db.commit()
        db.refresh(existing_rating)
        return existing_rating
    else:
        # creating a new rating
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