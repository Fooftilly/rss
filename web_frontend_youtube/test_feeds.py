#!/usr/bin/env python3

"""
Simple test script to verify the YouTube feed reader is working correctly.
"""

import os
import sys
sys.path.append('.')

from app.utils import get_all_feeds
from app.config import FEEDS_DIR, URLS_FILE, BOOKMARKS_FILE

def test_feeds():
    print("Testing YouTube Feed Reader...")
    print(f"Feeds directory: {FEEDS_DIR}")
    print(f"URLs file: {URLS_FILE}")
    print(f"Bookmarks file: {BOOKMARKS_FILE}")
    print()
    
    # Check if directories exist
    if not os.path.exists(FEEDS_DIR):
        print(f"❌ Feeds directory does not exist: {FEEDS_DIR}")
        return False
    
    print(f"✅ Feeds directory exists")
    
    # List feed files
    feed_files = [f for f in os.listdir(FEEDS_DIR) if os.path.isfile(os.path.join(FEEDS_DIR, f))]
    print(f"📁 Found {len(feed_files)} feed files")
    
    if len(feed_files) == 0:
        print("⚠️  No feed files found. Make sure sfeed has generated some YouTube feeds.")
        return True
    
    # Test loading feeds
    try:
        videos = get_all_feeds()
        print(f"🎥 Loaded {len(videos)} videos")
        
        if len(videos) > 0:
            # Show sample video
            sample = videos[0]
            print("\n📺 Sample video:")
            print(f"   Title: {sample['title'][:80]}...")
            print(f"   Channel: {sample['author']}")
            print(f"   Date: {sample['date']}")
            print(f"   Video ID: {sample['video_id']}")
            print(f"   Watched: {sample['watched']}")
            print(f"   Bookmarked: {sample['bookmarked']}")
            
            # Count by status
            unwatched = len([v for v in videos if not v['watched']])
            watched = len([v for v in videos if v['watched']])
            bookmarked = len([v for v in videos if v['bookmarked']])
            
            print(f"\n📊 Statistics:")
            print(f"   Unwatched: {unwatched}")
            print(f"   Watched: {watched}")
            print(f"   Bookmarked: {bookmarked}")
            
        print("\n✅ Feed loading test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading feeds: {e}")
        return False

if __name__ == "__main__":
    success = test_feeds()
    if success:
        print("\n🎉 All tests passed! The YouTube feed reader should work correctly.")
        print("Run 'python run.py' to start the web server.")
    else:
        print("\n💥 Some tests failed. Please check your sfeed configuration.")
        sys.exit(1)