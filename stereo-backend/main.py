from fastapi import FastAPI
from database.database import engine
from database import models
from api.endpoints import albums, trending, users, reviews, ratings, search

models.Base.metadata.create_all(bind=engine) #bind=engine connects the metadata to the database engine

app = FastAPI()

app.include_router(albums.router)
app.include_router(trending.router)
app.include_router(users.router)
app.include_router(reviews.router)
app.include_router(ratings.router)
app.include_router(search.router)