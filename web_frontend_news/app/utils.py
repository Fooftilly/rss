import os
import re
import hashlib
from datetime import datetime
from .config import FEEDS_DIR, URLS_FILE, BOOKMARKS_FILE, STARRED_FILE, DISLIKED_FILE

# In-memory cache to avoid re-reading files that haven't changed
_cache = {
    'feeds': {},  # {filename: (mtime, articles)}
    'urls': {'mtime': None, 'data': set()},  # Main URLs file (shared)
    'bookmarked_urls': {'mtime': None, 'data': set()},
    'starred_urls': {'mtime': None, 'data': set()},
    'disliked_urls': {'mtime': None, 'data': set()}
}

def read_urls_file_cached(file_path, cache_key):
    """Read a URLs file with caching to improve performance"""
    if not os.path.exists(file_path):
        return set()
    
    try:
        mtime = os.path.getmtime(file_path)
        if _cache[cache_key]['mtime'] == mtime and _cache[cache_key]['data'] is not None:
            return _cache[cache_key]['data']
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = set(line.strip() for line in f if line.strip() and not line.startswith('#'))
        
        _cache[cache_key] = {'mtime': mtime, 'data': data}
        return data
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return set()

def get_all_feeds():
    """
    Parse all sfeed files in the feeds directory and return a list of articles.
    Uses caching to improve performance by avoiding re-reading unchanged files.
    """
    if not os.path.exists(FEEDS_DIR):
        return []
    
    # Load URL sets with caching
    read_urls = read_urls_file_cached(URLS_FILE, 'urls')
    bookmarked_urls = read_urls_file_cached(BOOKMARKS_FILE, 'bookmarked_urls')
    starred_urls = read_urls_file_cached(STARRED_FILE, 'starred_urls')
    disliked_urls = read_urls_file_cached(DISLIKED_FILE, 'disliked_urls')
    
    articles = []
    
    # Process each feed file with caching
    try:
        feed_files = os.listdir(FEEDS_DIR)
    except OSError:
        return articles
    
    for filename in feed_files:
        filepath = os.path.join(FEEDS_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        
        try:
            # Check cache first
            mtime = os.path.getmtime(filepath)
            if filename in _cache['feeds']:
                cached_mtime, cached_articles = _cache['feeds'][filename]
                if cached_mtime == mtime:
                    # Use cached articles but update status flags
                    for article in cached_articles:
                        article['read'] = article['url'] in read_urls
                        article['bookmarked'] = article['url'] in bookmarked_urls
                        article['starred'] = article['url'] in starred_urls
                        article['disliked'] = article['url'] in disliked_urls
                    articles.extend(cached_articles)
                    continue
            
            # Read and parse the file
            file_articles = []
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse sfeed format: timestamp\ttitle\turl\tcontent\tauthor_html\tid\tactual_author
                    parts = line.split('\t')
                    if len(parts) >= 5:
                        timestamp_str = parts[0]
                        title = parts[1]
                        url = parts[2]
                        content = parts[3]
                        # Use actual author from field 6 if available, otherwise fall back to field 4
                        author = parts[6] if len(parts) > 6 and parts[6].strip() else (parts[4] if parts[4] != 'html' else 'Unknown')
                        
                        # Generate article ID from URL
                        article_id = hashlib.md5(url.encode()).hexdigest()
                        
                        # Create article dictionary
                        article = {
                            'title': title,
                            'url': url,
                            'timestamp': timestamp_str,
                            'author': author,
                            'content': content,
                            'read': url in read_urls,
                            'bookmarked': url in bookmarked_urls,
                            'starred': url in starred_urls,
                            'disliked': url in disliked_urls,
                            'article_id': article_id,
                            'source': filename  # Feed source file
                        }
                        
                        file_articles.append(article)
            
            # Cache the parsed articles
            _cache['feeds'][filename] = (mtime, file_articles)
            articles.extend(file_articles)
            
        except Exception as e:
            print(f"Error reading feed file {filename}: {e}")
            continue
    
    return articles

def format_url_for_sfeed_markread(url):
    """
    Format a URL for use with sfeed_markread.
    sfeed_markread expects URLs with newlines.
    """
    return url.strip() + '\n'

def parse_sfeedrc():
    """
    Parse the sfeedrc file to extract current subscriptions.
    Returns a list of dictionaries with 'name' and 'url' keys.
    """
    from .config import SFEEDRC_FILE
    
    subscriptions = []
    
    if not os.path.exists(SFEEDRC_FILE):
        return subscriptions
    
    try:
        with open(SFEEDRC_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract feed lines using regex
        # Looking for: feed "Name" "URL"
        feed_pattern = r'feed\s+"([^"]+)"\s+"([^"]+)"'
        matches = re.findall(feed_pattern, content)
        
        for name, url in matches:
            subscriptions.append({
                'name': name,
                'url': url
            })
    
    except Exception as e:
        print(f"Error parsing sfeedrc: {e}")
    
    return subscriptions

def update_sfeedrc(subscriptions):
    """
    Update the sfeedrc file with new subscriptions.
    subscriptions should be a list of dictionaries with 'name' and 'url' keys.
    """
    from .config import SFEEDRC_FILE
    
    try:
        # Read the current sfeedrc file to preserve non-feed content
        existing_content = ""
        if os.path.exists(SFEEDRC_FILE):
            with open(SFEEDRC_FILE, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        
        # Remove existing feed lines
        lines = existing_content.split('\n')
        non_feed_lines = []
        in_feeds_function = False
        
        for line in lines:
            stripped = line.strip()
            
            # Track if we're inside the feeds() function
            if stripped.startswith('feeds()'):
                in_feeds_function = True
                non_feed_lines.append(line)
                continue
            elif in_feeds_function and stripped == '}':
                in_feeds_function = False
                # Add new feed lines before the closing brace
                for sub in subscriptions:
                    feed_line = f'\tfeed "{sub["name"]}" "{sub["url"]}"'
                    non_feed_lines.append(feed_line)
                non_feed_lines.append(line)
                continue
            elif in_feeds_function and stripped.startswith('feed '):
                # Skip existing feed lines
                continue
            
            non_feed_lines.append(line)
        
        # If no feeds() function exists, create a basic one
        if not any('feeds()' in line for line in non_feed_lines):
            non_feed_lines.extend([
                '',
                '# list of feeds to fetch:',
                'feeds() {',
                '\t# feed <name> <feedurl>',
            ])
            for sub in subscriptions:
                feed_line = f'\tfeed "{sub["name"]}" "{sub["url"]}"'
                non_feed_lines.append(feed_line)
            non_feed_lines.append('}')
        
        # Write the updated content
        with open(SFEEDRC_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(non_feed_lines))
        
        return True
    
    except Exception as e:
        print(f"Error updating sfeedrc: {e}")
        return False

def extract_article_preview(content, max_length=200):
    """
    Extract a preview from article content (optimized version).
    """
    if not content:
        return ""
    
    # Quick check - if content is short and has no HTML, return as-is
    if len(content) <= max_length and '<' not in content:
        return content
    
    # Remove HTML tags if present (optimized regex)
    if '<' in content:
        clean_content = re.sub(r'<[^>]*>', '', content)
    else:
        clean_content = content
    
    # Truncate to max length
    if len(clean_content) <= max_length:
        return clean_content
    
    # Find a good breaking point (optimized)
    truncated = clean_content[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # If we can break at a word boundary
        return truncated[:last_space] + "..."
    
    return truncated + "..."

def format_timestamp(timestamp_str):
    """
    Format timestamp for display.
    """
    try:
        timestamp = int(timestamp_str)
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return timestamp_str

def invalidate_cache():
    """
    Invalidate all caches to force fresh data loading.
    Call this after updating URL files.
    """
    global _cache
    _cache = {
        'feeds': {},
        'urls': {'mtime': None, 'data': set()},  # Main URLs file (shared)
        'bookmarked_urls': {'mtime': None, 'data': set()},
        'starred_urls': {'mtime': None, 'data': set()},
        'disliked_urls': {'mtime': None, 'data': set()}
    }