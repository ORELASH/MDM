"""
Widget Management API Router
Comprehensive widget management endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.widget_registry import WidgetRegistry
from utils.user_preferences import UserPreferencesManager
from utils.logging_system import RedshiftLogger
from api.dependencies import get_current_api_user, require_role
from utils.auth_manager import UserRole

router = APIRouter(prefix="/widgets", tags=["widgets"])
logger = RedshiftLogger()

# Pydantic models
class WidgetInfo(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    enabled: bool
    config: Dict[str, Any] = {}

class WidgetConfig(BaseModel):
    widget_name: str
    config: Dict[str, Any]
    enabled: bool = True

class UserWidgetPreferences(BaseModel):
    enabled_widgets: List[str]
    widget_order: List[str]
    widget_configs: Dict[str, Dict[str, Any]]

@router.get("/", response_model=List[WidgetInfo])
async def get_available_widgets(current_user: dict = Depends(get_current_api_user)):
    """
    Get all available widgets
    """
    try:
        registry = WidgetRegistry()
        widgets = []
        
        for widget_name, widget_class in registry.widgets.items():
            widget_info = WidgetInfo(
                name=widget_name,
                display_name=getattr(widget_class, 'display_name', widget_name.replace('_', ' ').title()),
                description=getattr(widget_class, 'description', 'No description available'),
                category=getattr(widget_class, 'category', 'general'),
                enabled=True,
                config=getattr(widget_class, 'default_config', {})
            )
            widgets.append(widget_info)
        
        logger.log_action_end(f"Widget list retrieved by {current_user['username']}")
        return widgets
        
    except Exception as e:
        logger.log_error(f"Failed to get widgets: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve widgets")

@router.get("/user-preferences", response_model=UserWidgetPreferences)
async def get_user_widget_preferences(current_user: dict = Depends(get_current_api_user)):
    """
    Get current user's widget preferences
    """
    try:
        prefs_manager = UserPreferencesManager()
        user_prefs = prefs_manager.get_user_preferences(current_user['username'])
        
        widget_prefs = UserWidgetPreferences(
            enabled_widgets=user_prefs.get('enabled_widgets', []),
            widget_order=user_prefs.get('widget_order', []),
            widget_configs=user_prefs.get('widget_configs', {})
        )
        
        logger.log_action_end(f"Widget preferences retrieved for {current_user['username']}")
        return widget_prefs
        
    except Exception as e:
        logger.log_error(f"Failed to get widget preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve widget preferences")

@router.post("/user-preferences")
async def update_user_widget_preferences(
    preferences: UserWidgetPreferences,
    current_user: dict = Depends(get_current_api_user)
):
    """
    Update current user's widget preferences
    """
    try:
        prefs_manager = UserPreferencesManager()
        
        # Update preferences
        success = prefs_manager.update_preferences(current_user['username'], {
            'enabled_widgets': preferences.enabled_widgets,
            'widget_order': preferences.widget_order,
            'widget_configs': preferences.widget_configs
        })
        
        if success:
            logger.log_action_end(f"Widget preferences updated for {current_user['username']}")
            return {"success": True, "message": "Widget preferences updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update preferences")
        
    except Exception as e:
        logger.log_error(f"Failed to update widget preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update widget preferences")

@router.post("/register")
async def register_external_widget(
    widget_data: Dict[str, Any],
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """
    Register an external widget (admin only)
    """
    try:
        registry = WidgetRegistry()
        
        widget_name = widget_data.get('name')
        widget_class_path = widget_data.get('class_path')
        
        if not widget_name or not widget_class_path:
            raise HTTPException(status_code=400, detail="Widget name and class_path are required")
        
        # Register the widget
        success = registry.register_external_widget(widget_name, widget_class_path)
        
        if success:
            logger.log_action_end(f"External widget '{widget_name}' registered by {current_user['username']}")
            return {"success": True, "message": f"Widget '{widget_name}' registered successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to register widget")
        
    except Exception as e:
        logger.log_error(f"Failed to register widget: {e}")
        raise HTTPException(status_code=500, detail="Failed to register widget")

@router.get("/{widget_name}/config")
async def get_widget_config(
    widget_name: str,
    current_user: dict = Depends(get_current_api_user)
):
    """
    Get configuration for a specific widget
    """
    try:
        registry = WidgetRegistry()
        
        if widget_name not in registry.widgets:
            raise HTTPException(status_code=404, detail="Widget not found")
        
        widget_class = registry.widgets[widget_name]
        config = getattr(widget_class, 'default_config', {})
        
        # Get user-specific config if available
        prefs_manager = UserPreferencesManager()
        user_prefs = prefs_manager.get_user_preferences(current_user['username'])
        user_config = user_prefs.get('widget_configs', {}).get(widget_name, {})
        
        # Merge default and user config
        merged_config = {**config, **user_config}
        
        return {
            "widget_name": widget_name,
            "default_config": config,
            "user_config": user_config,
            "merged_config": merged_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(f"Failed to get widget config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve widget configuration")

@router.post("/{widget_name}/config")
async def update_widget_config(
    widget_name: str,
    config: WidgetConfig,
    current_user: dict = Depends(get_current_api_user)
):
    """
    Update configuration for a specific widget
    """
    try:
        registry = WidgetRegistry()
        
        if widget_name not in registry.widgets:
            raise HTTPException(status_code=404, detail="Widget not found")
        
        # Update user preferences
        prefs_manager = UserPreferencesManager()
        user_prefs = prefs_manager.get_user_preferences(current_user['username'])
        
        if 'widget_configs' not in user_prefs:
            user_prefs['widget_configs'] = {}
        
        user_prefs['widget_configs'][widget_name] = config.config
        
        success = prefs_manager.update_preferences(current_user['username'], user_prefs)
        
        if success:
            logger.log_action_end(f"Widget config updated for {widget_name} by {current_user['username']}")
            return {"success": True, "message": f"Configuration updated for widget '{widget_name}'"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update widget configuration")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(f"Failed to update widget config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update widget configuration")

@router.delete("/{widget_name}")
async def unregister_widget(
    widget_name: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """
    Unregister a widget (admin only)
    """
    try:
        registry = WidgetRegistry()
        
        if widget_name not in registry.widgets:
            raise HTTPException(status_code=404, detail="Widget not found")
        
        # Remove widget from registry
        del registry.widgets[widget_name]
        
        logger.log_action_end(f"Widget '{widget_name}' unregistered by {current_user['username']}")
        return {"success": True, "message": f"Widget '{widget_name}' unregistered successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(f"Failed to unregister widget: {e}")
        raise HTTPException(status_code=500, detail="Failed to unregister widget")