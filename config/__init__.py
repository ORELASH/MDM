# RedshiftManager Config Package
"""
Configuration management for RedshiftManager.
"""

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
        }
    }

# Load settings on import
APP_SETTINGS = load_app_settings()

__all__ = ['APP_SETTINGS', 'load_app_settings']