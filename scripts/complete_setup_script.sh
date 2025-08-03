#!/bin/bash
# RedshiftManager Complete Setup Script
# Creates the entire project structure with all files
# Run with: chmod +x setup_redshift_manager.sh && ./setup_redshift_manager.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_NAME="RedshiftManager"
PROJECT_DIR="$PWD/$PROJECT_NAME"

echo -e "${BLUE}🚀 RedshiftManager Complete Setup${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check if directory exists
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️  Directory '$PROJECT_NAME' already exists.${NC}"
    read -p "Do you want to continue and overwrite? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Setup cancelled.${NC}"
        exit 1
    fi
    rm -rf "$PROJECT_DIR"
fi

# Create project directory
echo -e "${CYAN}📁 Creating project directory...${NC}"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create directory structure
echo -e "${CYAN}📁 Creating directory structure...${NC}"
mkdir -p models utils config pages data logs backup uploads temp locales

echo -e "${GREEN}✅ Created directory structure${NC}"

# Create requirements.txt
echo -e "${CYAN}📦 Creating requirements.txt...${NC}"
cat > requirements.txt << 'EOF'
# RedshiftManager Requirements
# Core Dependencies for Amazon Redshift Management Tool

# Core Framework
streamlit>=1.28.0,<2.0.0
streamlit-option-menu>=0.3.6

# Database & ORM
SQLAlchemy>=2.0.0,<3.0.0
psycopg2-binary>=2.9.7
alembic>=1.12.0

# Security & Encryption
cryptography>=41.0.0
bcrypt>=4.0.0

# Data Processing & Analysis
pandas>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0
plotly>=5.15.0
matplotlib>=3.7.0

# Configuration & Environment
python-dotenv>=1.0.0
pyyaml>=6.0

# HTTP & API
requests>=2.31.0
urllib3>=2.0.0,<3.0.0

# Date & Time
python-dateutil>=2.8.0
pytz>=2023.3

# Utilities
click>=8.1.0
tqdm>=4.65.0
attrs>=23.1.0

# Validation & Parsing
pydantic>=2.0.0,<3.0.0

# Streamlit Components
streamlit-aggrid>=0.3.4

# SQL Tools
sqlparse>=0.4.4
sqlalchemy-utils>=0.41.0

# Performance
cachetools>=5.3.0

# Platform Specific
pywin32>=306; sys_platform == "win32"
distro>=1.8.0; sys_platform == "linux"

# Security Updates
certifi>=2023.7.22
setuptools>=68.0.0
pip>=23.2.0
EOF

echo -e "${GREEN}✅ Created requirements.txt${NC}"

# Create .env file
echo -e "${CYAN}⚙️  Creating .env file...${NC}"
cat > .env << 'EOF'
# RedshiftManager Environment Configuration

# Application Settings
APP_NAME=RedshiftManager
APP_VERSION=1.0.0
APP_ENV=development
DEBUG=true
SECRET_KEY=your-super-secret-key-change-this-in-production
MAINTENANCE_MODE=false

# Security & Encryption
ENCRYPTION_KEY=fGqnZ8J1WzQ7XmR4DdJ9kF2BzZ6eX8xJ9sP7Lr5vF3wQ=
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGITS=true
PASSWORD_REQUIRE_SPECIAL=true
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=900

# Database Settings
DB_TYPE=sqlite
DB_NAME=redshift_manager.db
DB_ENCRYPTION_ENABLED=true
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Redshift Default Settings
REDSHIFT_DEFAULT_PORT=5439
REDSHIFT_DEFAULT_DATABASE=dev
REDSHIFT_SSL_MODE=require
REDSHIFT_CONNECTION_TIMEOUT=30
REDSHIFT_QUERY_TIMEOUT=300
REDSHIFT_MAX_CONNECTIONS=10
REDSHIFT_REQUIRE_SSL=true
REDSHIFT_VERIFY_SSL=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s
LOG_TO_FILE=true
LOG_FILE_MAX_SIZE=10485760
LOG_FILE_BACKUP_COUNT=5

# UI & Internationalization
DEFAULT_LANGUAGE=en
SUPPORTED_LANGUAGES=en,he
DEFAULT_THEME=light
ENABLE_RTL=true
WIDE_MODE=true
ITEMS_PER_PAGE=50
ENABLE_AUTO_REFRESH=true
AUTO_REFRESH_INTERVAL=30

# Performance & Caching
ENABLE_CACHING=true
CACHE_TTL=300
CACHE_MAX_SIZE=1000
ENABLE_QUERY_CACHE=true
ENABLE_CONNECTION_POOLING=true

