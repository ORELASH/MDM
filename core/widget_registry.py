"""
Advanced Widget Registry for RedshiftManager Dashboard
Manages widget registration, discovery, and dynamic loading with open interfaces.
Supports multiple database types and external widget modules.
"""

import streamlit as st
from typing import Dict, List, Type, Optional, Any, Callable, Union
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import logging
from dataclasses import dataclass, field
from enum import Enum
import threading

from .widget_framework import (
    BaseWidget, IWidget, IDatabaseConnector, WidgetConfig, 
    WidgetType, WidgetSize, WidgetRefreshMode, DatabaseType, DatabaseConfig
)

logger = logging.getLogger(__name__)


@dataclass
class WidgetDescriptor:
    """Enhanced descriptor for registered widget types with multi-DB support"""
    name: str
    widget_class: Union[Type[BaseWidget], Type[IWidget]]
    category: str
    description: str
    icon: str
    default_config: Dict[str, Any]
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    supported_databases: List[DatabaseType] = field(default_factory=lambda: [DatabaseType.REDSHIFT])
    module_path: Optional[str] = None
    is_external: bool = False
    version: str = "1.0.0"


class WidgetCategory(Enum):
    """Widget categories for organization"""
    METRICS = "metrics"
    CHARTS = "charts"
    TABLES = "tables" 
    STATUS = "status"
    ACTIONS = "actions"
    TEXT = "text"
    CUSTOM = "custom"


