# Stereo Backend API

FastAPI-based music rating and review platform with MusicBrainz integration.

## Quick Start
```bash
cd stereo-backend
source ../stereo-env/bin/activate
uvicorn main:app --reload --port 8000
```
Visit http://127.0.0.1:8000/docs for interactive API documentation.

## API Endpoints

### Albums (`/albums`)
- `GET /{album_id}` - Retrieve specific album
- `POST /` - Create new album
- `GET /{album_id}/reviews` - Get album reviews
- `GET /{album_id}/average-rating` - Get album average rating
- `GET /search` - Search albums (local + MusicBrainz)
- `POST /add-from-search` - Add album from search results
- `POST /add-by-mbid/{mbid}` - Add album by MusicBrainz ID

### Trending (`/trending`)
- `GET /` - Get top 25 trending albums
- `POST /` - Create trending album entry

### Users (`/users`)
- `POST /register` - Register new user
- `POST /login` - User authentication
- `GET /profile/{user_id}` - Get user profile

### Reviews (`/reviews`)
- `GET /{album_id}` - Get reviews for album
- `POST /` - Create new review
- `PUT /{review_id}` - Update review
- `DELETE /{review_id}` - Delete review

### Ratings (`/ratings`)
- `GET /{album_id}` - Get ratings for album
- `POST /` - Create new rating
- `PUT /{rating_id}` - Update rating
- `POST /albums/{album_id}/rate` - Quick rate album (1-10)

### Search (`/search`)
- `GET /` - Unified search (albums + users)
- `GET /albums` - Advanced album search with filters
- `GET /users` - Search users
- `GET /suggestions` - Autocomplete suggestions
- `GET /trending-searches` - Popular search terms