# Security & Audit
ENABLE_AUDIT_LOGGING=true
AUDIT_RETENTION_DAYS=90
INCLUDE_SENSITIVE_IN_AUDIT=false
ENABLE_REAL_TIME_ALERTS=true
ENABLE_RBAC=true
DEFAULT_USER_ROLE=viewer
ADMIN_ROLE=admin

# Backup & Maintenance
ENABLE_AUTO_BACKUP=true
BACKUP_INTERVAL_HOURS=24
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION=true
BACKUP_PATH=./backups

# Feature Flags
FEATURE_BULK_OPERATIONS=true
FEATURE_ADVANCED_PERMISSIONS=true
FEATURE_CUSTOM_DASHBOARDS=false
FEATURE_API_ACCESS=false
EOF

echo -e "${GREEN}✅ Created .env file${NC}"

# Create models/__init__.py
echo -e "${CYAN}🔧 Creating models package...${NC}"
cat > models/__init__.py << 'EOF'
"""RedshiftManager Models Package"""

__version__ = "1.0.0"
__author__ = "RedshiftManager Team"

# Safe imports that won't fail if modules don't exist yet
__all__ = []

try:
    from .encryption_model import (
        get_encryption_manager,
        get_password_validator,
        PasswordPolicy,
        EncryptionConfig
    )
    __all__.extend(['get_encryption_manager', 'get_password_validator', 'PasswordPolicy', 'EncryptionConfig'])
except ImportError:
    pass

try:
    from .configuration_model import (
        get_configuration_manager,
        ConfigLevel,
        SecurityLevel
    )
    __all__.extend(['get_configuration_manager', 'ConfigLevel', 'SecurityLevel'])
except ImportError:
    pass

try:
    from .redshift_connection_model import (
        get_connector,
        ConnectionConfig,
        QueryResult,
        RedshiftUserInfo
    )
    __all__.extend(['get_connector', 'ConnectionConfig', 'QueryResult', 'RedshiftUserInfo'])
except ImportError:
    pass

try:
    from .database_models import (
        get_database_manager,
        RedshiftCluster,
        RedshiftUser,
        RedshiftRole,
        UserRole,
        UserSession,
        AuditLog
    )
    __all__.extend(['get_database_manager', 'RedshiftCluster', 'RedshiftUser', 'RedshiftRole', 'UserRole', 'UserSession', 'AuditLog'])
except ImportError:
    pass
EOF

# Create utils/__init__.py
cat > utils/__init__.py << 'EOF'
"""RedshiftManager Utils Package"""

__version__ = "1.0.0"

# Simple fallback translation function
def get_text(key, default=None, **kwargs):
    """Get translated text with fallback"""
    return default or key

# Convenience alias
_ = get_text

__all__ = ['get_text', '_']

# Try to import advanced i18n if available
try:
    from .i18n_helper import (
        set_language,
        create_language_selector,
        apply_rtl_css,
        format_number,
        format_date,
        format_time,
        get_translation_manager,
        get_streamlit_helper
    )
    # Override simple function with advanced one
    from .i18n_helper import get_text
    _ = get_text
    
    __all__.extend([
        'set_language',
        'create_language_selector', 
        'apply_rtl_css',
        'format_number',
        'format_date',
        'format_time',
        'get_translation_manager',
        'get_streamlit_helper'
    ])
except ImportError:
    pass
EOF

# Create config/__init__.py
cat > config/__init__.py << 'EOF'
"""RedshiftManager Config Package"""

__version__ = "1.0.0"

import json
from pathlib import Path

def load_app_settings():
    """Load application settings from JSON file."""
    try:
        config_path = Path(__file__).parent / "app_settings.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        import logging
        logging.warning(f"Could not load app settings: {e}")
    
    # Return minimal default settings
    return {
        "application": {
            "name": "RedshiftManager",
            "version": "1.0.0",
            "environment": "development"
        },
        "ui": {
            "theme": {
                "default_theme": "light"
            }
        }
    }

# Load settings on import
APP_SETTINGS = load_app_settings()

__all__ = ['APP_SETTINGS', 'load_app_settings']
EOF

# Create pages/__init__.py
cat > pages/__init__.py << 'EOF'
"""RedshiftManager Pages Package"""
__version__ = "1.0.0"
EOF

echo -e "${GREEN}✅ Created package initialization files${NC}"

