from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from uuid import UUID
import uuid

from database import get_db
from models import Album, TrendingAlbum
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
@router.get("{album_id}", response_model=List[RatingResponse])
def get_ratings(album_id: UUID, db: Session = Depends(get_db)):
    """retrieve all ratings for a specific album by its ID"""
    ratings = db.query(models.Rating).filter(models.Rating.album_id == album_id).all()
    if not ratings:
        raise HTTPException(status_code=404, detail="No ratings found for this album")
    return ratings

#post /ratings
@router.post("/", response_model=RatingResponse)
def create_rating(rating: RatingCreate, db: Session = Depends(get_db)):
    # Example implementation, adjust as needed
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
    """Update an existing rating by its ID"""
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