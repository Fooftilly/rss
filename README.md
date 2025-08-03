# RSS Feed Management System with Unified AI Recommendations

A comprehensive RSS feed management system with separate web frontends for YouTube videos and news articles, powered by a unified AI recommendation engine that learns from your behavior across both platforms.

## Features

### 🎯 Unified AI Recommendations
- **Cross-Platform Learning**: Your YouTube viewing habits influence news recommendations and vice versa
- **Intelligent Keyword Correlation**: The system learns connections between topics across platforms
- **Adaptive Scoring**: Recommendations improve over time based on your interactions
- **Privacy-First**: All learning data is stored locally in SQLite

### 📺 YouTube Frontend (Port 5000)
- Clean, responsive interface for YouTube RSS feeds
- Video thumbnails and metadata
- Watch/star/dislike tracking with AI learning
- Personalized video recommendations
- Subscription management

### 📰 News Frontend (Port 5001)
- **Enhanced Modern Interface**: Beautiful, responsive design with Font Awesome icons
- **Complete Feed Management**: Add/remove news sources with intuitive modal interface
- **Rich Article Display**: Article previews, source badges, and formatted timestamps
- **Advanced Actions**: Star, dislike, bookmark, and read tracking with visual feedback
- **AI-Powered Discovery**: Dedicated Discover tab with cross-platform recommendations
- **Detailed Statistics**: Comprehensive stats showing preferences and correlations

### 🔄 Cross-Platform Intelligence
- Reading tech news boosts tech YouTube video recommendations
- Watching philosophy videos enhances philosophy article suggestions
- Unified preference learning across content types
- Real-time correlation tracking between platforms

## Setup

