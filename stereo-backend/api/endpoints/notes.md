albums.py:

GET /albums/{id} - get one album
POST /albums - create new album
GET /albums/{id}/reviews - get album's reviews
GET /albums/{id}/average-rating - get album's average rating

trending.py:

GET /trending - get trending list
POST /trending - update trending rankings

users.py (for later):

POST /auth/register - create account
POST /auth/login - login
GET /users/me - get current user

reviews.py (for later):

POST /albums/{id}/reviews - add review
PUT /reviews/{id} - update review
DELETE /reviews/{id} - delete review