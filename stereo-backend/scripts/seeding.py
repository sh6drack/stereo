# we are using musicbrainz for seeding album data
# and cover art archive for cover art images

import uuid
import requests
import time
from datetime import date
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

from database.models import Album, TrendingAlbum, Rating, Review, Base

load_dotenv()

Base.metadata.create_all(bind=engine)
#^ creates all tables in the database based on the models defined in database/models.py