#!/bin/bash
# MultiDBManager Health Monitor

echo "🔍 MultiDBManager Health Monitor"
echo "================================"

while true; do
    clear
    echo "🕒 $(date)"
    echo "================================"
    
    # Check if process is running
    if pgrep -f "streamlit run main.py" > /dev/null; then
        PID=$(pgrep -f "streamlit run main.py" | head -1)
        echo "✅ Status: RUNNING (PID: $PID)"
        
        # Memory usage
        MEMORY=$(ps -p $PID -o rss= 2>/dev/null | awk '{print int($1/1024)"MB"}')
        echo "💾 Memory: ${MEMORY:-Unknown}"
        
        # CPU usage
        CPU=$(ps -p $PID -o %cpu= 2>/dev/null | awk '{print $1"%"}')
        echo "🚀 CPU: ${CPU:-Unknown}"
        
        # Web interface check
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 | grep -q "200"; then
            echo "🌐 Web Interface: ✅ ACCESSIBLE"
        else
            echo "🌐 Web Interface: ❌ NOT ACCESSIBLE"
        fi
        
        # Check for recent errors
        ERROR_COUNT=$(tail -n 10 logs/redshift_manager.log 2>/dev/null | grep -c "ERROR" || echo "0")
        if [ "$ERROR_COUNT" -gt 0 ]; then
            echo "⚠️  Recent Errors: $ERROR_COUNT"
            echo "📋 Last Error:"
            tail -n 10 logs/redshift_manager.log 2>/dev/null | grep "ERROR" | tail -1
        else
            echo "✅ No Recent Errors"
        fi
        
    else
        echo "❌ Status: STOPPED"
        echo "💡 Run ./start.sh to restart"
    fi
    
    echo ""
    echo "🔄 Refreshing in 5 seconds... (Ctrl+C to exit)"
    sleep 5
done