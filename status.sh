#!/bin/bash
# MultiDBManager Status Check Script

echo "📊 MultiDBManager Status Check"
echo "================================"

# Check if process is running
if pgrep -f "streamlit run main.py" > /dev/null; then
    PID=$(pgrep -f "streamlit run main.py" | head -1)
    echo "✅ Status: RUNNING"
    echo "🆔 Process ID: $PID"
    
    # Check if port is accessible
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 | grep -q "200"; then
        echo "🌐 Web Interface: ACCESSIBLE"
        echo "📍 Local URL: http://localhost:8501"
        echo "🔗 Network URL: http://$(hostname -I | awk '{print $1}'):8501"
    else
        echo "⚠️  Web Interface: NOT ACCESSIBLE"
    fi
    
    # Show memory usage
    MEMORY=$(ps -p $PID -o rss= 2>/dev/null | awk '{print int($1/1024)"MB"}')
    echo "💾 Memory Usage: ${MEMORY:-Unknown}"
    
    # Show uptime
    STARTED=$(ps -p $PID -o lstart= 2>/dev/null | awk '{print $4}')
    echo "⏱️  Started: ${STARTED:-Unknown}"
    
else
    echo "❌ Status: STOPPED"
    echo "💡 To start: ./start.sh"
fi

echo ""
echo "🔧 Management Commands:"
echo "   ./start.sh  - Start MultiDBManager"
echo "   ./stop.sh   - Stop MultiDBManager"
echo "   ./status.sh - Check status"