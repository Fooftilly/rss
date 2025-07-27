import os

# Base directory for RSS files
RSS_BASE_DIR = os.path.expanduser("~/rss")

# Path to the directory containing sfeed data files
FEEDS_DIR = os.path.join(RSS_BASE_DIR, "youtube/feeds")

# Path to the file storing watched video URLs
URLS_FILE = os.path.join(RSS_BASE_DIR, "urls-youtube")

# Path to the file storing bookmarked video URLs
BOOKMARKS_FILE = os.path.join(RSS_BASE_DIR, "urls-bookmarks-youtube")

# Path to the file storing starred video URLs
STARRED_FILE = os.path.join(RSS_BASE_DIR, "urls-starred-youtube")

# Path to your sfeedrc file for managing subscriptions
SFEEDRC_FILE = os.path.join(RSS_BASE_DIR, "youtube/sfeedrc")

# Number of items to show per page in the feed
ITEMS_PER_PAGE = 20
