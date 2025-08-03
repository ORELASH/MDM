#!/bin/bash
# RedshiftManager Setup with Virtual Environment
# Solves "externally-managed-environment" error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}🐍 RedshiftManager Setup with Virtual Environment${NC}"
echo "=================================================="

# Check if we're in the RedshiftManager directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt not found!${NC}"
    echo "Please run this script from the RedshiftManager directory"
    exit 1
fi

echo -e "${YELLOW}📍 Current directory: $(pwd)${NC}"

# Check Python
echo -e "${YELLOW}🔍 Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Python3 found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python3 not found!${NC}"
    echo "Please install Python3: sudo apt update && sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# Check if python3-venv is available
echo -e "${YELLOW}🔍 Checking python3-venv...${NC}"
if $PYTHON_CMD -m venv --help &> /dev/null; then
    echo -e "${GREEN}✅ python3-venv available${NC}"
else
    echo -e "${YELLOW}📦 Installing python3-venv...${NC}"
    sudo apt update
    sudo apt install python3-venv python3-full -y
fi

# Remove old venv if exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}🗑️  Removing old virtual environment...${NC}"
    rm -rf venv
fi

# Create virtual environment
echo -e "${YELLOW}🔨 Creating virtual environment...${NC}"
$PYTHON_CMD -m venv venv

if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Failed to create virtual environment!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment created successfully!${NC}"

# Activate virtual environment
echo -e "${YELLOW}🔌 Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip in venv
echo -e "${YELLOW}⬆️  Upgrading pip in virtual environment...${NC}"
pip install --upgrade pip

# Install requirements
echo -e "${YELLOW}📦 Installing requirements in virtual environment...${NC}"
pip install -r requirements.txt

# Verify critical packages
echo -e "${YELLOW}✅ Verifying installation...${NC}"

critical_packages=("streamlit" "python-dotenv" "sqlalchemy" "pandas" "cryptography")
all_good=true

for package in "${critical_packages[@]}"; do
    if python -c "import ${package//-/_}" 2>/dev/null; then
        echo -e "${GREEN}✅ $package${NC}"
    else
        echo -e "${RED}❌ $package${NC}"
        all_good=false
    fi
done

if [ "$all_good" = true ]; then
    echo -e "${GREEN}🎉 All packages installed successfully!${NC}"
else
    echo -e "${RED}❌ Some packages failed to install${NC}"
    exit 1
fi

# Update run scripts to use venv
echo -e "${YELLOW}🔧 Updating run scripts...${NC}"

# Update run.sh
cat > run.sh << 'EOF'
#!/bin/bash
# RedshiftManager Run Script with Virtual Environment

echo "🚀 Starting RedshiftManager with Virtual Environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: ./setup_with_venv.sh"
    exit 1
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found!"
    exit 1
fi

# Start Streamlit
echo "🌐 Starting Streamlit server..."
echo "📱 Access the application at: http://localhost:8501"
echo "💡 To stop: Press Ctrl+C"
echo ""

streamlit run main.py --server.port=8501 --server.address=0.0.0.0
EOF

chmod +x run.sh

# Update run.bat for Windows
cat > run.bat << 'EOF'
@echo off
echo 🚀 Starting RedshiftManager with Virtual Environment...

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Virtual environment not found!
    echo Please run: setup_with_venv.sh
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate

REM Check if main.py exists
if not exist "main.py" (
    echo ❌ main.py not found!
    pause
    exit /b 1
)

REM Start Streamlit
echo 🌐 Starting Streamlit server...
echo 📱 Access the application at: http://localhost:8501
echo 💡 To stop: Press Ctrl+C
echo.

streamlit run main.py --server.port=8501 --server.address=0.0.0.0
pause
EOF

# Test the application
echo -e "${YELLOW}🧪 Testing the application...${NC}"
if python -c "
import streamlit
import pandas  
import sqlalchemy
from dotenv import load_dotenv
print('✅ All imports successful!')
" 2>/dev/null; then
    echo -e "${GREEN}🎉 Application ready to run!${NC}"
else
    echo -e "${RED}❌ Application test failed${NC}"
    exit 1
fi

# Final instructions
echo ""
echo -e "${PURPLE}========================================${NC}"
echo -e "${GREEN}🎉 Setup Complete with Virtual Environment!${NC}"
echo -e "${PURPLE}========================================${NC}"
echo ""
echo -e "${YELLOW}🚀 To start the application:${NC}"
echo -e "${WHITE}   ./run.sh                    ${NC}${BLUE}# Recommended${NC}"
echo -e "${WHITE}   source venv/bin/activate && streamlit run main.py${NC}"
echo ""
echo -e "${YELLOW}🛠️  Virtual Environment Info:${NC}"
echo -e "${WHITE}   Location: $(pwd)/venv${NC}"
echo -e "${WHITE}   Activate: source venv/bin/activate${NC}"
echo -e "${WHITE}   Deactivate: deactivate${NC}"
echo ""
echo -e "${YELLOW}📦 Installed Packages:${NC}"
pip list | head -10
echo "   ... and more"
echo ""
echo -e "${GREEN}✨ Ready to code!${NC}"

# Ask to start now
echo ""
read -p "🚀 Do you want to start the application now? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}🌐 Starting RedshiftManager...${NC}"
    ./run.sh
fi
