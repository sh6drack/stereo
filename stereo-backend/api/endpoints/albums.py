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

router = APIRouter(prefix="/albums", tags = ["albums"]) 
# prefix="/albums" sets the base path for all endpoints in this router
#tags = ["albums"] is used to group endpoints in the API documentation
# the router is used to create a new endpoint for the API

# models are used to define the structure of
# the data that will be sent and received by the API

class AlbumCreate(BaseModel): #what client sends
    title: str
    artist: str
    release_date: date
    cover_url: str

class AlbumResponse(BaseModel): #what client recieves
    id: UUID
    title: str
    artist: str
    release_date: date
    cover_url: str

    class Config:
        orm_mode = True #this allows the model to read data as if it were a SQLAlchemy model instance
        #could also do from_attributes = True, 

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

#get /albums/{album_id}
@router.get("/{album_id}", response_model=AlbumResponse)
# "/{album_id}" is a path parameter that will be replaced with the actual album ID when the endpoint is called
def get_album(album_id: UUID, db:Session = Depends(get_db)):
    #depends provides a way to inject dependencies into the endpoint func
    #allows us to use get_db to get a database session
    """
    Retrieve a specific album by its ID ; query the database for the album with the given ID
    """
    album = db.query(Album).filter (Album.id == album_id).first()
    #QUERY is used to retrieve data from database 
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    return album

#post /albums - create a new album
@router.post("/", response_model=AlbumResponse)
def create_album(album: AlbumCreate, db: Session = Depends(get_db)):
    """
    create a new album in the database
    """
    new_album = Album(
        id=uuid.uuid4(),  # generates new UUID for the album
        title=album.title,
        artist=album.artist,
        release_date=album.release_date,
        cover_url=album.cover_url
    )
    
    db.add(new_album)
    db.commit()
    db.refresh(new_album) #get the updated instance from the database

    return new_album

# get /albums/{album_id}/reviews
@router.get("/{album_id}/reviews", response_model=List[schemas.ReviewResponse])
def get_album_reviews(album_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve all reviews for a specific album
    """
    #first query the database to check if the album exists
    album = db.query(Album).filter(Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Placeholder return - will implement when we add Review model
    return {"message": f"Reviews for album {album_id} - to be implemented"}

#get /albums/{album_id}/average-rating
@router.get("/{album_id}/average-rating", response_model=float)
def get_album_average_rating(album_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve the average rating for a specific album
    """
    
    #first query the database to check if the album exists
    album = db.query(Album).filter(Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Placeholder return - will implement when we add Review model
    return {"message": f"Average rating for album {album_id} - to be implemented"}