from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List as ListType, Optional
from uuid import UUID
import uuid
from datetime import date
from pydantic import BaseModel, Field

from database.database import get_db
from database.models import List, ListItem, Album, User

router = APIRouter(prefix="/lists", tags=["lists"])

class ListCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = True
    is_ranked: bool = False

class ListUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    is_ranked: Optional[bool] = None

class ListItemCreate(BaseModel):
    album_id: UUID
    position: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=300)

class ListItemUpdate(BaseModel):
    position: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=300)

class AlbumSummary(BaseModel):
    id: UUID
    title: str
    artist: str
    cover_url: str

    class Config:
        from_attributes = True

class ListItemResponse(BaseModel):
    id: UUID
    album_id: UUID
    position: Optional[int]
    notes: Optional[str]
    added_at: date
    album: AlbumSummary

    class Config:
        from_attributes = True

class ListResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    is_public: bool
    is_ranked: bool
    created_at: date
    updated_at: Optional[date]
    item_count: Optional[int] = None

    class Config:
        from_attributes = True

class ListDetailResponse(ListResponse):
    items: ListType[ListItemResponse] = []

@router.get("/", response_model=ListType[ListResponse])
def get_lists(
    user_id: Optional[UUID] = None,
    public_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get lists, optionally filtered by user or public visibility"""
    query = db.query(List)
    
    if user_id:
        query = query.filter(List.user_id == user_id)
    
    if public_only:
        query = query.filter(List.is_public == True)
    
    lists = query.order_by(List.created_at.desc()).all()
    
    # Add item count to each list
    for list_obj in lists:
        list_obj.item_count = db.query(ListItem).filter(ListItem.list_id == list_obj.id).count()
    
    return lists

@router.get("/{list_id}", response_model=ListDetailResponse)
def get_list(list_id: UUID, db: Session = Depends(get_db)):
    """Get a specific list with all its items"""
    list_obj = db.query(List).filter(List.id == list_id).first()
    if not list_obj:
        raise HTTPException(status_code=404, detail="List not found")
    
    # Get list items with album details, ordered by position if ranked
    items_query = db.query(ListItem).filter(ListItem.list_id == list_id).join(Album)
    
    if list_obj.is_ranked:
        items_query = items_query.order_by(ListItem.position.nulls_last(), ListItem.added_at)
    else:
        items_query = items_query.order_by(ListItem.added_at.desc())
    
    items = items_query.all()
    
    # Convert to response format
    list_response = ListDetailResponse(
        id=list_obj.id,
        user_id=list_obj.user_id,
        title=list_obj.title,
        description=list_obj.description,
        is_public=list_obj.is_public,
        is_ranked=list_obj.is_ranked,
        created_at=list_obj.created_at,
        updated_at=list_obj.updated_at,
        item_count=len(items),
        items=[
            ListItemResponse(
                id=item.id,
                album_id=item.album_id,
                position=item.position,
                notes=item.notes,
                added_at=item.added_at,
                album=AlbumSummary(
                    id=item.album.id,
                    title=item.album.title,
                    artist=item.album.artist,
                    cover_url=item.album.cover_url
                )
            ) for item in items
        ]
    )
    
    return list_response

@router.post("/", response_model=ListResponse)
def create_list(list_data: ListCreate, user_id: UUID, db: Session = Depends(get_db)):
    """Create a new list"""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_list = List(
        id=uuid.uuid4(),
        user_id=user_id,
        title=list_data.title,
        description=list_data.description,
        is_public=list_data.is_public,
        is_ranked=list_data.is_ranked,
        created_at=date.today()
    )
    
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    
    new_list.item_count = 0
    return new_list

@router.put("/{list_id}", response_model=ListResponse)
def update_list(list_id: UUID, list_data: ListUpdate, user_id: UUID, db: Session = Depends(get_db)):
    """Update a list (only the owner can update)"""
    list_obj = db.query(List).filter(List.id == list_id).first()
    if not list_obj:
        raise HTTPException(status_code=404, detail="List not found")
    
    if list_obj.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only update your own lists")
    
    # Update fields if provided
    if list_data.title is not None:
        setattr(list_obj, 'title', list_data.title)
    if list_data.description is not None:
        setattr(list_obj, 'description', list_data.description)
    if list_data.is_public is not None:
        setattr(list_obj, 'is_public', list_data.is_public)
    if list_data.is_ranked is not None:
        setattr(list_obj, 'is_ranked', list_data.is_ranked)
    
    setattr(list_obj, 'updated_at', date.today())
    
    db.commit()
    db.refresh(list_obj)
    
    list_obj.item_count = db.query(ListItem).filter(ListItem.list_id == list_obj.id).count()
    return list_obj

@router.delete("/{list_id}")
def delete_list(list_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    """Delete a list (only the owner can delete)"""
    list_obj = db.query(List).filter(List.id == list_id).first()
    if not list_obj:
        raise HTTPException(status_code=404, detail="List not found")
    
    if list_obj.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own lists")
    
    # Delete all list items first (cascade)
    db.query(ListItem).filter(ListItem.list_id == list_id).delete()
    
    # Delete the list
    db.delete(list_obj)
    db.commit()
    
    return {"message": "List deleted successfully"}

@router.post("/{list_id}/items", response_model=ListItemResponse)
def add_item_to_list(
    list_id: UUID, 
    item_data: ListItemCreate, 
    user_id: UUID, 
    db: Session = Depends(get_db)
):
    """Add an album to a list"""
    # Check if list exists and user owns it
    list_obj = db.query(List).filter(List.id == list_id).first()
    if not list_obj:
        raise HTTPException(status_code=404, detail="List not found")
    
    if list_obj.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only add items to your own lists")
    
    # Check if album exists
    album = db.query(Album).filter(Album.id == item_data.album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Check if album is already in the list
    existing_item = db.query(ListItem).filter(
        and_(ListItem.list_id == list_id, ListItem.album_id == item_data.album_id)
    ).first()
    if existing_item:
        raise HTTPException(status_code=400, detail="Album is already in this list")
    
    # For ranked lists, auto-assign position if not provided
    position = item_data.position
    if list_obj.is_ranked and position is None:
        max_position = db.query(ListItem.position).filter(ListItem.list_id == list_id).order_by(ListItem.position.desc()).first()
        position = (max_position[0] + 1) if max_position and max_position[0] else 1
    
    new_item = ListItem(
        id=uuid.uuid4(),
        list_id=list_id,
        album_id=item_data.album_id,
        position=position,
        notes=item_data.notes,
        added_at=date.today()
    )
    
    db.add(new_item)
    
    # Update list's updated_at
    setattr(list_obj, 'updated_at', date.today())
    
    db.commit()
    db.refresh(new_item)
    
    return ListItemResponse(
        id=new_item.id,
        album_id=new_item.album_id,
        position=new_item.position,
        notes=new_item.notes,
        added_at=new_item.added_at,
        album=AlbumSummary(
            id=album.id,
            title=album.title,
            artist=album.artist,
            cover_url=album.cover_url
        )
    )

@router.put("/{list_id}/items/{item_id}", response_model=ListItemResponse)
def update_list_item(
    list_id: UUID,
    item_id: UUID,
    item_data: ListItemUpdate,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Update a list item (position, notes)"""
    # Check if list exists and user owns it
    list_obj = db.query(List).filter(List.id == list_id).first()
    if not list_obj:
        raise HTTPException(status_code=404, detail="List not found")
    
    if list_obj.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only update items in your own lists")
    
    # Get the list item
    item = db.query(ListItem).filter(
        and_(ListItem.id == item_id, ListItem.list_id == list_id)
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")
    
    # Update fields if provided
    if item_data.position is not None:
        setattr(item, 'position', item_data.position)
    if item_data.notes is not None:
        setattr(item, 'notes', item_data.notes)
    
    # Update list's updated_at
    setattr(list_obj, 'updated_at', date.today())
    
    db.commit()
    db.refresh(item)
    
    # Get album details for response
    album = db.query(Album).filter(Album.id == item.album_id).first()
    
    return ListItemResponse(
        id=item.id,
        album_id=item.album_id,
        position=item.position,
        notes=item.notes,
        added_at=item.added_at,
        album=AlbumSummary(
            id=album.id,
            title=album.title,
            artist=album.artist,
            cover_url=album.cover_url
        )
    )

@router.delete("/{list_id}/items/{item_id}")
def remove_item_from_list(
    list_id: UUID,
    item_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove an album from a list"""
    # Check if list exists and user owns it
    list_obj = db.query(List).filter(List.id == list_id).first()
    if not list_obj:
        raise HTTPException(status_code=404, detail="List not found")
    
    if list_obj.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only remove items from your own lists")
    
    # Get the list item
    item = db.query(ListItem).filter(
        and_(ListItem.id == item_id, ListItem.list_id == list_id)
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")
    
    db.delete(item)
    
    # Update list's updated_at
    setattr(list_obj, 'updated_at', date.today())
    
    db.commit()
    
    return {"message": "Item removed from list successfully"}

@router.get("/user/{user_id}", response_model=ListType[ListResponse])
def get_user_lists(user_id: UUID, db: Session = Depends(get_db)):
    """Get all public lists for a specific user"""
    lists = db.query(List).filter(
        and_(List.user_id == user_id, List.is_public == True)
    ).order_by(List.created_at.desc()).all()
    
    # Add item count to each list
    for list_obj in lists:
        list_obj.item_count = db.query(ListItem).filter(ListItem.list_id == list_obj.id).count()
    
    return lists