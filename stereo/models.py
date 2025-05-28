import uuid
#uuid is a python library for generating unique identifiers
from datetime import date # date class for date values
from sqlalchemy import Column, String, Integer, Date, ForeignKey

from sqlalchemy.dialects.postgresql import UUID #postgresql uuid
from .database import Base

#foreinkeys define relationships between tables
#defining database models

class Album(Base):
    __tablename__ = "albums"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    release_date = Column(Date, nullable=False)
    cover_art = Column(String, nullable=False)

class trendingAlbum(Base):
    __tablename__ = "trending_albums"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    week_start = Column(Date, nullable=True)

# Each row in TrendingAlbum refers to one row in Album through the album_id foreign key

