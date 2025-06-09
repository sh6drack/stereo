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

router = APIRouter(prefix="/reviews", tags=["reviews"])

class ReviewCreate(BaseModel):
    album_id: UUID
    user_id: UUID
    content: str
    rating: int

# we need create review for album , get all reviews, get one review, update a review
# and delete a review

class ReviewResponse(BaseModel):
    id: UUID
    album_id: UUID
    user_id: UUID
    content: str
    rating: int
    created_at: date

    class Config:
        orm_mode = True

@router.get("/{album_id}", response_model=List[ReviewResponse])
def get_reviews(album_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve all reviews for a specific album byt its ID
    """

    reviews = db.query(models.Review).filter(models.Review.album_id == album_id).all()
    if not reviews:
        raise HTTPException(status_code=404, detail="")
    
    return reviews

@router.post("/", response_model=ReviewResponse)
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    """
    create a new review for an album
    """
    db_review = models.Review(
        id=uuid.uuid4(),
        album_id=review.album_id,
        user_id=review.user_id,
        content=review.content,
        rating=review.rating,
        created_at=date.today()
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(review_id: UUID, review: ReviewCreate, db: Session = Depends(get_db)):
    """
    update an existing review by its ID
    """
    db_review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db_review.album_id = review.album_id
    db_review.user_id = review.user_id
    db_review.content = review.content
    db_review.rating = review.rating
    db.commit()
    db.refresh(db_review)
    
    return db_review


@router.delete("/{review_id}", response_model=ReviewResponse)
def delete_review(review_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a review by its ID
    """
    db_review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(db_review)
    db.commit()
    
    return db_review
