#!/usr/bin/env python3
"""
temporary script to add test ratings for albums to see average ratings in UI
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import uuid
import random
from database.database import get_db
from database.models import Album, Rating, User

def add_test_ratings():
    """add random test ratings to existing albums"""
    db = next(get_db())
    try:
        # get all albums
        albums = db.query(Album).all()
        if not albums:
            print("❌ no albums found. run seeding script first.")
            return
        
        # create a test user if none exists
        test_user = db.query(User).first()
        if not test_user:
            test_user = User(
                id=uuid.uuid4(),
                username="testuser",
                email="test@waxfeed.com",
                password_hash="dummy_hash",
            )
            db.add(test_user)
            db.commit()
            print("✨ created test user")
        
        # add 3-5 random ratings per album
        for album in albums:
            num_ratings = random.randint(3, 5)
            
            for i in range(num_ratings):
                # create fake user for each rating
                fake_user = User(
                    id=uuid.uuid4(),
                    username=f"user_{album.id}_{i}",
                    email=f"user_{album.id}_{i}@test.com",
                    password_hash="dummy_hash"
                )
                db.add(fake_user)
                db.flush()  # get the user id
                
                # add rating (bias towards 7-9 for realistic data)
                rating_value = random.choices(
                    range(1, 11),
                    weights=[1, 1, 2, 3, 5, 8, 10, 12, 8, 5]  # bell curve around 7-8
                )[0]
                
                rating = Rating(
                    id=uuid.uuid4(),
                    album_id=album.id,
                    user_id=fake_user.id,
                    rating=rating_value
                )
                db.add(rating)
            
            db.commit()
            print(f"📊 added {num_ratings} ratings to: {album.title}")
        
        print(f"\n🎯 added test ratings to {len(albums)} albums!")
        
    except Exception as e:
        print(f"❌ error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🧪 adding test ratings...")
    add_test_ratings()
    print("✅ done! restart backend to see average ratings")