import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from . import models

# Load environment variables from .env file
load_dotenv()

# Database URL from environment variable ; create connection to database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

# create a session(how to interact with the database)
LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# create a base class for the database models
Base = declarative_base()

# function to get a database session
def get_db():
    db = LocalSession()
    try:
        yield db # will provide a session to the caller
    finally: #always executes 
        db.close()

# create all tables in the database
# bind means to connect the models to the database