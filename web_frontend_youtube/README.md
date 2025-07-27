# YouTube Feed Reader - Web Frontend for sfeed

A modern web interface for watching YouTube videos from RSS feeds using sfeed.

## Features

- **Clean, responsive interface** - Works on desktop and mobile
- **Multiple views** - Unwatched, Watched, Bookmarked, All videos, and Discover (personalized recommendations)
- **Search functionality** - Search through titles, channels, and content
- **Sorting options** - Sort by date, title, channel, or personalized recommendations
- **Mark as watched/unwatched** - Uses `sfeed_markread` to manage watched status
- **Bookmark videos** - Custom bookmarking feature for saving videos
- **YouTube thumbnails** - Shows video thumbnails for better browsing
- **Pagination** - Efficient loading of large feeds
- **Subscription management** - Add/remove YouTube channel subscriptions
- **Smart Recommendations** - AI-powered recommendations that learn from your viewing patterns

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
├── urls-bookmarks-youtube # bookmarked URLs (managed by this app)
├── urls-starred-youtube   # starred URLs (high preference videos)
├── urls-disliked-youtube  # disliked URLs (negative preference videos)
└── recommendations.json   # recommendation learning data
```

## Usage

- **View Controls**: Switch between Unwatched, Watched, Bookmarked, All videos, and Discover
  - **Discover Tab**: Shows personalized recommendations for unstarred videos based on your preferences
- **Search**: Type in the search box to filter videos by title, channel, or content
- **Sort**: Use the dropdown to sort videos by date, title, channel, or get personalized recommendations
- **Actions**: 
  - **Click thumbnail/title** to open video (high preference signal - full learning boost)
  - **Click "Star"** to indicate high preference (3x learning boost)
  - **Click "Dislike"** to decrease channel preference (negative learning signal)
  - **Click "Mark as Watched"** to just mark as seen (low preference signal - minimal learning)
  - **Click "Bookmark"** to save videos for later
- **Subscriptions**: Manage your YouTube channel subscriptions through the interface
- **Recommendations**: View your recommendation stats and see how the system learns your preferences

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
- **Custom Favicon**: Distinctive icon representing RSS feeds, video content, and smart recommendations

## Smart Recommendation System

The application includes an intelligent recommendation engine that learns from your viewing behavior:

### How It Works
- **Channel Preferences**: Learns which channels you watch most frequently
- **Content Analysis**: Analyzes video titles to understand your topic preferences
- **Viewing Patterns**: Tracks when you typically watch videos
- **Skip Detection**: Notices when you skip videos to avoid similar content
- **Interaction Weighting**: Differentiates between clicking to watch (high preference) vs marking as watched (low preference)

### Features
- **Personalized Sorting**: Select "Recommended" from the sort dropdown to see videos ranked by your preferences
- **Star System**: Click the star button on videos you really like for 3x stronger preference learning
- **Learning Over Time**: The more you use the app, the better the recommendations become
- **Privacy-First**: All learning data is stored locally on your machine
- **Statistics View**: Check your recommendation stats to see what the system has learned

### Data Storage
Recommendation data is stored in `~/rss/recommendations.json` and includes:
- Watched video history
- Starred video history (high preference)
- Disliked video history (negative preference)
- Channel preference scores
- Keyword preference scores
- Time-based viewing patterns

User preferences are also tracked in separate files:
- `~/rss/urls-starred-youtube` for starred videos
- `~/rss/urls-disliked-youtube` for disliked videos

The system automatically updates as you interact with videos, requiring no manual configuration.