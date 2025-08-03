import os

# Base directory for RSS files
RSS_BASE_DIR = os.path.expanduser("~/rss")

# Path to the directory containing sfeed data files
FEEDS_DIR = os.path.join(RSS_BASE_DIR, "news/feeds")

# Path to the file storing read article URLs
URLS_FILE = os.path.join(RSS_BASE_DIR, "urls")

# Path to the file storing bookmarked article URLs
BOOKMARKS_FILE = os.path.join(RSS_BASE_DIR, "urls-bookmarks-news")

# Path to the file storing starred article URLs
STARRED_FILE = os.path.join(RSS_BASE_DIR, "urls-starred-news")

# Path to the file storing disliked article URLs
DISLIKED_FILE = os.path.join(RSS_BASE_DIR, "urls-disliked-news")

# Path to your sfeedrc file for managing subscriptions
SFEEDRC_FILE = os.path.join(RSS_BASE_DIR, "news/sfeedrc")

# Number of items to show per page in the feed
ITEMS_PER_PAGE = 20