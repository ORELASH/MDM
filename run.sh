#!/bin/bash
# RedshiftManager Run Script

echo "🚀 Starting RedshiftManager..."

# Check if virtual environment exists
if [ -d "../venv" ]; then
    echo "🔌 Activating virtual environment..."
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    echo "🔌 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if dashboard.py exists
if [ ! -f "dashboard.py" ]; then
    echo "❌ dashboard.py not found!"
    exit 1
fi

# Start Streamlit
echo "🌐 Starting Streamlit server..."
echo "📱 Access the application at: http://localhost:8501"
echo "📁 Using reorganized file structure"
echo ""

streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0
