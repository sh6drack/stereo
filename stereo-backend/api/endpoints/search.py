from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import func, desc

from database.database import get_db
from database.models import Album, User, Rating
from .albums import AlbumResponse
from .users import UserResponse

router = APIRouter(prefix="/search", tags=["search"])
# unified search endpoints for all content types

class SearchFilters(BaseModel):
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    sort_by: Optional[str] = "relevance"  # relevance, rating, date, popularity

class UnifiedSearchResult(BaseModel):
    albums: List[AlbumResponse]
    users: List[UserResponse]
    total_albums: int
    total_users: int

@router.get("/", response_model=UnifiedSearchResult)
def unified_search(
    q: str = Query(..., min_length=2, description="search query"),
    limit: int = Query(10, ge=1, le=50, description="results per category"),
    db: Session = Depends(get_db)
):
    # searches across albums and users
    search_term = q.strip().lower()
    
    # search albums
    album_query = db.query(Album).filter(
        (Album.title.ilike(f"%{search_term}%")) |
        (Album.artist.ilike(f"%{search_term}%"))
    )
    
    albums = album_query.limit(limit).all()
    total_albums = album_query.count()
    
    # search users
    user_query = db.query(User).filter(
        (User.username.ilike(f"%{search_term}%")) |
        (User.email.ilike(f"%{search_term}%"))
    )
    
    users = user_query.limit(limit).all()
    total_users = user_query.count()
    
    return UnifiedSearchResult(
        albums=[AlbumResponse.from_orm(album) for album in albums],
        users=[UserResponse.from_orm(user) for user in users],
        total_albums=total_albums,
        total_users=total_users
    )

@router.get("/albums", response_model=List[AlbumResponse])
def search_albums_advanced(
    q: str = Query(..., min_length=2),
    artist: Optional[str] = Query(None, description="filter by artist"),
    min_rating: Optional[float] = Query(None, ge=0, le=10),
    max_rating: Optional[float] = Query(None, ge=0, le=10),
    year_from: Optional[int] = Query(None, ge=1900),
    year_to: Optional[int] = Query(None, le=2030),
    sort_by: str = Query("relevance", regex="^(relevance|rating|date|popularity)$"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    # advanced album search with filters and sorting
    search_term = q.strip().lower()
    
    # base query
    query = db.query(Album).filter(
        (Album.title.ilike(f"%{search_term}%")) |
        (Album.artist.ilike(f"%{search_term}%"))
    )
    
    # apply filters
    if artist:
        query = query.filter(Album.artist.ilike(f"%{artist.strip()}%"))
    
    if year_from:
        query = query.filter(func.extract('year', Album.release_date) >= year_from)
    
    if year_to:
        query = query.filter(func.extract('year', Album.release_date) <= year_to)
    
    # join with ratings for rating-based filters and sorting
    if min_rating or max_rating or sort_by in ["rating", "popularity"]:
        query = query.outerjoin(Rating, Album.id == Rating.album_id)
        
        if min_rating:
            avg_rating_subq = db.query(
                Rating.album_id,
                func.avg(Rating.rating).label('avg_rating')
            ).group_by(Rating.album_id).subquery()
            
            query = query.join(avg_rating_subq, Album.id == avg_rating_subq.c.album_id)
            query = query.filter(avg_rating_subq.c.avg_rating >= min_rating)
        
        if max_rating:
            avg_rating_subq = db.query(
                Rating.album_id,
                func.avg(Rating.rating).label('avg_rating')
            ).group_by(Rating.album_id).subquery()
            
            query = query.join(avg_rating_subq, Album.id == avg_rating_subq.c.album_id)
            query = query.filter(avg_rating_subq.c.avg_rating <= max_rating)
    
    # apply sorting
    if sort_by == "date":
        query = query.order_by(desc(Album.release_date))
    elif sort_by == "rating":
        query = query.group_by(Album.id).order_by(desc(func.avg(Rating.rating)))
    elif sort_by == "popularity":
        query = query.group_by(Album.id).order_by(desc(func.count(Rating.id)))
    else:  # relevance (default)
        # simple relevance: exact title matches first, then artist matches
        query = query.order_by(
            Album.title.ilike(f"{search_term}%").desc(),
            Album.artist.ilike(f"{search_term}%").desc(),
            Album.title
        )
    
    return query.offset(offset).limit(limit).all()

@router.get("/users", response_model=List[UserResponse])
def search_users(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    # searches for users by username or email
    search_term = q.strip().lower()
    
    users = db.query(User).filter(
        (User.username.ilike(f"%{search_term}%")) |
        (User.email.ilike(f"%{search_term}%"))
    ).order_by(
        User.username.ilike(f"{search_term}%").desc(),
        User.username
    ).offset(offset).limit(limit).all()
    
    return users

@router.get("/suggestions")
def search_suggestions(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    # provides search suggestions for autocomplete
    search_term = q.strip().lower()
    
    # get album suggestions
    album_titles = db.query(Album.title).filter(
        Album.title.ilike(f"{search_term}%")
    ).limit(5).all()
    
    album_artists = db.query(Album.artist).filter(
        Album.artist.ilike(f"{search_term}%")
    ).distinct().limit(5).all()
    
    # get user suggestions
    usernames = db.query(User.username).filter(
        User.username.ilike(f"{search_term}%")
    ).limit(3).all()
    
    return {
        "albums": [title[0] for title in album_titles],
        "artists": [artist[0] for artist in album_artists],
        "users": [username[0] for username in usernames]
    }

@router.get("/trending-searches")
def trending_searches(db: Session = Depends(get_db)):
    # returns popular search terms (mock implementation)
    # in real app, you'd track search queries and return most frequent
    popular_artists = db.query(
        Album.artist,
        func.count(Rating.id).label('rating_count')
    ).outerjoin(Rating, Album.id == Rating.album_id
    ).group_by(Album.artist
    ).order_by(desc('rating_count')
    ).limit(10).all()
    
    return {
        "trending_artists": [artist[0] for artist in popular_artists],
        "trending_albums": [
            "OK Computer",
            "To Pimp a Butterfly", 
            "Blonde",
            "The Dark Side of the Moon",
            "Abbey Road"
        ]
    }