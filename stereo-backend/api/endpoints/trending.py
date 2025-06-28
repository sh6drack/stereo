from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import date
from pydantic import BaseModel

from database.database import get_db
from database.models import Album, TrendingAlbum, Rating
from sqlalchemy import func
from .albums import AlbumResponse

router = APIRouter(prefix="/trending", tags=["trending"])
# sets up trending endpoints with proper routing and api docs grouping

class TrendingAlbumCreate(BaseModel):
    album_id: UUID
    rank: int
    week_start: date

class TrendingAlbumResponse(BaseModel):
    id: UUID
    album_id: UUID
    rank: int
    week_start: date

    class Config:
        from_attributes = True

@router.get("/albums", response_model=List[AlbumResponse])
def get_trending(db: Session = Depends(get_db)):
    # gets top 25 trending albums with full album details and average ratings
    trending_albums = (db.query(Album, TrendingAlbum).
                       join(TrendingAlbum, Album.id == TrendingAlbum.album_id).
                       order_by(TrendingAlbum.rank).
                       limit(25).all())
    if not trending_albums: 
        raise HTTPException(status_code=404, detail="No trending albums found")
    
    # add average rating to each album
    result = []
    for album, trending in trending_albums:
        # calculate average rating
        avg_rating = db.query(func.avg(Rating.rating)).filter(Rating.album_id == album.id).scalar()
        
        # create album response with average rating
        album_dict = {
            "id": album.id,
            "title": album.title,
            "artist": album.artist,
            "release_date": album.release_date,
            "cover_url": album.cover_url,
            "description": album.description,
            "runtime_minutes": album.runtime_minutes,
            "musicbrainz_id": album.musicbrainz_id,
            "average_rating": round(avg_rating, 1) if avg_rating else None
        }
        result.append(AlbumResponse(**album_dict))
    
    return result

@router.post("/", response_model=TrendingAlbumResponse)
def create_trending_album(
    trending_album: TrendingAlbumCreate, db: Session = Depends(get_db)
):
    # creates new trending album entry in db
    db_trending_album = TrendingAlbum(
        album_id=trending_album.album_id,
        rank=trending_album.rank,
        week_start=trending_album.week_start,
    )
    db.add(db_trending_album)
    db.commit()
    db.refresh(db_trending_album)
    return db_trending_album