

## Quick Start
```bash
cd waxfeed-backend
source ../waxfeed-env/bin/activate
uvicorn main:app --reload --port 8000
```
# Waxfeed Backend API
FastAPI-based music rating and review platform with MusicBrainz integration.

### Albums (`/albums`)
- `GET /{album_id}` - retrieve specific album
- `POST /` - create new album
- `GET /{album_id}/reviews` - get album reviews
- `GET /{album_id}/average-rating` - get album average rating
- `GET /search` - search albums (local + musicbrainz)
- `POST /add-from-search` - add album from search results
- `POST /add-by-mbid/{mbid}` - add album by musicbrainz id

### Trending (`/trending`)
- `GET /` - get top 25 trending albums
- `POST /` - create trending album entry

### Users (`/users`)
- `POST /register` - register new user
- `POST /login` - user authentication
- `GET /profile/{user_id}` - get user profile

### Reviews (`/reviews`)
- `GET /{album_id}` - get reviews for album
- `POST /` - create new review
- `PUT /{review_id}` - update review
- `DELETE /{review_id}` - delete review

### Ratings (`/ratings`)
- `GET /{album_id}` - get ratings for album
- `POST /` - create new rating
- `PUT /{rating_id}` - update rating
- `POST /albums/{album_id}/rate` - quick rate album (1-10)

### Search (`/search`)
- `GET /` - unified search (albums + users)
- `GET /albums` - advanced album search with filters
- `GET /users` - search users
- `GET /suggestions` - autocomplete suggestions
- `GET /trending-searches` - popular search terms