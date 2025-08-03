#!/usr/bin/env python3
"""
RedshiftManager Main Dashboard Launcher
Entry point for the reorganized RedshiftManager system
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import from the reorganized structure
from ui.open_dashboard import main

if __name__ == "__main__":
    print("🚀 Starting RedshiftManager Dashboard...")
    print("📁 Using reorganized file structure")
    main()