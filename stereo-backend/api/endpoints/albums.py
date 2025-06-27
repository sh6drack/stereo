from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
from datetime import date
from pydantic import BaseModel
import requests
from sqlalchemy import func

from database.database import get_db
from database.models import Album, Rating, Review
from .reviews import ReviewResponse

router = APIRouter(prefix="/albums", tags=["albums"])
# handles album endpoints with proper routing and api docs grouping

class AlbumCreate(BaseModel):  # what client sends
    title: str
    artist: str
    release_date: date
    cover_url: str

class AlbumResponse(BaseModel):  # what client receives
    id: UUID
    title: str
    artist: str
    release_date: date
    cover_url: str

    class Config:
        orm_mode = True 

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
    mbid: str | None = None  # musicbrainz id if from api
    title: str
    artist: str
    release_date: str
    cover_url: str | None = None
    in_database: bool  # true if already in database

@router.get("/{album_id}", response_model=AlbumResponse)
def get_album(album_id: UUID, db: Session = Depends(get_db)):
    # retrieves specific album by its id
    album = db.query(Album).filter(Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    return album

@router.post("/", response_model=AlbumResponse)
def create_album(album: AlbumCreate, db: Session = Depends(get_db)):
    # creates new album in the database
    new_album = Album(
        id=uuid.uuid4(),
        title=album.title,
        artist=album.artist,
        release_date=album.release_date,
        cover_url=album.cover_url
    )
    
    db.add(new_album)
    db.commit()
    db.refresh(new_album)

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
    
    avg_rating = db.query(func.avg(Rating.rating)).filter(Rating.album_id == album_id).scalar()
    return {"average_rating": avg_rating or 0}  # 0 if no ratings exist

def get_cover_art_url(mbid: str) -> str:
    # tries to get cover art from cover art archive, falls back to placeholder
    try:
        cover_response = requests.get(
            f"https://coverartarchive.org/release/{mbid}",
            headers={"User-Agent": "StereoApp/1.0 (stereo@example.com)"},
            timeout=5
        )
        if cover_response.status_code == 200:
            cover_data = cover_response.json()
            if cover_data.get('images'):
                # get the front cover or first image
                for image in cover_data['images']:
                    if image.get('front', False):
                        return image['image']
                # if no front cover, use first image
                return cover_data['images'][0]['image']
    except Exception:
        pass  # fall through to placeholder
    
    return "https://via.placeholder.com/500x500?text=No+Cover+Art"

def search_musicbrainz_api(query: str, limit: int = 10):
    # searches for albums in the musicbrainz api
    url = "https://musicbrainz.org/ws/2/release"
    params = {
        "query": query,
        "fmt": "json",
        "limit": limit
    }
    headers = {
        "User-Agent": "StereoApp/1.0 (stereo@example.com)"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for release in data.get('releases', []):
            # get cover art with proper fallback
            cover_url = get_cover_art_url(release['id'])
            
            result = AlbumSearchResult(
                mbid=release['id'],
                title=release['title'],
                artist=release['artist-credit'][0]['artist']['name'] if release.get('artist-credit') else "Unknown Artist",
                release_date=release.get('date', 'Unknown'),
                cover_url=cover_url,
                in_database=False
            )
            results.append(result)
        
        return results
    except requests.RequestException as e:
        print(f"Error searching MusicBrainz: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
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
            mbid=None,  # local albums might not have mbid stored
            title=str(album.title),
            artist=str(album.artist),
            release_date=str(album.release_date),
            cover_url=str(album.cover_url),
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

def parse_release_date(date_str: str) -> date:
    # parses various date formats from musicbrainz
    if not date_str or date_str == 'Unknown':
        return date(2020, 1, 1)  # fallback
    
    try:
        # try full date first (YYYY-MM-DD)
        if len(date_str) >= 10:
            return date.fromisoformat(date_str[:10])
        # try year-month (YYYY-MM)
        elif len(date_str) >= 7:
            year, month = date_str[:7].split('-')
            return date(int(year), int(month), 1)
        # try just year (YYYY)
        elif len(date_str) >= 4:
            year = int(date_str[:4])
            return date(year, 1, 1)
    except (ValueError, IndexError):
        pass
    
    return date(2020, 1, 1)  # fallback

@router.post("/add-from-search", response_model=AlbumResponse)
def add_album_from_search(album_data: AlbumSearchResult, db: Session = Depends(get_db)):
    # adds an album to the database from search results
    # check if album already exists
    existing_album = db.query(Album).filter(
        Album.title.ilike(album_data.title),
        Album.artist.ilike(album_data.artist)
    ).first()
    
    if existing_album:
        return existing_album
    
    # parse release date with better handling
    release_date = parse_release_date(album_data.release_date)
    
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

@router.post("/add-by-mbid/{mbid}", response_model=AlbumResponse)
def add_album_by_mbid(mbid: str, db: Session = Depends(get_db)):
    # adds an album to database by musicbrainz id
    try:
        # get album details from musicbrainz
        response = requests.get(
            f"https://musicbrainz.org/ws/2/release/{mbid}",
            params={"fmt": "json"},
            headers={"User-Agent": "StereoApp/1.0 (stereo@example.com)"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # check if album already exists
        existing_album = db.query(Album).filter(
            Album.title.ilike(data['title']),
            Album.artist.ilike(data['artist-credit'][0]['artist']['name'] if data.get('artist-credit') else "Unknown Artist")
        ).first()
        
        if existing_album:
            return existing_album
        
        # create new album
        artist_name = data['artist-credit'][0]['artist']['name'] if data.get('artist-credit') else "Unknown Artist"
        cover_url = get_cover_art_url(mbid)
        release_date = parse_release_date(data.get('date', 'Unknown'))
        
        new_album = Album(
            id=uuid.uuid4(),
            title=data['title'],
            artist=artist_name,
            release_date=release_date,
            cover_url=cover_url
        )
        
        db.add(new_album)
        db.commit()
        db.refresh(new_album)
        
        return new_album
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch album from MusicBrainz: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding album: {str(e)}")