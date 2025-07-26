import os
import re
import csv
import shlex
from datetime import datetime
from .config import FEEDS_DIR, URLS_FILE, BOOKMARKS_FILE, SFEEDRC_FILE

# Increase CSV field size limit to handle large content fields
csv.field_size_limit(1000000)

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
    """Aggregates all items from all feed files with deduplication by URL."""
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

    # Deduplicate by URL, keeping only the most recent entry for each URL
    url_to_item = {}
    for item in all_items:
        url = item['link']
        if url not in url_to_item:
            url_to_item[url] = item
        else:
            # Keep the item with the most recent timestamp
            existing_timestamp = int(url_to_item[url]['timestamp']) if str(url_to_item[url].get('timestamp')).isdigit() else 0
            current_timestamp = int(item['timestamp']) if str(item.get('timestamp')).isdigit() else 0
            if current_timestamp > existing_timestamp:
                url_to_item[url] = item

    # Convert back to list and sort by date descending
    deduplicated_items = list(url_to_item.values())
    deduplicated_items.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0, reverse=True)
    return deduplicated_items

def format_url_for_sfeed_markread(url):
    """Ensures the URL has a trailing newline for the sfeed_markread command."""
    return url if url.endswith('\n') else url + '\n'

def parse_sfeedrc():
    """Parses the sfeedrc file to extract feed information."""
    subscriptions = []
    if not os.path.exists(SFEEDRC_FILE):
        return []

    try:
        with open(SFEEDRC_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # Regex to find lines like: feed 'Channel Name' 'https://...'
            feed_lines = re.findall(r"^\s*feed\s+('.*?'|\".*?\")\s+('.*?'|\".*?\")", content, re.MULTILINE)

            for name_quoted, url_quoted in feed_lines:
                # Use shlex to handle quoted strings properly
                name = shlex.split(name_quoted)[0]
                url = shlex.split(url_quoted)[0]
                subscriptions.append({'name': name, 'url': url})

    except Exception as e:
        print(f"Error parsing sfeedrc file: {e}")

    return subscriptions

def update_sfeedrc(subscriptions):
    """
    Writes a list of subscriptions back to the sfeedrc file,
    preserving the header and footer.
    """
    if not os.path.exists(SFEEDRC_FILE):
        print(f"Error: sfeedrc file not found at {SFEEDRC_FILE}")
        return False

    try:
        with open(SFEEDRC_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find the start and end of the feeds() function
        start_index, end_index = -1, -1
        for i, line in enumerate(lines):
            if line.strip().startswith('feeds()'):
                start_index = i
            elif start_index != -1 and line.strip() == '}':
                end_index = i
                break

        if start_index == -1 or end_index == -1:
            print("Error: Could not find feeds() function in sfeedrc.")
            return False

        header = lines[:start_index + 1]
        footer = lines[end_index:]

        # Create the new feed lines, sorted by name
        sorted_subscriptions = sorted(subscriptions, key=lambda x: x['name'].lower())
        new_feed_lines = []
        for sub in sorted_subscriptions:
            # Escape single quotes in the name for shell safety.
            # ' -> '\''
            escaped_name = sub['name'].replace("'", r"'\''")
            new_feed_lines.append(f"\tfeed '{escaped_name}' '{sub['url']}'\n")


        # Combine everything and write back to the file
        new_content = header + new_feed_lines + footer
        with open(SFEEDRC_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_content)

        return True
    except Exception as e:
        print(f"Error updating sfeedrc file: {e}")
        return False
