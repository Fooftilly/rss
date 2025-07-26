#!/bin/bash

# YouTube Feed Reader Startup Script

echo "Starting YouTube Feed Reader..."
echo "Make sure you have:"
echo "  - sfeed installed and configured"
echo "  - YouTube feeds in ~/rss/youtube/feeds/"
echo "  - Python dependencies installed (pip install -r requirements.txt)"
echo ""

# Check if feeds directory exists
if [ ! -d "$HOME/rss/youtube/feeds" ]; then
    echo "Warning: ~/rss/youtube/feeds directory not found!"
    echo "Please make sure sfeed is configured to output YouTube feeds there."
    echo ""
fi

# Check if sfeed_markread is available
if ! command -v sfeed_markread &> /dev/null; then
    echo "Warning: sfeed_markread command not found!"
    echo "Please make sure sfeed is installed and in your PATH."
    echo ""
fi

# Create bookmarks file if it doesn't exist
mkdir -p "$HOME/rss"
touch "$HOME/rss/urls-bookmarks-youtube"

echo "Starting web server on http://127.0.0.1:5000"
echo "Press Ctrl+C to stop"
echo ""

python run.py