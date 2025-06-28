from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine
from database import models
from api.endpoints import albums, trending, users, reviews, ratings, search, lists

models.Base.metadata.create_all(bind=engine) #bind=engine connects the metadata to the database engine

app = FastAPI()

# enable cors for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(albums.router)
app.include_router(trending.router)
app.include_router(users.router)
app.include_router(reviews.router)
app.include_router(ratings.router)
app.include_router(search.router)
app.include_router(lists.router)