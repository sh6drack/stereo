import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# loads environment variables from .env file
load_dotenv()

# gets db url from env variables and creates connection to database
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

# creates session factory for database interactions
LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# base class for all database models
Base = declarative_base()

# dependency function to get database session
def get_db():
    db = LocalSession()
    try:
        yield db  # provides session to caller
    finally:  # always executes to clean up
        db.close()