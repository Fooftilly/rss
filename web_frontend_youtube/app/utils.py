import os
import re
import csv
from datetime import datetime
from .config import FEEDS_DIR, URLS_FILE, BOOKMARKS_FILE

# In-memory cache to avoid re-reading files that haven't changed
_cache = {
    'feeds': {},  # {filename: (mtime, items)}
    'bookmarks': {'mtime': None, 'data': set()},
    'watched': {'mtime': None, 'data': set()}
}

def extract_youtube_id(url):
    """Extracts the YouTube video ID from various URL formats."""
    if not url:
        return None
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([^&\n?#]+)',
        r'youtube\.com/v/([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_thumbnail(video_id):
    """Generates a YouTube thumbnail URL from a video ID."""
    if not video_id:
        return None
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

def read_urls_file(file_path):
    """Generic function to read a file of URLs into a set, with caching."""
    cache_key = os.path.basename(file_path)
    if not os.path.exists(file_path):
        return set()

    mtime = os.path.getmtime(file_path)
    if _cache.get(cache_key) and _cache[cache_key]['mtime'] == mtime:
        return _cache[cache_key]['data']

    with open(file_path, 'r', encoding='utf-8') as f:
        data = set(line.strip() for line in f if line.strip())

    _cache[cache_key] = {'mtime': mtime, 'data': data}
    return data

def parse_feed_file(filepath):
    """Parses a single sfeed data file."""
    if not os.path.exists(filepath):
        print(f"Error: Feed file does not exist: {filepath}")
        return []

    mtime = os.path.getmtime(filepath)
    if _cache['feeds'].get(filepath) and _cache['feeds'][filepath][0] == mtime:
        return _cache['feeds'][filepath][1]

    items = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                if len(row) < 8:
                    continue  # Skip malformed rows

                timestamp, title, link, content, _, _, author, _ = row[:8]
                video_id = extract_youtube_id(link)

                if not all([title, link, author, video_id]):
                    continue # Skip if essential data is missing

                try:
                    dt = datetime.fromtimestamp(int(timestamp))
                    formatted_date = dt.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    formatted_date = "Unknown date"

                items.append({
                    'timestamp': timestamp,
                    'title': title.strip(),
                    'link': link.strip(),
                    'content': content,
                    'author': author.strip(),
                    'date': formatted_date,
                    'feed_name': os.path.basename(filepath),
                    'video_id': video_id,
                    'thumbnail_url': get_youtube_thumbnail(video_id)
                })
    except Exception as e:
        print(f"Error parsing feed file {filepath}: {e}")
        return []

    _cache['feeds'][filepath] = (mtime, items)
    return items

def get_all_feeds():
    """Aggregates all items from all feed files."""
    all_items = []
    watched_urls = read_urls_file(URLS_FILE)
    bookmarked_urls = read_urls_file(BOOKMARKS_FILE)

    if not os.path.exists(FEEDS_DIR):
        print(f"Warning: Feeds directory does not exist: {FEEDS_DIR}")
        return []

    try:
        for filename in os.listdir(FEEDS_DIR):
            filepath = os.path.join(FEEDS_DIR, filename)
            if not os.path.isfile(filepath):
                continue

            items = parse_feed_file(filepath)
            for item in items:
                item['watched'] = item['link'] in watched_urls
                item['bookmarked'] = item['link'] in bookmarked_urls
            all_items.extend(items)
    except Exception as e:
        print(f"Critical error reading feeds directory: {e}")

    # Default sort by date descending. The API endpoint will handle other sort orders.
    all_items.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0, reverse=True)
    return all_items

def format_url_for_sfeed_markread(url):
    """Ensures the URL has a trailing newline for the sfeed_markread command."""
    return url if url.endswith('\n') else url + '\n'

