"""
User Preferences Manager
Manages user dashboard layouts, widget configurations, and settings.
Supports both session-based and persistent storage.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserPreferencesManager:
    """Manages user preferences and dashboard layouts"""
    
    def __init__(self, preferences_dir: str = "data/user_preferences"):
        self.preferences_dir = Path(preferences_dir)
        self.preferences_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("user_preferences")
    
    def get_user_preferences_file(self, user_id: str = "default") -> Path:
        """Get path to user preferences file"""
        return self.preferences_dir / f"{user_id}_preferences.json"
    
    def load_user_preferences(self, user_id: str = "default") -> Dict[str, Any]:
        """Load user preferences from file"""
        try:
            preferences_file = self.get_user_preferences_file(user_id)
            
            if preferences_file.exists():
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    preferences = json.load(f)
                    self.logger.info(f"Loaded preferences for user {user_id}")
                    return preferences
            else:
                # Return default preferences
                return self._get_default_preferences()
                
        except Exception as e:
            self.logger.error(f"Error loading preferences for user {user_id}: {e}")
            return self._get_default_preferences()
    
    def save_user_preferences(self, preferences: Dict[str, Any], user_id: str = "default") -> bool:
        """Save user preferences to file"""
        try:
            preferences_file = self.get_user_preferences_file(user_id)
            
            # Add timestamp
            preferences['last_updated'] = datetime.now().isoformat()
            
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Saved preferences for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving preferences for user {user_id}: {e}")
            return False
    
    def get_dashboard_layout(self, user_id: str = "default") -> List[Dict[str, Any]]:
        """Get user's dashboard widget layout"""
        preferences = self.load_user_preferences(user_id)
        return preferences.get('dashboard_layout', self._get_default_widgets())
    
    def save_dashboard_layout(self, layout: List[Dict[str, Any]], user_id: str = "default") -> bool:
        """Save user's dashboard widget layout"""
        preferences = self.load_user_preferences(user_id)
        preferences['dashboard_layout'] = layout
        return self.save_user_preferences(preferences, user_id)
    
    def add_widget_to_layout(self, widget_config: Dict[str, Any], user_id: str = "default") -> bool:
        """Add widget to user's layout"""
        layout = self.get_dashboard_layout(user_id)
        layout.append(widget_config)
        return self.save_dashboard_layout(layout, user_id)
    
    def remove_widget_from_layout(self, widget_name: str, user_id: str = "default") -> bool:
        """Remove widget from user's layout"""
        layout = self.get_dashboard_layout(user_id)
        layout = [w for w in layout if w.get('name') != widget_name]
        return self.save_dashboard_layout(layout, user_id)
    
    def update_widget_position(self, widget_name: str, position: Dict[str, int], user_id: str = "default") -> bool:
        """Update widget position in layout"""
        layout = self.get_dashboard_layout(user_id)
        
        for widget in layout:
            if widget.get('name') == widget_name:
                widget['position'] = position
                break
        
        return self.save_dashboard_layout(layout, user_id)
    
    def get_database_preference(self, user_id: str = "default") -> str:
        """Get user's preferred database type"""
        preferences = self.load_user_preferences(user_id)
        return preferences.get('preferred_database', 'redshift')
    
    def set_database_preference(self, db_type: str, user_id: str = "default") -> bool:
        """Set user's preferred database type"""
        preferences = self.load_user_preferences(user_id)
        preferences['preferred_database'] = db_type
        return self.save_user_preferences(preferences, user_id)
    
    def get_theme_preference(self, user_id: str = "default") -> str:
        """Get user's theme preference"""
        preferences = self.load_user_preferences(user_id)
        return preferences.get('theme', 'light')
    
    def set_theme_preference(self, theme: str, user_id: str = "default") -> bool:
        """Set user's theme preference"""
        preferences = self.load_user_preferences(user_id)
        preferences['theme'] = theme
        return self.save_user_preferences(preferences, user_id)
    
    def get_language_preference(self, user_id: str = "default") -> str:
        """Get user's language preference"""
        preferences = self.load_user_preferences(user_id)
        return preferences.get('language', 'en')
    
    def set_language_preference(self, language: str, user_id: str = "default") -> bool:
        """Set user's language preference"""
        preferences = self.load_user_preferences(user_id)
        preferences['language'] = language
        return self.save_user_preferences(preferences, user_id)
    
    def export_preferences(self, user_id: str = "default") -> Dict[str, Any]:
        """Export user preferences for backup"""
        preferences = self.load_user_preferences(user_id)
        preferences['export_timestamp'] = datetime.now().isoformat()
        preferences['export_version'] = "1.0"
        return preferences
    
    def import_preferences(self, preferences: Dict[str, Any], user_id: str = "default") -> bool:
        """Import user preferences from backup"""
        try:
            # Validate preferences structure
            if not isinstance(preferences, dict):
                raise ValueError("Invalid preferences format")
            
            # Remove export metadata
            preferences.pop('export_timestamp', None)
            preferences.pop('export_version', None)
            
            return self.save_user_preferences(preferences, user_id)
            
        except Exception as e:
            self.logger.error(f"Error importing preferences: {e}")
            return False
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences"""
        return {
            'dashboard_layout': self._get_default_widgets(),
            'preferred_database': 'redshift',
            'theme': 'light',
            'language': 'en',
            'auto_refresh': True,
            'refresh_interval': 30,
            'show_tooltips': True,
            'compact_mode': False,
            'created_at': datetime.now().isoformat()
        }
    
    def _get_default_widgets(self) -> List[Dict[str, Any]]:
        """Get default widget configuration"""
        return [
            {
                'name': 'cluster_status',
                'title': 'Cluster Status',
                'type': 'status',
                'size': 'medium',
                'position': {'row': 0, 'col': 0},
                'enabled': True
            },
            {
                'name': 'query_performance',
                'title': 'Query Performance',
                'type': 'chart',
                'size': 'large',
                'position': {'row': 0, 'col': 1},
                'enabled': True
            },
            {
                'name': 'storage_usage',
                'title': 'Storage Usage',
                'type': 'metric',
                'size': 'small',
                'position': {'row': 1, 'col': 0},
                'enabled': True
            }
        ]
    
    def reset_to_defaults(self, user_id: str = "default") -> bool:
        """Reset user preferences to default values"""
        try:
            defaults = self._get_default_preferences()
            return self.save_user_preferences(defaults, user_id)
        except Exception as e:
            self.logger.error(f"Error resetting preferences to defaults: {e}")
            return False
    
    def get_all_user_ids(self) -> List[str]:
        """Get list of all user IDs with saved preferences"""
        try:
            user_ids = []
            for file_path in self.preferences_dir.glob("*_preferences.json"):
                user_id = file_path.stem.replace('_preferences', '')
                user_ids.append(user_id)
            return sorted(user_ids)
        except Exception as e:
            self.logger.error(f"Error getting user IDs: {e}")
            return []

# Global preferences manager instance
preferences_manager = UserPreferencesManager()

# Helper functions
def get_user_dashboard_layout(user_id: str = "default") -> List[Dict[str, Any]]:
    """Get user's dashboard layout"""
    return preferences_manager.get_dashboard_layout(user_id)

def save_user_dashboard_layout(layout: List[Dict[str, Any]], user_id: str = "default") -> bool:
    """Save user's dashboard layout"""
    return preferences_manager.save_dashboard_layout(layout, user_id)

def get_user_database_preference(user_id: str = "default") -> str:
    """Get user's preferred database"""
    return preferences_manager.get_database_preference(user_id)

def save_user_database_preference(db_type: str, user_id: str = "default") -> bool:
    """Save user's database preference"""
    return preferences_manager.set_database_preference(db_type, user_id)