#!/bin/bash
# MultiDBManager Startup Script

echo "🚀 Starting MultiDBManager..."
echo "📁 Universal Multi-Database Management System"

# Change to script directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements-minimal.txt
else
    source venv/bin/activate
fi

# Check if port is available
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8501 is already in use. Stopping existing process..."
    pkill -f "streamlit run main.py"
    sleep 2
fi

echo "🔧 Starting Streamlit server..."
echo "📍 URL: http://localhost:8501"
echo "🌐 Network URL: http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "Press Ctrl+C to stop the server"

# Start the application
streamlit run main.py --server.port 8501 --server.address 0.0.0.0