class WidgetRegistry:
    """Enhanced central registry for managing widgets with multi-DB support"""
    
    def __init__(self):
        self._widgets: Dict[str, WidgetDescriptor] = {}
        self._database_connectors: Dict[DatabaseType, IDatabaseConnector] = {}
        self._widget_instances: Dict[str, IWidget] = {}
        self._registry_lock = threading.RLock()
        self._auto_discovery_enabled = True
        self._instances: Dict[str, BaseWidget] = {}
        self._layouts: Dict[str, List[str]] = {}
        self.logger = logging.getLogger("widget_registry")
        
        # Auto-discover built-in widgets
        if self._auto_discovery_enabled:
            self._discover_builtin_widgets()
    
    def register_database_connector(self, db_type: DatabaseType, connector: IDatabaseConnector) -> None:
        """Register a database connector for a specific database type"""
        with self._registry_lock:
            self._database_connectors[db_type] = connector
            self.logger.info(f"Registered database connector for {db_type.value}")
    
    def get_database_connector(self, db_type: DatabaseType) -> Optional[IDatabaseConnector]:
        """Get database connector for a specific type"""
        return self._database_connectors.get(db_type)
    
    def register_external_widget(
        self, 
        name: str,
        widget_class: Union[Type[BaseWidget], Type[IWidget]],
        category: str = "custom",
        description: str = "",
        icon: str = "🔧",
        supported_databases: List[DatabaseType] = None,
        module_path: str = None,
        **kwargs
    ) -> bool:
        """Register an external widget implementation"""
        try:
            with self._registry_lock:
                descriptor = WidgetDescriptor(
                    name=name,
                    widget_class=widget_class,
                    category=category,
                    description=description,
                    icon=icon,
                    default_config=kwargs.get('default_config', {}),
                    required_params=kwargs.get('required_params', []),
                    optional_params=kwargs.get('optional_params', []),
                    examples=kwargs.get('examples', []),
                    supported_databases=supported_databases or [DatabaseType.GENERIC],
                    module_path=module_path,
                    is_external=True,
                    version=kwargs.get('version', '1.0.0')
                )
                
                self._widgets[name] = descriptor
                self.logger.info(f"Registered external widget: {name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register external widget {name}: {e}")
            return False
    
    def create_widget_instance(
        self, 
        widget_name: str, 
        config: WidgetConfig,
        db_type: DatabaseType = DatabaseType.REDSHIFT
    ) -> Optional[IWidget]:
        """Create widget instance with appropriate database connector"""
        try:
            with self._registry_lock:
                if widget_name not in self._widgets:
                    self.logger.error(f"Widget {widget_name} not found in registry")
                    return None
                
                descriptor = self._widgets[widget_name]
                
                # Check if widget supports the requested database type
                if db_type not in descriptor.supported_databases:
                    self.logger.warning(f"Widget {widget_name} doesn't support {db_type.value}")
                
                # Get appropriate database connector
                db_connector = self.get_database_connector(db_type)
                
                # Create widget instance
                if issubclass(descriptor.widget_class, BaseWidget):
                    instance = descriptor.widget_class(config, db_connector)
                else:
                    # External IWidget implementation
                    instance = descriptor.widget_class()
                    instance.configure(config.to_dict())
                
                # Store instance for management
                instance_id = f"{widget_name}_{config.widget_id}"
                self._widget_instances[instance_id] = instance
                
                self.logger.info(f"Created widget instance: {instance_id}")
                return instance
                
        except Exception as e:
            self.logger.error(f"Failed to create widget instance {widget_name}: {e}")
            return None
    
    def get_widgets_by_database(self, db_type: DatabaseType) -> List[WidgetDescriptor]:
        """Get all widgets that support a specific database type"""
        return [
            descriptor for descriptor in self._widgets.values()
            if db_type in descriptor.supported_databases
        ]
    
    def discover_external_widgets(self, search_paths: List[str]) -> int:
        """Discover and register widgets from external modules"""
        discovered_count = 0
        
        for search_path in search_paths:
            try:
                path = Path(search_path)
                if not path.exists():
                    continue
                
                # Search for Python files
                for py_file in path.rglob("*.py"):
                    if py_file.name.startswith("_"):
                        continue
                    
                    discovered_count += self._discover_widgets_in_file(py_file)
                    
            except Exception as e:
                self.logger.error(f"Error discovering widgets in {search_path}: {e}")
        
        self.logger.info(f"Discovered {discovered_count} external widgets")
        return discovered_count
    
    def _discover_widgets_in_file(self, file_path: Path) -> int:
        """Discover widgets in a specific Python file"""
        try:
            # Dynamic import
            spec = importlib.util.spec_from_file_location("widget_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            discovered = 0
            
            # Look for widget classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, (BaseWidget, IWidget)) and 
                    obj not in (BaseWidget, IWidget)):
                    
                    # Try to register the widget
                    widget_name = getattr(obj, 'WIDGET_NAME', name.lower())
                    if self.register_external_widget(
                        name=widget_name,
                        widget_class=obj,
                        module_path=str(file_path)
                    ):
                        discovered += 1
            
            return discovered
            
        except Exception as e:
            self.logger.error(f"Error discovering widgets in {file_path}: {e}")
            return 0
    
    def list_widgets(self, category: Optional[str] = None, db_type: Optional[DatabaseType] = None) -> List[WidgetDescriptor]:
        """List all registered widgets with optional filters"""
        widgets = list(self._widgets.values())
        
        if category:
            widgets = [w for w in widgets if w.category == category]
        
        if db_type:
            widgets = [w for w in widgets if db_type in w.supported_databases]
        
        return sorted(widgets, key=lambda x: (x.category, x.name))
    
    def get_widget_descriptor(self, name: str) -> Optional[WidgetDescriptor]:
        """Get widget descriptor by name"""
        return self._widgets.get(name)
    
    def unregister_widget(self, name: str) -> bool:
        """Unregister a widget type"""
        with self._registry_lock:
            if name in self._widgets:
                del self._widgets[name]
                self.logger.info(f"Unregistered widget: {name}")
                return True
            return False
    
    def _discover_builtin_widgets(self) -> None:
        """Discover built-in widgets in the system"""
        # This will be expanded as we add more built-in widgets
        self.logger.info("Built-in widget discovery completed")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self._registry_lock:
            return {
                'total_widgets': len(self._widgets),
                'external_widgets': len([w for w in self._widgets.values() if w.is_external]),
                'database_connectors': len(self._database_connectors),
                'active_instances': len(self._widget_instances),
                'categories': list(set(w.category for w in self._widgets.values())),
                'supported_databases': list(set().union(*[w.supported_databases for w in self._widgets.values()]))
            }


# Global registry instance
widget_registry = WidgetRegistry()

# Helper functions for easy access
def register_widget(name: str, widget_class: Union[Type[BaseWidget], Type[IWidget]], **kwargs) -> bool:
    """Register a widget in the global registry"""
    return widget_registry.register_external_widget(name, widget_class, **kwargs)

def create_widget(widget_name: str, config: WidgetConfig, db_type: DatabaseType = DatabaseType.REDSHIFT) -> Optional[IWidget]:
    """Create a widget instance from the global registry"""
    return widget_registry.create_widget_instance(widget_name, config, db_type)

def get_available_widgets(db_type: DatabaseType = None) -> List[WidgetDescriptor]:
    """Get list of available widgets, optionally filtered by database type"""
    if db_type:
        return widget_registry.get_widgets_by_database(db_type)
    return list(widget_registry._widgets.values())

def register_database_connector(db_type: DatabaseType, connector: IDatabaseConnector) -> None:
    """Register a database connector globally"""
    widget_registry.register_database_connector(db_type, connector)

def get_widget_registry() -> WidgetRegistry:
    """Get the global widget registry instance"""
    return widget_registry

def get_widget_factory():
    """Get widget factory (alias for registry)"""
    return widget_registry