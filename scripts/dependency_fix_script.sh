#!/bin/bash
# Fix Dependencies Script for RedshiftManager

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 RedshiftManager Dependency Fix${NC}"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt not found!${NC}"
    echo "Please run this script from the RedshiftManager directory"
    exit 1
fi

echo -e "${YELLOW}📍 Current directory: $(pwd)${NC}"

# Check Python
echo -e "${YELLOW}🐍 Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo -e "${GREEN}✅ Python3 found: $(python3 --version)${NC}"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo -e "${GREEN}✅ Python found: $(python --version)${NC}"
else
    echo -e "${RED}❌ Python not found!${NC}"
    exit 1
fi

# Check pip
echo -e "${YELLOW}📦 Checking pip...${NC}"
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${YELLOW}📦 Installing pip...${NC}"
    $PYTHON_CMD -m ensurepip --default-pip
fi

echo -e "${GREEN}✅ Pip version: $($PYTHON_CMD -m pip --version)${NC}"

# Upgrade pip
echo -e "${YELLOW}⬆️ Upgrading pip...${NC}"
$PYTHON_CMD -m pip install --upgrade pip

# Show requirements.txt content
echo -e "${YELLOW}📋 Current requirements.txt:${NC}"
head -10 requirements.txt
echo "..."

# Install dependencies with verbose output
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
$PYTHON_CMD -m pip install -r requirements.txt --verbose

# Verify critical packages
echo -e "${YELLOW}✅ Verifying critical packages...${NC}"

critical_packages=("streamlit" "python-dotenv" "sqlalchemy" "pandas" "cryptography")

for package in "${critical_packages[@]}"; do
    if $PYTHON_CMD -c "import ${package//-/_}" 2>/dev/null; then
        echo -e "${GREEN}✅ $package installed${NC}"
    else
        echo -e "${RED}❌ $package missing - installing individually...${NC}"
        $PYTHON_CMD -m pip install "$package"
    fi
done

# Test the application
echo -e "${YELLOW}🧪 Testing application...${NC}"
if $PYTHON_CMD -c "
import streamlit
import pandas
import sqlalchemy
from dotenv import load_dotenv
print('✅ All critical packages working!')
" 2>/dev/null; then
    echo -e "${GREEN}🎉 All dependencies working correctly!${NC}"
else
    echo -e "${RED}❌ Some packages still not working${NC}"
    echo "Try manual installation:"
    echo "pip install streamlit python-dotenv sqlalchemy pandas cryptography"
fi

echo -e "${BLUE}🚀 Ready to run: streamlit run main.py${NC}"
