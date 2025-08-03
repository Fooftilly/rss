#!/bin/bash

# Start both RSS frontends
echo "🚀 Starting RSS Feed Management System"
echo "======================================"

# Check if ports are available
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Port 5000 is already in use. Please stop the service using it."
    exit 1
fi

if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Port 5001 is already in use. Please stop the service using it."
    exit 1
fi

# Start YouTube frontend in background
echo "📺 Starting YouTube frontend on port 5000..."
cd web_frontend_youtube
python run.py &
YOUTUBE_PID=$!
cd ..

# Wait a moment for it to start
sleep 2

# Start News frontend in background
echo "📰 Starting News frontend on port 5001..."
cd web_frontend_news
python run.py &
NEWS_PID=$!
cd ..

# Wait a moment for it to start
sleep 2

echo ""
echo "✅ Both frontends are starting up!"
echo ""
echo "🌐 Access your feeds:"
echo "   YouTube: http://localhost:5000"
echo "   News:    http://localhost:5001"
echo ""
echo "🤖 Features:"
echo "   • Cross-platform AI recommendations"
echo "   • Unified learning across YouTube and News"
echo "   • Real-time preference correlation"
echo ""
echo "⏹️  To stop both services, press Ctrl+C"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping frontends..."
    kill $YOUTUBE_PID 2>/dev/null
    kill $NEWS_PID 2>/dev/null
    echo "✅ All services stopped."
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait $YOUTUBE_PID $NEWS_PID