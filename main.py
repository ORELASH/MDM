#!/usr/bin/env python3
"""
MultiDBManager Main Application Launcher
Universal multi-database management tool supporting PostgreSQL, MySQL, Redis, and more.
"""

import sys
from pathlib import Path
from database.database_manager import get_database_manager

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def main():
    """Main application entry point with clean structure"""
    print("🚀 Starting MultiDBManager...")
    print("📁 Universal multi-database management tool")
    
    try:
        # Import and run the main dashboard from the new location
        from ui.open_dashboard import main as dashboard_main
        dashboard_main()
    except ImportError as e:
        print(f"❌ Failed to import dashboard: {e}")
        print("🔧 Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()