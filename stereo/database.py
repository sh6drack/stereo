import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from .database import engine
from . import models

# Load environment variables from .env file
load_dotenv()

# Database URL from environment variable ; create connection to database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

# create a session(how to interact with the database)
sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# create a base class for the database models
Base = declarative_base()

# function to get a database session
def get_dbs():
    dbs = sessionmaker
    try:
        yield dbs # will provide a session to the caller
    finally: #always executes 
        dbs.close()

# create all tables in the database
models.Base.metadata.create_all(bind=engine)
# bind means to connect the models to the database