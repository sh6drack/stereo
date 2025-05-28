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

router = APIRouter(prefix="/trending", tags=["trending"])
# prefix="/trending" sets the base path for all endpoints in this router
#tags = ["trending"] is used to group endpoints in the API documentation
# the router is used to create a new endpoint for the API

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
        orm_mode = True

@router.get("/", response_model=List[TrendingAlbumResponse])
def get_trending(db: Session = Depends(get_db)):
    """
    Retrieve the top 25 trending albums for a specific album ID.
    """
    trending_albums = (db.query(TrendingAlbum).
                       order_by(TrendingAlbum.rank).limit(25).all())
    if not trending_albums:
        raise HTTPException(status_code=404, detail="No trending albums found")
    return trending_albums

@router.post("/", response_model=TrendingAlbumCreate)
def create_trending_album(
    trending_album: TrendingAlbumCreate, db: Session = Depends(get_db)
):
    """
    Create a new trending album entry in the database.
    """
    db_trending_album = TrendingAlbum(
        album_id=trending_album.album_id,
        rank=trending_album.rank,
        week_start=trending_album.week_start,
    )
    db.add(db_trending_album)
    db.commit()
    db.refresh(db_trending_album)
    return db_trending_album