from fastapi import FastAPI
from .database import engine
from . import structs

structs.Base.metadata.create_all(bind=engine)