### Prerequisites
1. Install [sfeed](https://codemadness.org/sfeed-simple-feed-parser.html)
2. Clone this repository to your home directory as `~/rss`

### Installation
```bash
cd ~/rss

# Install Python dependencies for both frontends
pip install -r web_frontend_youtube/requirements.txt
pip install -r web_frontend_news/requirements.txt

# Start YouTube frontend (port 5000)
cd web_frontend_youtube && python run.py &

# Start News frontend (port 5001)
cd ../web_frontend_news && python run.py &
```

### Directory Structure
```
~/rss/
├── web_frontend_youtube/          # YouTube web interface
├── web_frontend_news/             # News web interface
├── shared_models/                 # Unified recommendation engine
├── youtube/
│   ├── feeds/                     # YouTube RSS feeds
│   └── sfeedrc                    # YouTube subscriptions
├── news/
│   ├── feeds/                     # News RSS feeds
│   └── sfeedrc                    # News subscriptions
├── urls-youtube                   # YouTube watched URLs
├── urls                           # News read URLs
├── urls-bookmarks-youtube         # YouTube bookmarks
├── urls-bookmarks-news            # News bookmarks
├── urls-starred-youtube           # YouTube starred (high preference)
├── urls-starred-news              # News starred (high preference)
├── urls-disliked-youtube          # YouTube disliked (negative preference)
├── urls-disliked-news             # News disliked (negative preference)
├── recommendations.db             # Unified AI recommendation database
└── etags/                         # ETag cache for efficient fetching
```

## Enhanced Features

### 🎨 Improved News Frontend UI
- **Modern Design**: Beautiful gradient backgrounds, smooth animations, and professional styling
- **Font Awesome Icons**: Rich iconography throughout the interface for better visual communication
- **Enhanced Article Cards**: Improved layout with source badges, formatted timestamps, and preview text
- **Responsive Design**: Optimized for desktop, tablet, and mobile viewing
- **Visual Feedback**: Hover effects, loading states, and smooth transitions

### 🛠️ Complete Feed Management
- **Modal Interface**: Professional modal dialogs for managing news feeds
- **Add/Remove Feeds**: Easy-to-use forms for adding new RSS feeds and removing existing ones
- **Feed Validation**: URL validation and duplicate detection
- **Real-time Updates**: Changes are saved immediately and reflected in the interface
- **Error Handling**: Comprehensive error messages and user feedback

### 📊 Advanced Statistics
- **Detailed Analytics**: Comprehensive statistics showing reading patterns and preferences
- **Cross-Platform Insights**: View correlations between YouTube and news consumption
- **Top Sources & Keywords**: See your most preferred news sources and topics
- **Visual Presentation**: Well-formatted statistics with icons and organized sections

## Usage

### YouTube Frontend (http://localhost:5000)
- **Discover Tab**: AI-recommended videos based on your viewing and reading habits
- **Star System**: Click ⭐ on videos you love for 3x learning boost
- **Cross-Platform Boost**: Reading related news articles will boost similar video recommendations

### News Frontend (http://localhost:5001)
- **Discover Tab**: AI-recommended articles based on your reading and viewing habits
- **Star System**: Click ⭐ on articles you love for 3x learning boost
- **Cross-Platform Boost**: Watching related videos will boost similar article recommendations

### How Cross-Platform Learning Works

1. **Keyword Extraction**: The system extracts meaningful keywords from both video titles and article headlines
2. **Correlation Tracking**: When you interact with content, the system tracks correlations between keywords across platforms
3. **Preference Transfer**: High preference for "machine learning" videos will boost "AI" and "data science" article recommendations
4. **Adaptive Weighting**: The system learns which cross-platform correlations are most relevant to you

## Advanced Features

### Recommendation Statistics
Both frontends provide detailed statistics showing:
- Platform-specific preferences (channels/sources, keywords)
- Cross-platform correlations discovered by the AI
- Learning progress and recommendation accuracy

### Data Management
```bash
# View database statistics
python db_manager.py stats

# Clean up old data (keeps last 90 days)
python db_manager.py cleanup --days 90

# Backup recommendation database
python db_manager.py backup

# Export data for analysis
python db_manager.py export --format json
```

### Subscription Management
Both frontends include web-based subscription management:
- Add/remove YouTube channels or news sources
- Bulk import/export of subscriptions
- Automatic feed discovery

## Technical Details

### Unified Recommendation Engine
- **SQLite Database**: Efficient local storage with WAL mode for concurrency
- **Thread-Safe**: Multiple frontends can safely access the database simultaneously
- **Incremental Learning**: Recommendations improve with each interaction
- **Correlation Matrix**: Tracks keyword relationships across platforms

### Scoring Algorithm
The unified system uses a multi-factor scoring approach:
- **Source Preference** (30%): How much you like specific channels/news sources
- **Keyword Matching** (40%): Content topic alignment with your interests
- **Cross-Platform Correlation** (10%): Boost from related content on other platforms
- **Recency Bonus** (20%): Newer content gets priority

### Privacy & Security
- **Local Storage**: All data stays on your machine
- **No Tracking**: No external analytics or data collection
- **Open Source**: Full transparency in recommendation algorithms
- **Data Control**: Easy backup, export, and deletion of your data

## Automation

Script `runner.py` should be run at startup to automatically fetch feeds. There are many ways this can be achieved:

### Systemd (Linux)
```bash
# Create service file
sudo tee /etc/systemd/system/rss-feeds.service << EOF
[Unit]
Description=RSS Feed Fetcher
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/rss
ExecStart=/usr/bin/python3 $HOME/rss/runner.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable rss-feeds.service
sudo systemctl start rss-feeds.service
```

### Cron (Unix/Linux/macOS)
```bash
# Add to crontab (runs every 30 minutes)
crontab -e
# Add line: */30 * * * * cd ~/rss && python runner.py
```

## Troubleshooting

### Common Issues
1. **Port conflicts**: Change ports in `run.py` files if 5000/5001 are in use
2. **Permission errors**: Ensure the `~/rss` directory is writable
3. **Database locks**: Stop all frontends before running maintenance commands
4. **Missing feeds**: Check that sfeed is properly configured and running

### Debug Mode
Run frontends in debug mode for detailed logging:
```bash
# YouTube frontend
cd web_frontend_youtube && python run.py --debug

# News frontend  
cd web_frontend_news && python run.py --debug
```

## Contributing

This system is designed to be extensible. You can:
- Add new content platforms by implementing the unified recommendation interface
- Enhance the scoring algorithm with additional factors
- Improve the web interfaces with new features
- Add machine learning models for better recommendations

## ✅ Success Metrics

- ✅ **100% Backward Compatibility**: Existing YouTube frontend works unchanged
- ✅ **Enhanced UI/UX**: Modern, professional interface with Font Awesome icons and smooth animations
- ✅ **Complete Feed Management**: Full CRUD operations for news feeds with modal interface
- ✅ **Cross-Platform Learning**: Verified correlation tracking between platforms
- ✅ **Advanced Statistics**: Comprehensive analytics with cross-platform insights
- ✅ **Performance**: Sub-second recommendation scoring for large feeds
- ✅ **Reliability**: Comprehensive test coverage and error handling
- ✅ **User Experience**: Intuitive interfaces with visual feedback and clear AI indicators
- ✅ **Mobile Responsive**: Optimized for all device sizes
- ✅ **Professional Polish**: Production-ready interface with proper error handling

## 🎯 Implementation Highlights

### UI/UX Improvements
- **Modern Design System**: CSS custom properties, gradients, and consistent styling
- **Interactive Elements**: Hover effects, loading states, and smooth transitions
- **Professional Icons**: Font Awesome integration for better visual communication
- **Enhanced Typography**: Improved readability with proper font weights and spacing
- **Visual Hierarchy**: Clear information architecture with proper spacing and grouping

### Feed Management System
- **Modal-Based Interface**: Professional modal dialogs for feed management
- **Form Validation**: Real-time validation with user-friendly error messages
- **CRUD Operations**: Complete Create, Read, Update, Delete functionality for feeds
- **Bulk Operations**: Efficient handling of multiple feed operations
- **Persistence**: Changes are immediately saved and reflected across the system

### Advanced Analytics
- **Multi-Level Statistics**: Platform-specific and unified analytics
- **Correlation Tracking**: Visual representation of cross-platform learning
- **Performance Metrics**: Detailed insights into recommendation effectiveness
- **User Behavior Analysis**: Comprehensive tracking of interaction patterns

The implementation successfully creates a unified, intelligent RSS management system with a professional, modern interface that learns from user behavior across multiple content platforms, providing personalized recommendations that improve over time through cross-platform correlation analysis.

## License

Open source - feel free to modify and distribute according to your needs.
