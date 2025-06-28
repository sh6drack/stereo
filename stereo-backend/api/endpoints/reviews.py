from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
from datetime import date
from pydantic import BaseModel

from database.database import get_db
from database.models import Review

router = APIRouter(prefix="/reviews", tags=["reviews"])

class ReviewCreate(BaseModel):
    album_id: UUID
    user_id: UUID
    review_text: str
    rating: int

# handles creating, reading, updating and deleting album reviews

class ReviewResponse(BaseModel):
    id: UUID
    album_id: UUID
    user_id: UUID
    review_text: str
    rating: int
    created_at: date

    class Config:
        from_attributes = True

@router.get("/{album_id}", response_model=List[ReviewResponse])
def get_reviews(album_id: UUID, db: Session = Depends(get_db)):
    # gets all reviews for a specific album by its id
    reviews = db.query(Review).filter(Review.album_id == album_id).all()
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this album")
    
    return reviews

@router.post("/", response_model=ReviewResponse)
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    # creates a new review for an album
    db_review = Review(
        id=uuid.uuid4(),
        album_id=review.album_id,
        user_id=review.user_id,
        review_text=review.review_text,
        rating=review.rating,
        created_at=date.today()
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(review_id: UUID, review: ReviewCreate, db: Session = Depends(get_db)):
    # updates an existing review by its id
    db_review = db.query(Review).filter(Review.id == review_id).first()
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # update the review fields
    for field, value in review.model_dump().items():
        setattr(db_review, field, value)
    
    # type: ignore for sqlalchemy column assignment
    db_review.updated_at = date.today()  # type: ignore
    db.commit()
    db.refresh(db_review)
    
    return db_review


@router.delete("/{review_id}", response_model=ReviewResponse)
def delete_review(review_id: UUID, db: Session = Depends(get_db)):
    # deletes a review by its id
    db_review = db.query(Review).filter(Review.id == review_id).first()
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(db_review)
    db.commit()
    
    return db_review
