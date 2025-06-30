#!/usr/bin/env python3
"""
Smart album import with popularity filtering
Uses multiple signals to determine album relevance/popularity
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import uuid
import requests
import time
from datetime import date, datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

from database.models import Album, Base

load_dotenv()

class PopularityFilteredImporter:
    def __init__(self):
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self.imported_count = 0
        self.target_count = 2000  # Target 2000 quality albums
        self.rejected_count = 0
    
    def get_popularity_score(self, release, artist_releases_count=None):
        """
        Calculate popularity score based on multiple signals
        Returns score 0-100 (higher = more popular/relevant)
        """
        score = 0
        
        # 1. Release status (official albums get higher scores)
        status = release.get('status', '').lower()
        if status == 'official':
            score += 25
        elif status in ['promotion', 'bootleg']:
            score -= 10  # Heavily penalize bootlegs
        
        # 2. Primary type filtering (studio albums prioritized)
        release_group = release.get('release-group', {})
        primary_type = release_group.get('primary-type', '').lower()
        if primary_type == 'album':
            score += 20
        elif primary_type in ['compilation', 'live']:
            score -= 5
        elif primary_type in ['ep', 'single']:
            score += 5  # EPs/singles can be important
        
        # 3. Tag count (more tags = more user engagement)
        tags = release_group.get('tags', [])
        tag_count = len(tags) if tags else 0
        if tag_count > 10:
            score += 15
        elif tag_count > 5:
            score += 10
        elif tag_count > 0:
            score += 5
        
        # 4. Rating existence and quality
        rating = release_group.get('rating', {})
        if rating:
            rating_value = rating.get('value', 0)
            votes_count = rating.get('votes-count', 0)
            
            if votes_count > 50:  # Well-rated albums
                score += 15
                if rating_value >= 4.0:
                    score += 10  # Highly rated
            elif votes_count > 10:
                score += 8
            elif votes_count > 0:
                score += 3
        
        # 5. Artist popularity proxy (if artist has many releases, they're probably notable)
        if artist_releases_count:
            if artist_releases_count > 20:
                score += 10
            elif artist_releases_count > 10:
                score += 5
            elif artist_releases_count > 5:
                score += 2
        
        # 6. Recent popularity (recent albums from established artists)
        release_date = release.get('date', '')
        if release_date:
            try:
                year = int(release_date[:4])
                current_year = datetime.now().year
                
                # Boost recent releases (last 5 years)
                if current_year - year <= 5:
                    score += 8
                # Classic albums (1960-2000) often important
                elif 1960 <= year <= 2000:
                    score += 5
            except (ValueError, IndexError):
                pass
        
        # 7. Country/language filtering (prioritize major markets)
        country = release.get('country', '')
        if country in ['US', 'GB', 'CA', 'AU']:  # English-speaking markets
            score += 5
        elif country in ['DE', 'FR', 'JP', 'NL']:  # Other major markets
            score += 3
        
        # 8. Disambiguation penalty (if needs disambiguation, might be obscure)
        if release.get('disambiguation'):
            score -= 3
        
        return max(0, min(100, score))  # Clamp to 0-100
    
    def search_popular_releases(self, query, max_results=100):
        """Search for releases and filter by popularity"""
        try:
            response = requests.get(
                "https://musicbrainz.org/ws/2/release",
                params={
                    "query": query,
                    "fmt": "json",
                    "limit": max_results,
                    # Include additional data for popularity scoring
                    "inc": "release-groups+tags+ratings"
                },
                headers={"User-Agent": "WaxfeedApp/1.0 (kingpharoah19@gmail.com)"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                releases = data.get('releases', [])
                
                # Score and filter releases
                scored_releases = []
                for release in releases:
                    score = self.get_popularity_score(release)
                    if score >= 30:  # Minimum popularity threshold
                        scored_releases.append((release, score))
                
                # Sort by score (highest first)
                scored_releases.sort(key=lambda x: x[1], reverse=True)
                
                return [release for release, score in scored_releases[:20]]  # Top 20
            
        except Exception as e:
            print(f"❌ Search error for '{query}': {e}")
        
        return []
    
    def get_popular_searches(self):
        """
        Generate search queries targeting popular/relevant albums
        Uses multiple strategies to find notable releases
        """
        searches = []
        
        # 1. Year-based searches for important periods
        important_years = [
            # Classic rock era
            *range(1965, 1980),
            # Alternative/indie golden ages  
            *range(1985, 2000),
            # Modern era
            *range(2000, 2025)
        ]
        
        for year in important_years:
            searches.extend([
                f'date:{year} AND status:official AND type:album',
                f'date:{year} AND status:official AND type:album AND country:US',
                f'date:{year} AND status:official AND type:album AND country:GB'
            ])
        
        # 2. Genre-based searches for popular genres
        popular_genres = [
            'rock', 'pop', 'hip-hop', 'electronic', 'indie', 'alternative',
            'jazz', 'blues', 'country', 'folk', 'metal', 'punk', 'reggae',
            'soul', 'funk', 'r&b', 'classical', 'experimental'
        ]
        
        for genre in popular_genres:
            searches.extend([
                f'tag:{genre} AND status:official AND type:album',
                f'tag:{genre} AND status:official AND type:album AND date:[2000-01-01 TO 2024-12-31]'
            ])
        
        # 3. Label-based searches (major labels = popular releases)
        major_labels = [
            'Columbia', 'Atlantic', 'Capitol', 'Warner', 'Universal',
            'EMI', 'Sony', 'RCA', 'Def Jam', 'Interscope', 'Virgin',
            'Island', 'Elektra', 'Geffen', 'Parlophone'
        ]
        
        for label in major_labels:
            searches.append(f'label:{label} AND status:official AND type:album')
        
        # 4. Country-based searches (major music markets)
        major_markets = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP']
        for country in major_markets:
            searches.extend([
                f'country:{country} AND status:official AND type:album AND date:[1960-01-01 TO 2024-12-31]'
            ])
        
        return searches
    
    def should_import_release(self, release):
        """Final filter before import"""
        # Check if already exists
        mbid = release.get('id')
        if mbid:
            existing = self.session.query(Album).filter(Album.musicbrainz_id == mbid).first()
            if existing:
                return False
        
        # Basic quality checks
        title = release.get('title', '').strip()
        if not title or len(title) < 2:
            return False
            
        artist_credit = release.get('artist-credit', [])
        if not artist_credit:
            return False
            
        # Skip various artists compilations
        artist_name = artist_credit[0].get('artist', {}).get('name', '').lower()
        if 'various' in artist_name or len(artist_name) < 2:
            return False
        
        # Calculate final popularity score
        score = self.get_popularity_score(release)
        return score >= 35  # Higher threshold for final import
    
    def import_release(self, release):
        """Import a release to database"""
        try:
            mbid = release['id']
            title = release['title']
            artist_name = release['artist-credit'][0]['artist']['name']
            
            # Get additional metadata
            cover_url = self.get_cover_art_url(mbid)
            release_date = self.parse_release_date(release.get('date', ''))
            
            # Create album
            album = Album(
                id=uuid.uuid4(),
                title=title,
                artist=artist_name,
                release_date=release_date,
                cover_url=cover_url,
                musicbrainz_id=mbid
            )
            
            self.session.add(album)
            self.imported_count += 1
            
            score = self.get_popularity_score(release)
            print(f"✅ {self.imported_count:4d}/{self.target_count} [score:{score:2d}] {artist_name} - {title}")
            
            # Commit every 50 albums
            if self.imported_count % 50 == 0:
                self.session.commit()
                print(f"💾 Committed batch ({self.imported_count}/{self.target_count})")
                print(f"📊 Progress: {(self.imported_count/self.target_count)*100:.1f}% | Rejected: {self.rejected_count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error importing {release.get('title', 'Unknown')}: {e}")
            return False
    
    def get_cover_art_url(self, mbid):
        """Get cover art from Cover Art Archive"""
        try:
            response = requests.get(
                f"https://coverartarchive.org/release/{mbid}",
                headers={"User-Agent": "WaxfeedApp/1.0 (kingpharoah19@gmail.com)"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                images = data.get('images', [])
                
                for image in images:
                    if image.get('front', False):
                        return image['image']
                
                if images:
                    return images[0]['image']
                    
        except Exception:
            pass
            
        return "https://via.placeholder.com/500x500?text=No+Cover+Art"
    
    def parse_release_date(self, date_str):
        """Parse MusicBrainz date format"""
        if not date_str:
            return date(2000, 1, 1)
            
        try:
            if len(date_str) >= 10:
                return date.fromisoformat(date_str[:10])
            elif len(date_str) >= 7:
                year, month = date_str[:7].split('-')
                return date(int(year), int(month), 1)
            elif len(date_str) >= 4:
                return date(int(date_str[:4]), 1, 1)
        except (ValueError, IndexError):
            pass
            
        return date(2000, 1, 1)
    
    def run_import(self):
        """Main import process"""
        try:
            print(f"🚀 Starting popularity-filtered import (target: {self.target_count} albums)")
            
            searches = self.get_popular_searches()
            total_searches = len(searches)
            print(f"📦 Generated {total_searches} search queries")
            
            for i, query in enumerate(searches):
                if self.imported_count >= self.target_count:
                    break
                
                print(f"\n🔍 [{i+1}/{total_searches}] {query[:60]}...")
                
                releases = self.search_popular_releases(query, max_results=50)
                
                for release in releases:
                    if self.imported_count >= self.target_count:
                        break
                        
                    if self.should_import_release(release):
                        self.import_release(release)
                    else:
                        self.rejected_count += 1
                
                # Rate limiting
                time.sleep(1.5)
            
            # Final commit
            self.session.commit()
            
            print(f"\n🎉 Import complete!")
            print(f"✅ Imported: {self.imported_count} albums")
            print(f"❌ Rejected: {self.rejected_count}")
            print(f"📈 Accept rate: {(self.imported_count/(self.imported_count+self.rejected_count)*100):.1f}%")
            
            if self.imported_count >= 2000:
                print("🎯 Database ready for production!")
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            self.session.rollback()
            raise
        finally:
            self.session.close()

if __name__ == "__main__":
    importer = PopularityFilteredImporter()
    importer.run_import()