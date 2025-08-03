@echo off
echo 🚀 Starting RedshiftManager...

REM Check if virtual environment exists
if exist "venv" (
    echo 🔌 Activating virtual environment...
    call venv\Scripts\activate
)

REM Check if main.py exists
if not exist "main.py" (
    echo ❌ main.py not found!
    pause
    exit /b 1
)

REM Start Streamlit
echo 🌐 Starting Streamlit server...
echo 📱 Access the application at: http://localhost:8501
echo.

streamlit run main.py --server.port=8501 --server.address=0.0.0.0
pause
