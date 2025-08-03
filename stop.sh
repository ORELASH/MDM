#!/bin/bash
# MultiDBManager Stop Script

echo "🛑 Stopping MultiDBManager..."

# Find and kill Streamlit processes
if pgrep -f "streamlit run main.py" > /dev/null; then
    echo "📍 Found running MultiDBManager processes..."
    pkill -f "streamlit run main.py"
    echo "✅ MultiDBManager stopped successfully"
else
    echo "ℹ️  No running MultiDBManager processes found"
fi

# Check if stopped
sleep 1
if pgrep -f "streamlit run main.py" > /dev/null; then
    echo "⚠️  Force stopping remaining processes..."
    pkill -9 -f "streamlit run main.py"
fi

echo "🏁 MultiDBManager shutdown complete"