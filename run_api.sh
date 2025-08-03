#!/bin/bash
# RedshiftManager API Server Launcher
# Launches FastAPI server with proper environment setup

echo "🚀 Starting RedshiftManager API Server..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ -d "../venv" ]; then
    echo "✅ Activating virtual environment..."
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️ Virtual environment not found, using system Python"
fi

# Check if requirements are installed
echo "🔍 Checking dependencies..."
python -c "
import fastapi, uvicorn, pydantic
print('✅ FastAPI dependencies are installed')
" 2>/dev/null || {
    echo "❌ FastAPI dependencies missing. Installing..."
    pip install fastapi uvicorn pydantic
}

# Set environment variables
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
export APP_ENV="development"

# Parse command line arguments
DEV_MODE=false
HOST="127.0.0.1"
PORT=8000
WORKERS=1

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --dev          Run in development mode with hot reload"
            echo "  --host HOST    Host to bind to (default: 127.0.0.1)"
            echo "  --port PORT    Port to bind to (default: 8000)"
            echo "  --workers N    Number of workers (default: 1)"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Start the server
echo "🌐 Server will be available at: http://$HOST:$PORT"
echo "📚 API Documentation: http://$HOST:$PORT/docs"
echo "🔄 Alternative Docs: http://$HOST:$PORT/redoc"
echo ""

if [ "$DEV_MODE" = true ]; then
    echo "🔧 Starting in DEVELOPMENT mode with hot reload..."
    python api/server.py --host "$HOST" --port "$PORT" --dev
else
    echo "🚀 Starting in PRODUCTION mode..."
    python api/server.py --host "$HOST" --port "$PORT" --workers "$WORKERS"
fi