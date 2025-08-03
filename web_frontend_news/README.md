# News Feed Reader - Web Frontend for sfeed

A modern web interface for reading news articles from RSS feeds using sfeed, with cross-platform recommendation integration.

## Features

- **Clean, responsive interface** - Works on desktop and mobile
- **Multiple views** - Unread, Read, Bookmarked, All articles, and Discover (personalized recommendations)
- **Search functionality** - Search through titles, sources, and content
- **Sorting options** - Sort by date, title, source, or personalized recommendations
- **Mark as read/unread** - Uses `sfeed_markread` to manage read status
- **Bookmark articles** - Custom bookmarking feature for saving articles
- **Article previews** - Shows article excerpts for better browsing
- **Pagination** - Efficient loading of large feeds
- **Subscription management** - Add/remove news source subscriptions
- **Smart Recommendations** - AI-powered recommendations that learn from your reading patterns
- **Cross-platform Learning** - Recommendations influenced by both news and YouTube viewing habits

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure your sfeed setup is correct:**
   - News feeds should be in `~/rss/news/feeds/`
   - Read URLs are tracked in `~/rss/urls`
   - Bookmarks are saved in `~/rss/urls-bookmarks-news`
   - Subscriptions are managed in `~/rss/news/sfeedrc`

3. **Run the application:**
   ```bash
   python run.py
   ```

4. **Open in browser:**
   Navigate to `http://127.0.0.1:5001`

## Directory Structure

```
~/rss/
├── news/
│   ├── feeds/             # sfeed output files
│   └── sfeedrc            # News subscriptions
├── urls                   # read URLs (managed by sfeed_markread)
├── urls-bookmarks-news    # bookmarked URLs (managed by this app)
├── urls-starred-news      # starred URLs (high preference articles)
├── urls-disliked-news     # disliked URLs (negative preference articles)
└── recommendations.db     # unified recommendation database (shared with YouTube)
```

## Usage

- **View Controls**: Switch between Unread, Read, Bookmarked, All articles, and Discover
  - **Discover Tab**: Shows personalized recommendations based on your reading and viewing preferences
- **Search**: Type in the search box to filter articles by title, source, or content
- **Sort**: Use the dropdown to sort articles by date, title, source, or get personalized recommendations
- **Actions**: 
  - **Click title** to open article (high preference signal - full learning boost)
  - **Click "Star"** to indicate high preference (3x learning boost)
  - **Click "Dislike"** to decrease source preference (negative learning signal)
  - **Click "Mark as Read"** to just mark as seen (low preference signal - minimal learning)
  - **Click "Bookmark"** to save articles for later
- **Subscriptions**: Manage your news source subscriptions through the interface
- **Recommendations**: View your recommendation stats and see how the system learns your preferences

## Integration with sfeed

This frontend integrates with sfeed by:
- Reading sfeed output files from `~/rss/news/feeds/`
- Using `sfeed_markread` command to manage read/unread status
- Managing news source subscriptions in `~/rss/news/sfeedrc`
- Storing bookmarks in a separate file for the custom bookmarking feature

## Cross-Platform Recommendation System

The application includes an intelligent recommendation engine that learns from both news and YouTube interactions:

### How It Works
- **Source Preferences**: Learns which news sources you read most frequently
- **Content Analysis**: Analyzes article titles to understand your topic preferences
- **Cross-Platform Learning**: YouTube viewing habits influence news recommendations and vice versa
- **Reading Patterns**: Tracks when you typically read articles
- **Skip Detection**: Notices when you skip articles to avoid similar content
- **Interaction Weighting**: Differentiates between clicking to read (high preference) vs marking as read (low preference)

### Features
- **Unified Learning**: Your YouTube preferences influence news recommendations
- **Personalized Sorting**: Select "Recommended" from the sort dropdown to see articles ranked by your preferences
- **Star System**: Click the star button on articles you really like for 3x stronger preference learning
- **Cross-Influence**: Reading certain news topics will boost similar YouTube content recommendations
- **Privacy-First**: All learning data is stored locally in a unified SQLite database
- **Statistics View**: Check your recommendation stats to see what the system has learned across platforms

### Data Storage
Recommendation data is stored in `~/rss/recommendations.db` (shared with YouTube) and includes:
- Read article history
- Starred article history (high preference)
- Disliked article history (negative preference)
- Source preference scores
- Keyword preference scores (shared with YouTube keywords)
- Time-based reading patterns
- Cross-platform preference correlations

The system automatically updates as you interact with articles, requiring no manual configuration.