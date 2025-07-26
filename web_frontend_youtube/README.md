# YouTube Feed Reader - Web Frontend for sfeed

A modern web interface for watching YouTube videos from RSS feeds using sfeed.

## Features

- **Clean, responsive interface** - Works on desktop and mobile
- **Multiple views** - Unwatched, Watched, Bookmarked, and All videos
- **Search functionality** - Search through titles, channels, and content
- **Sorting options** - Sort by date, title, or channel
- **Mark as watched/unwatched** - Uses `sfeed_markread` to manage watched status
- **Bookmark videos** - Custom bookmarking feature for saving videos
- **YouTube thumbnails** - Shows video thumbnails for better browsing
- **Pagination** - Efficient loading of large feeds
- **Subscription management** - Add/remove YouTube channel subscriptions

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure your sfeed setup is correct:**
   - YouTube feeds should be in `~/rss/youtube/feeds/`
   - Watched URLs are tracked in `~/rss/urls-youtube`
   - Bookmarks are saved in `~/rss/urls-bookmarks-youtube`
   - Subscriptions are managed in `~/rss/youtube/sfeedrc`

3. **Run the application:**
   ```bash
   python run.py
   ```

4. **Open in browser:**
   Navigate to `http://127.0.0.1:5000`

## Directory Structure

```
~/rss/
├── youtube/
│   ├── feeds/              # sfeed output files
│   └── sfeedrc            # YouTube subscriptions
├── urls-youtube           # watched URLs (managed by sfeed_markread)
└── urls-bookmarks-youtube # bookmarked URLs (managed by this app)
```

## Usage

- **View Controls**: Switch between Unwatched, Watched, Bookmarked, and All videos
- **Search**: Type in the search box to filter videos by title, channel, or content
- **Sort**: Use the dropdown to sort videos by date, title, or channel
- **Actions**: 
  - Click "Mark as Watched/Unwatched" to toggle watched status
  - Click "Bookmark/Remove Bookmark" to save videos for later
  - Click "Open Video" to open in a new tab (automatically marks as watched)
- **Subscriptions**: Manage your YouTube channel subscriptions through the interface

## Integration with sfeed

This frontend integrates with sfeed by:
- Reading sfeed output files from `~/rss/youtube/feeds/`
- Using `sfeed_markread` command to manage watched/unwatched status
- Managing YouTube channel subscriptions in `~/rss/youtube/sfeedrc`
- Storing bookmarks in a separate file for the custom bookmarking feature

Make sure you have sfeed installed and configured to generate YouTube feeds in the expected directory.

## YouTube-Specific Features

- **Video Thumbnails**: Automatically extracts and displays YouTube video thumbnails
- **Channel Information**: Shows the YouTube channel name for each video
- **Direct Video Links**: Opens videos directly on YouTube
- **Subscription Management**: Add/remove YouTube channels through the web interface