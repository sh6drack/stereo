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
from .reviews import ReviewResponse

import requests
import time

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

class AlbumSearchResult(BaseModel):
    mbid: str = None  # MusicBrainz ID (if from API)
    title: str
    artist: str
    release_date: str
    cover_url: str = None
    in_database: bool  # True if already in your database

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
@router.get("/{album_id}/reviews", response_model=List[ReviewResponse])
def get_album_reviews(album_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve all reviews for a specific album
    """
    # the album exists?
    album = db.query(Album).filter(Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    reviews = db.query(Review).filter(Review.album_id == album_id).all()
    return reviews


#get /albums/{album_id}/average-rating
@router.get("/{album_id}/average-rating")
def get_album_average_rating(album_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve the average rating for a specific album
    """
    
    # the album exists?
    album = db.query(Album).filter(Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    from sqlalchemy import func
    avg_rating = db.query(func.avg(Rating.rating)).filter(Rating.album_id == album_id).scalar()
    return {"average_rating": avg_rating or 0} #0 if no ratings exist

#helper function to search musicbrainz api
def search_musicbrainz_api(query:str, limit: int = 10):
    """
    Search for albums in the MusicBrainz API.
    """
    url = "https://musicbrainz.org/ws/2/release"
    params = {
        "query": query,
        "fmt": "json",
        "limit": limit
    }
    headers = {
        "User-Agent": "StereoApp/1.0 (your-email@example.com)"  # Replace with your email
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for release in data.get('releases', []):
            result = AlbumSearchResult(
                mbid=release['id'],
                title=release['title'],
                artist=release['artist-credit'][0]['artist']['name'] if release.get('artist-credit') else "Unknown Artist",
                release_date=release.get('date', 'Unknown'),
                cover_url=f"https://coverartarchive.org/release/{release['id']}/front-500",
                in_database=False
            )
            results.append(result)
        
        return results
    except Exception as e:
        print(f"Error searching MusicBrainz: {e}")
        return []
    
@router.get("/search", response_model=List[AlbumSearchResult])
def search_albums(q: str, db: Session = Depends(get_db)):
    """
    Search for albums in local database and MusicBrainz
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    
    search_term = q.strip().lower()
    
    # 1. Search local database first
    local_albums = db.query(Album).filter(
        (Album.title.ilike(f"%{search_term}%")) | 
        (Album.artist.ilike(f"%{search_term}%"))
    ).limit(10).all()
    
    # Convert local results to search results
    local_results = []
    for album in local_albums:
        result = AlbumSearchResult(
            mbid=None,  # Local albums might not have MBID stored
            title=album.title,
            artist=album.artist,
            release_date=str(album.release_date),
            cover_url=album.cover_url,
            in_database=True
        )
        local_results.append(result)
    
    # 2. If we have fewer than 10 results, search MusicBrainz
    if len(local_results) < 10:
        api_results = search_musicbrainz_api(q, limit=10 - len(local_results))
        
        # Filter out albums that are already in local results
        local_titles = {(album.title.lower(), album.artist.lower()) for album in local_albums}
        filtered_api_results = [
            result for result in api_results 
            if (result.title.lower(), result.artist.lower()) not in local_titles
        ]
        
        return local_results + filtered_api_results
    
    return local_results

@router.post("/add-from-search", response_model=AlbumResponse)
def add_album_from_search(album_data: AlbumSearchResult, db: Session = Depends(get_db)):
    """
    add an album to the database from search results
    """
    # album already exists?
    existing_album = db.query(Album).filter(
        Album.title.ilike(album_data.title),
        Album.artist.ilike(album_data.artist)
    ).first()
    
    if existing_album:
        return existing_album
    
    # parse release date
    try:
        if len(album_data.release_date) >= 4:
            year = album_data.release_date[:4]
            release_date = date(int(year), 1, 1)  # Default to January 1st
        else:
            release_date = date(2020, 1, 1)  # Fallback
    except:
        release_date = date(2020, 1, 1)  # Fallback
    
    # create new album
    new_album = Album(
        id=uuid.uuid4(),
        title=album_data.title,
        artist=album_data.artist,
        release_date=release_date,
        cover_url=album_data.cover_url or "https://via.placeholder.com/500x500?text=No+Cover+Art"
    )
    
    db.add(new_album)
    db.commit()
    db.refresh(new_album)
    
    return new_album