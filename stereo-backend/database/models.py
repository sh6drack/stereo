import uuid
#uuid is a python library for generating unique identifiers
from datetime import date # date class for date values
from sqlalchemy import Column, String, Integer, Date, ForeignKey, Boolean, UniqueConstraint

from sqlalchemy.dialects.postgresql import UUID #postgresql uuid
from .database import Base

#foreignkeys define relationships between tables

#defining database models

#uuid is a universally unique identifier, used to uniquely identify rows in the database
#primary_key is a unique identifier for each row in the table
#nullable=False means that the column cannot be null, it must have a value

class Album(Base):
    __tablename__ = "albums"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    release_date = Column(Date, nullable=False)
    cover_url = Column(String, nullable=False)
    description = Column(String, nullable=True)  # album description from musicbrainz annotation
    runtime_minutes = Column(Integer, nullable=True)  # total album runtime in minutes
    musicbrainz_id = Column(String, nullable=True)  # musicbrainz release id for api calls


class TrendingAlbum(Base):
    __tablename__ = "trending_albums"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    week_start = Column(Date, nullable=True)

# Each row in TrendingAlbum refers to one row in Album through the album_id foreign key

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)  # Store hashed passwords for zero-knowledge security
    created_at = Column(Date, default=date.today)  # Date when the user was created

class Review(Base): 
    __tablename__ = "reviews"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable = True) #1-10 rating for the album
    review_text = Column(String, nullable=True)  # Text of the review
    created_at = Column(Date, default=date.today)  # Date when the review was created
    updated_at = Column(Date, nullable=True)  # Date when the review was last updated

class Rating(Base):
    __tablename__ = "ratings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-10 rating for the album
    created_at = Column(Date, default=date.today, nullable=False)  # Date when the rating was created
    updated_at = Column(Date, nullable=True)  # Date when the rating was last updated

class List(Base):
    __tablename__ = "lists"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)  
    description = Column(String, nullable=True)  # optional description
    is_public = Column(Boolean, default=True)  # oublic or private list
    is_ranked = Column(Boolean, default=False)  #  (top 10 vs just collection)
    created_at = Column(Date, default=date.today)
    updated_at = Column(Date, nullable=True)

class ListItem(Base):
    __tablename__ = "list_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id = Column(UUID(as_uuid=True), ForeignKey("lists.id"), nullable=False)
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), nullable=False)
    position = Column(Integer, nullable=True)  #  ranked lists (1, 2, 3...), null for unranked
    notes = Column(String, nullable=True)  # Optional note about why this album is on the list
    added_at = Column(Date, default=date.today)

    # Ensure unique album per list (can't add same album twice to one list)
    __table_args__ = (UniqueConstraint('list_id', 'album_id'),)