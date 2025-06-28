# manual seeding for testing

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import uuid
import requests
import time
from datetime import date
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

from database.models import Album, TrendingAlbum, Rating, Review, Base

load_dotenv()

# get database url and create engine
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

# creates all tables in the database based on the models
Base.metadata.create_all(bind=engine)

# create session for database operations
Session = sessionmaker(bind=engine)
session = Session()

def get_cover_art_url(mbid: str) -> str:
    # gets cover art from cover art archive with fallback
    try:
        cover_response = requests.get(
            f"https://coverartarchive.org/release/{mbid}",
            headers={"User-Agent": "WaxfeedApp/1.0 (kingpharoah19@gmail.com)"},
            timeout=5
        )
        if cover_response.status_code == 200:
            cover_data = cover_response.json()
            if cover_data.get('images'):
                for image in cover_data['images']:
                    if image.get('front', False):
                        return image['image']
                return cover_data['images'][0]['image']
    except Exception:
        pass
    return "https://via.placeholder.com/500x500?text=No+Cover+Art"

def get_album_annotation(mbid: str) -> str:
    # gets album description from musicbrainz annotation
    try:
        annotation_response = requests.get(
            f"https://musicbrainz.org/ws/2/release/{mbid}",
            params={"inc": "annotation", "fmt": "json"},
            headers={"User-Agent": "WaxfeedApp/1.0 (kingpharoah19@gmail.com)"},
            timeout=5
        )
        if annotation_response.status_code == 200:
            annotation_data = annotation_response.json()
            return annotation_data.get('annotation', '')
    except Exception:
        pass
    return ''

def get_album_runtime(mbid: str) -> int | None:
    # gets total album runtime in minutes from recordings
    try:
        recordings_response = requests.get(
            f"https://musicbrainz.org/ws/2/release/{mbid}",
            params={"inc": "recordings", "fmt": "json"},
            headers={"User-Agent": "WaxfeedApp/1.0 (kingpharoah19@gmail.com)"},
            timeout=10
        )
        if recordings_response.status_code == 200:
            data = recordings_response.json()
            total_ms = 0
            if 'media' in data:
                for medium in data['media']:
                    if 'tracks' in medium:
                        for track in medium['tracks']:
                            if 'recording' in track and 'length' in track['recording']:
                                total_ms += int(track['recording']['length'])
            return total_ms // 60000  # convert ms to minutes
    except Exception:
        pass
    return None

def parse_release_date(date_str: str) -> date:
    # parses various date formats
    if not date_str or date_str == 'Unknown':
        return date(2020, 1, 1)
    
    try:
        if len(date_str) >= 10:
            return date.fromisoformat(date_str[:10])
        elif len(date_str) >= 7:
            year, month = date_str[:7].split('-')
            return date(int(year), int(month), 1)
        elif len(date_str) >= 4:
            year = int(date_str[:4])
            return date(year, 1, 1)
    except (ValueError, IndexError):
        pass
    
    return date(2020, 1, 1)

def seed_popular_albums():
    # seeds database with some popular albums for testing
    popular_albums = [
        # classic rock/pop
        "The Dark Side of the Moon Pink Floyd",
        "Abbey Road The Beatles",
        "Led Zeppelin IV Led Zeppelin",
        "Rumours Fleetwood Mac",
        "Hotel California Eagles",
        
        # modern albums
        "OK Computer Radiohead",
        "The College Dropout Kanye West",
        "Blonde Frank Ocean",
        "To Pimp a Butterfly Kendrick Lamar",
        "Melodrama Lorde",
        
        # hip-hop classics
        "Illmatic Nas",
        "The Chronic Dr. Dre",
        "Enter the Wu-Tang Clan Wu-Tang Clan",
        
        # indie/alternative
        "In the Aeroplane Over the Sea Neutral Milk Hotel",
        "Funeral Arcade Fire",
    ]
    
    added_count = 0
    for query in popular_albums:
        try:
            # search musicbrainz for the album
            response = requests.get(
                "https://musicbrainz.org/ws/2/release",
                params={"query": query, "fmt": "json", "limit": 1},
                headers={"User-Agent": "WaxfeedApp/1.0 (kingpharoah19@gmail.com)"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                releases = data.get('releases', [])
                
                if releases:
                    release = releases[0]
                    
                    # check if album already exists
                    existing = session.query(Album).filter(
                        Album.title.ilike(release['title']),
                        Album.artist.ilike(release['artist-credit'][0]['artist']['name'] if release.get('artist-credit') else "Unknown")
                    ).first()
                    
                    if not existing:
                        artist_name = release['artist-credit'][0]['artist']['name'] if release.get('artist-credit') else "Unknown Artist"
                        cover_url = get_cover_art_url(release['id'])
                        release_date = parse_release_date(release.get('date', 'Unknown'))
                        description = get_album_annotation(release['id'])
                        runtime = get_album_runtime(release['id'])
                        
                        album = Album(
                            id=uuid.uuid4(),
                            title=release['title'],
                            artist=artist_name,
                            release_date=release_date,
                            cover_url=cover_url,
                            description=description,
                            runtime_minutes=runtime,
                            musicbrainz_id=release['id']
                        )
                        
                        session.add(album)
                        added_count += 1
                        print(f"Added: {artist_name} - {release['title']}")
                    else:
                        print(f"Already exists: {existing.artist} - {existing.title}")
            
            # be nice to musicbrainz api
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing '{query}': {e}")
            continue
    
    session.commit()
    print(f"\nSeeding complete! Added {added_count} new albums.")

def seed_trending_albums():
    # creates some trending album entries for the current week
    albums = session.query(Album).limit(25).all()
    
    if len(albums) < 10:
        print("Not enough albums in database for trending. Run album seeding first.")
        return
    
    # clear existing trending
    session.query(TrendingAlbum).delete()
    
    # add current albums as trending
    for i, album in enumerate(albums[:25]):
        trending = TrendingAlbum(
            id=uuid.uuid4(),
            album_id=album.id,
            rank=i + 1,
            week_start=date.today()
        )
        session.add(trending)
    
    session.commit()
    print(f"Added {len(albums[:25])} trending albums for this week.")

if __name__ == "__main__":
    print("Starting database seeding...")
    
    try:
        # seed popular albums first
        print("\n1. Seeding popular albums...")
        seed_popular_albums()
        
        # then create trending entries
        print("\n2. Creating trending albums...")
        seed_trending_albums()
        
        print("\nDatabase seeding completed successfully!")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        session.rollback()
    
    finally:
        session.close()