# Create a basic config/app_settings.json
echo -e "${CYAN}⚙️  Creating app settings...${NC}"
cat > config/app_settings.json << 'EOF'
{
  "_metadata": {
    "version": "1.0.0",
    "created_at": "2024-07-27T00:00:00Z",
    "description": "RedshiftManager Application Configuration"
  },
  "application": {
    "name": "RedshiftManager",
    "version": "1.0.0",
    "environment": "development",
    "debug_mode": true,
    "timezone": "UTC",
    "locale": "en",
    "supported_locales": ["en", "he"]
  },
  "ui": {
    "theme": {
      "default_theme": "light",
      "available_themes": ["light", "dark", "auto"]
    },
    "layout": {
      "sidebar_collapsed": false,
      "wide_mode": true,
      "items_per_page": 50
    },
    "components": {
      "enable_sql_preview": true,
      "enable_auto_refresh": true,
      "auto_refresh_interval": 30
    }
  },
  "database": {
    "local": {
      "engine": "sqlite",
      "filename": "redshift_manager.db",
      "backup_enabled": true,
      "encryption_enabled": true
    }
  },
  "redshift": {
    "defaults": {
      "port": 5439,
      "database": "dev",
      "ssl_mode": "require",
      "connection_timeout": 30,
      "query_timeout": 300
    }
  },
  "security": {
    "authentication": {
      "session_timeout": 3600,
      "max_login_attempts": 5,
      "lockout_duration": 900
    },
    "encryption": {
      "algorithm": "AES-256-GCM",
      "key_derivation": "PBKDF2",
      "iterations": 100000
    }
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
EOF

# Create main.py
echo -e "${CYAN}🚀 Creating main application...${NC}"
cat > main.py << 'EOF'
#!/usr/bin/env python3
"""
RedshiftManager Main Application
Cross-platform Amazon Redshift management tool with Streamlit interface.
"""

import streamlit as st
import sys
import os
from pathlib import Path
import json

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Configure Streamlit
st.set_page_config(
    page_title="RedshiftManager",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

def check_dependencies():
    """Check if required dependencies are installed"""
    missing_deps = []
    required_packages = [
        'streamlit', 'sqlalchemy', 'pandas', 'plotly', 
        'cryptography', 'psycopg2', 'python-dotenv'
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_deps.append(package)
    
    return missing_deps

def load_environment():
    """Load environment variables"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return True
    except ImportError:
        return False

def main():
    """Main application entry point"""
    
    # Load environment
    env_loaded = load_environment()
    
    # Header
    st.title("🔧 RedshiftManager")
    st.markdown("### Cross-platform Amazon Redshift Management Tool")
    
    # Check dependencies
    missing_deps = check_dependencies()
    
    if missing_deps:
        st.error("❌ Missing dependencies detected!")
        st.write("**Missing packages:**")
        for dep in missing_deps:
            st.write(f"- {dep}")
        st.info("Run: `pip install -r requirements.txt` to install missing dependencies")
        return
    
    st.success("✅ All dependencies are installed!")
    
    # Environment status
    if env_loaded:
        st.success("✅ Environment variables loaded from .env")
    else:
        st.warning("⚠️ python-dotenv not available, using system environment")
    
    # Project status
    st.subheader("📊 Project Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Python", f"{sys.version_info.major}.{sys.version_info.minor}")
    
    with col2:
        st.metric("Platform", sys.platform.title())
    
    with col3:
        app_env = os.getenv('APP_ENV', 'development')
        st.metric("Environment", app_env.title())
    
    with col4:
        st.metric("Status", "Running")
    
    # Module status
    st.subheader("🔧 Core Modules Status")
    
    modules_to_check = [
        ("models", "Data Models"),
        ("utils", "Utilities"), 
        ("config", "Configuration"),
        ("pages", "UI Pages")
    ]
    
    for module_name, description in modules_to_check:
        try:
            __import__(module_name)
            st.success(f"✅ {description}")
        except ImportError:
            st.error(f"❌ {description}")
    
    # Advanced modules check
    st.subheader("🏗️ Advanced Modules Status")
    
    advanced_modules = [
        ("models.encryption_model", "🔐 Encryption & Security"),
        ("models.configuration_model", "⚙️ Configuration Management"),
        ("models.redshift_connection_model", "🔌 Redshift Connectivity"),
        ("models.database_models", "🗄️ Database Models"),
        ("utils.i18n_helper", "🌐 Internationalization"),
    ]
    
    missing_advanced = []
    for module_name, description in advanced_modules:
        try:
            __import__(module_name)
            st.success(f"✅ {description}")
        except ImportError:
            st.warning(f"⚠️ {description} - Implementation needed")
            missing_advanced.append(module_name)
    
    # File structure check
    with st.expander("📁 File Structure"):
        important_files = [
            "requirements.txt",
            ".env",
            "models/__init__.py",
            "utils/__init__.py",
            "config/__init__.py",
            "config/app_settings.json",
            "data/",
            "logs/",
            "backup/"
        ]
        
        for file_path in important_files:
            path = Path(file_path)
            if path.exists():
                st.success(f"✅ {file_path}")
            else:
                st.error(f"❌ {file_path}")
    
    # Navigation placeholder
    st.subheader("🧭 Navigation")
    
    # Simple navigation
    pages = ["Home", "Clusters", "Users", "Roles", "Permissions", "Reports", "Settings"]
    selected_page = st.selectbox("Select Page:", pages)
    
    if selected_page == "Home":
        st.info("👋 Welcome to RedshiftManager! Select a page from the dropdown above.")
    else:
        st.info(f"🚧 {selected_page} page is under development.")
    
    # Instructions
    st.subheader("🚀 Next Steps")
    
    if missing_advanced:
        st.warning("⚠️ Some advanced modules are missing. Add them to unlock full functionality.")
        
        with st.expander("📝 Missing Modules Instructions"):
            st.markdown("""
            **To complete the setup, add these advanced modules:**
            
            1. **Copy the following files from the conversation:**
               - `models/encryption_model.py` - Security and encryption
               - `models/configuration_model.py` - Configuration management
               - `models/redshift_connection_model.py` - Redshift connectivity
               - `models/database_models.py` - Database models
               - `utils/i18n_helper.py` - Internationalization
            
            2. **Complete UI Pages:**
               - `pages/clusters_management_page.py`
               - `pages/settings_page.py`
               - Update existing pages
            
            3. **Test the application:**
               - Add Redshift connections
               - Test user management
               - Verify security features
            """)
    else:
        st.success("🎉 All core modules are loaded! The application is fully functional.")
    
    # Development info
    with st.expander("🔍 Development Information"):
        st.write("**Project Root:**", str(project_root))
        st.write("**App Name:**", os.getenv('APP_NAME', 'RedshiftManager'))
        st.write("**Debug Mode:**", os.getenv('DEBUG', 'false'))
        st.write("**Default Language:**", os.getenv('DEFAULT_LANGUAGE', 'en'))
        
        # Config file content
        config_file = Path("config/app_settings.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            st.json(config_data)

if __name__ == "__main__":
    main()
EOF

echo -e "${GREEN}✅ Created main application${NC}"

# Create README.md
echo -e "${CYAN}📖 Creating README...${NC}"
cat > README.md << 'EOF'
# 🔧 RedshiftManager

Cross-platform Amazon Redshift Management Tool

## 🚀 Quick Start

The project has been set up automatically! Follow these steps:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
streamlit run main.py
```

### 3. Open Your Browser
Navigate to `http://localhost:8501`

## 📊 Project Status

✅ **Completed:**
- Project structure created
- Core dependencies configured
- Environment setup complete
- Basic application running
- Package initialization

⚠️ **Next Steps:**
- Add advanced model implementations
- Complete UI pages
- Configure Redshift connections
- Test all functionality

## 🏗️ Architecture

```
RedshiftManager/
├── models/           # Data models and business logic
│   ├── __init__.py   ✅
│   ├── encryption_model.py      (to be added)
│   ├── configuration_model.py   (to be added)
│   ├── redshift_connection_model.py (to be added)
│   └── database_models.py       (to be added)
├── utils/            # Utility functions
│   ├── __init__.py   ✅
│   └── i18n_helper.py           (to be added)
├── config/           # Configuration
│   ├── __init__.py   ✅
│   └── app_settings.json        ✅
├── pages/            # UI pages
├── data/             # Local database
├── logs/             # Application logs
└── backup/           # Backups
```

## 🔧 Features

- 🔐 Advanced security and encryption
- 🌐 Multi-language support (English/Hebrew)
- 🗄️ Comprehensive database management
- 📊 Real-time monitoring
- ⚙️ Hierarchical configuration
- 🔌 Advanced Redshift connectivity

## 📝 Adding Advanced Modules

To complete the setup, copy the advanced module files from the conversation:

1. **models/encryption_model.py** - Security system
2. **models/configuration_model.py** - Configuration management
3. **models/redshift_connection_model.py** - Redshift connectivity
4. **models/database_models.py** - Database models
5. **utils/i18n_helper.py** - Internationalization

## 🌐 Access

After running `streamlit run main.py`, open:
- **Local:** http://localhost:8501
- **Network:** http://[your-ip]:8501

## 📄 License

MIT License

---

**Generated automatically by RedshiftManager setup script**
EOF

echo -e "${GREEN}✅ Created README${NC}"

# Create basic language files
echo -e "${CYAN}🌐 Creating language files...${NC}"
mkdir -p locales

cat > locales/en.json << 'EOF'
{
  "app": {
    "title": "RedshiftManager",
    "subtitle": "Amazon Redshift Management Tool",
    "loading": "Loading...",
    "success": "Success",
    "error": "Error",
    "warning": "Warning"
  },
  "navigation": {
    "home": "Home",
    "clusters": "Clusters", 
    "users": "Users",
    "roles": "Roles",
    "permissions": "Permissions",
    "reports": "Reports",
    "settings": "Settings"
  }
}
EOF

cat > locales/he.json << 'EOF'
{
  "app": {
    "title": "מנהל רדשיפט",
    "subtitle": "כלי ניהול Amazon Redshift",
    "loading": "טוען...",
    "success": "הצלחה",
    "error": "שגיאה", 
    "warning": "אזהרה"
  },
  "navigation": {
    "home": "בית",
    "clusters": "קלסטרים",
    "users": "משתמשים", 
    "roles": "תפקידים",
    "permissions": "הרשאות",
    "reports": "דוחות",
    "settings": "הגדרות"
  }
}
EOF

echo -e "${GREEN}✅ Created language files${NC}"

# Create run scripts
echo -e "${CYAN}🏃 Creating run scripts...${NC}"

# Linux/macOS run script
cat > run.sh << 'EOF'
#!/bin/bash
# RedshiftManager Run Script

echo "🚀 Starting RedshiftManager..."

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "🔌 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found!"
    exit 1
fi

# Start Streamlit
echo "🌐 Starting Streamlit server..."
echo "📱 Access the application at: http://localhost:8501"
echo ""

streamlit run main.py --server.port=8501 --server.address=0.0.0.0
EOF

chmod +x run.sh

# Windows run script
cat > run.bat << 'EOF'
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
EOF

echo -e "${GREEN}✅ Created run scripts${NC}"

# Install dependencies if Python is available
echo -e "${CYAN}📦 Installing dependencies...${NC}"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python not found! Please install Python 3.8+ and try again.${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Python found: $PYTHON_CMD${NC}"

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${YELLOW}📋 Python version: $PYTHON_VERSION${NC}"

# Install pip if not available
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${YELLOW}📦 Installing pip...${NC}"
    $PYTHON_CMD -m ensurepip --default-pip
fi

# Upgrade pip
echo -e "${YELLOW}⬆️  Upgrading pip...${NC}"
$PYTHON_CMD -m pip install --upgrade pip

# Install requirements
echo -e "${YELLOW}📦 Installing requirements...${NC}"
$PYTHON_CMD -m pip install -r requirements.txt

echo -e "${GREEN}✅ Dependencies installed successfully!${NC}"

# Final instructions
echo ""
echo -e "${PURPLE}=====================================${NC}"
echo -e "${GREEN}🎉 RedshiftManager Setup Complete!${NC}"
echo -e "${PURPLE}=====================================${NC}"
echo ""
echo -e "${CYAN}📁 Project created in: $PROJECT_DIR${NC}"
echo ""
echo -e "${YELLOW}🚀 To start the application:${NC}"
echo -e "${WHITE}   cd $PROJECT_NAME${NC}"
echo -e "${WHITE}   ./run.sh          ${NC}${BLUE}# Linux/macOS${NC}"
echo -e "${WHITE}   run.bat           ${NC}${BLUE}# Windows${NC}"
echo -e "${WHITE}   streamlit run main.py  ${NC}${BLUE}# Direct${NC}"
echo ""
echo -e "${YELLOW}🌐 Application will be available at:${NC}"
echo -e "${WHITE}   http://localhost:8501${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps to complete the setup:${NC}"
echo -e "${WHITE}   1. Add advanced model files from the conversation${NC}"
echo -e "${WHITE}   2. Complete UI pages implementation${NC}"
echo -e "${WHITE}   3. Configure your Redshift connections${NC}"
echo -e "${WHITE}   4. Test all functionality${NC}"
echo ""
echo -e "${GREEN}✨ Happy coding!${NC}"

# Automatically start if requested
read -p "🚀 Do you want to start the application now? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}🌐 Starting RedshiftManager...${NC}"
    ./run.sh
fi
EOF

echo -e "${GREEN}🎉 Setup script created successfully!${NC}"
echo ""
echo -e "${BLUE}To use this script:${NC}"
echo -e "${WHITE}1. Save it as 'setup_redshift_manager.sh'${NC}"
echo -e "${WHITE}2. chmod +x setup_redshift_manager.sh${NC}"
echo -e "${WHITE}3. ./setup_redshift_manager.sh${NC}"