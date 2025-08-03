"""
Advanced Widget Framework for RedshiftManager Dashboard
Provides open interfaces and base classes for dynamic widgets.
Supports multiple database types and extensible architecture.
"""

import streamlit as st
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union, Type
from enum import Enum
import json
import uuid
from datetime import datetime
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Database type support for open interfaces
class DatabaseType(Enum):
    """Supported database types for future expansion"""
    REDSHIFT = "redshift"
    POSTGRESQL = "postgresql" 
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLITE = "sqlite"
    GENERIC = "generic"

@dataclass
class DatabaseConfig:
    """Database configuration for widgets"""
    db_type: DatabaseType
    connection_params: Dict[str, Any] = field(default_factory=dict)
    schema_info: Optional[Dict[str, Any]] = None
    query_adapter: Optional[str] = None


class WidgetType(Enum):
    """Supported widget types"""
    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"
    STATUS = "status"
    ACTION = "action"
    FORM = "form"
    TEXT = "text"
    CUSTOM = "custom"


class WidgetSize(Enum):
    """Widget sizing options"""
    SMALL = "small"      # 1/4 width
    MEDIUM = "medium"    # 1/2 width  
    LARGE = "large"      # 3/4 width
    FULL = "full"        # Full width


class WidgetRefreshMode(Enum):
    """Widget refresh behavior"""
    STATIC = "static"        # No auto refresh
    MANUAL = "manual"        # User triggered only
    AUTO = "auto"           # Auto refresh at intervals
    REALTIME = "realtime"   # Real-time updates


class WidgetConfig:
    """Widget configuration class"""
    
    def __init__(self, 
                 title: str,
                 widget_type: WidgetType,
                 size: WidgetSize = WidgetSize.MEDIUM,
                 refresh_mode: WidgetRefreshMode = WidgetRefreshMode.MANUAL,
                 refresh_interval: int = 30,
                 collapsible: bool = True,
                 custom_css: Optional[str] = None,
                 data_source: Optional[str] = None,
                 **kwargs):
        self.title = title
        self.widget_type = widget_type
        self.size = size
        self.refresh_mode = refresh_mode
        self.refresh_interval = refresh_interval
        self.collapsible = collapsible
        self.custom_css = custom_css
        self.data_source = data_source
        self.custom_params = kwargs
        
        # Auto-generated properties
        self.widget_id = str(uuid.uuid4())
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'widget_id': self.widget_id,
            'title': self.title,
            'widget_type': self.widget_type.value,
            'size': self.size.value,
            'refresh_mode': self.refresh_mode.value,
            'refresh_interval': self.refresh_interval,
            'collapsible': self.collapsible,
            'custom_css': self.custom_css,
            'data_source': self.data_source,
            'created_at': self.created_at.isoformat(),
            'custom_params': self.custom_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WidgetConfig':
        """Create config from dictionary"""
        config = cls(
            title=data['title'],
            widget_type=WidgetType(data['widget_type']),
            size=WidgetSize(data['size']),
            refresh_mode=WidgetRefreshMode(data['refresh_mode']),
            refresh_interval=data.get('refresh_interval', 30),
            collapsible=data.get('collapsible', True),
            custom_css=data.get('custom_css'),
            data_source=data.get('data_source'),
            **data.get('custom_params', {})
        )
        config.widget_id = data['widget_id']
        config.created_at = datetime.fromisoformat(data['created_at'])
        return config


# Open Interfaces for extensibility

class IWidget(ABC):
    """Open interface for all widgets - allows external implementations"""
    
    @abstractmethod
    def get_id(self) -> str:
        """Get unique widget identifier"""
        pass
    
    @abstractmethod
    def get_title(self) -> str:
        """Get widget title"""
        pass
    
    @abstractmethod
    def get_type(self) -> WidgetType:
        """Get widget type"""
        pass
    
    @abstractmethod
    def render(self, container: Any = None) -> Any:
        """Render widget in given container"""
        pass
    
    @abstractmethod
    def get_data(self, db_config: Optional[DatabaseConfig] = None) -> Dict[str, Any]:
        """Get widget data from any database type"""
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure widget with parameters"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate widget configuration and data"""
        pass

class IDatabaseConnector(ABC):
    """Open interface for database connections - supports multiple DB types"""
    
    @abstractmethod
    def connect(self, config: DatabaseConfig) -> bool:
        """Connect to database"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute query and return results"""
        pass
    
    @abstractmethod
    def get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information"""
        pass
    
    @abstractmethod
    def adapt_query(self, query: str, target_db: DatabaseType) -> str:
        """Adapt query for specific database type"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close database connection"""
        pass

class BaseWidget(IWidget):
    """Enhanced base class for all dashboard widgets with open interfaces"""
    
    def __init__(self, config: WidgetConfig, db_connector: Optional[IDatabaseConnector] = None):
        self.config = config
        self.logger = logging.getLogger(f"widget.{config.widget_id}")
        self._data_cache = {}
        self._last_refresh = None
        self.db_connector = db_connector
        self._db_config: Optional[DatabaseConfig] = None
        
    @abstractmethod
    def render_content(self) -> None:
        """Render the main widget content. Must be implemented by subclasses."""
        pass
    
    def render(self) -> None:
        """Main render method that handles the widget container and content"""
        try:
            # Apply custom CSS if provided
            if self.config.custom_css:
                st.markdown(f"<style>{self.config.custom_css}</style>", unsafe_allow_html=True)
            
            # Create widget container
            with st.container():
                self._render_header()
                
                # Render content based on collapsible setting
                if self.config.collapsible:
                    with st.expander(self.config.title, expanded=True):
                        self._render_with_error_handling()
                else:
                    st.subheader(self.config.title)
                    self._render_with_error_handling()
                
                self._render_footer()
                
        except Exception as e:
            self.logger.error(f"Error rendering widget {self.config.widget_id}: {e}")
            st.error(f"Widget Error: {e}")
    
    # IWidget interface implementation
    def get_id(self) -> str:
        """Get unique widget identifier"""
        return self.config.widget_id
    
    def get_title(self) -> str:
        """Get widget title"""
        return self.config.title
    
    def get_type(self) -> WidgetType:
        """Get widget type"""
        return self.config.widget_type
    
    def get_data(self, db_config: Optional[DatabaseConfig] = None) -> Dict[str, Any]:
        """Get widget data from any database type"""
        if db_config:
            self._db_config = db_config
        
        # Use cached data if still valid
        if self._should_use_cache():
            return self._data_cache
        
        try:
            if self.db_connector and self._db_config:
                # Connect to specified database
                if self.db_connector.connect(self._db_config):
                    data = self._fetch_data_from_db()
                    self._data_cache = data
                    self._last_refresh = datetime.now()
                    return data
            
            # Fallback to default data fetching
            data = self._fetch_default_data()
            self._data_cache = data
            self._last_refresh = datetime.now()
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching data: {e}")
            return {"error": str(e)}
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure widget with parameters"""
        try:
            # Update widget config
            for key, value in config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Apply database configuration if provided
            if 'database' in config:
                db_info = config['database']
                self._db_config = DatabaseConfig(
                    db_type=DatabaseType(db_info.get('type', 'redshift')),
                    connection_params=db_info.get('params', {}),
                    schema_info=db_info.get('schema'),
                    query_adapter=db_info.get('adapter')
                )
            
            self.logger.info(f"Widget {self.get_id()} configured successfully")
            
        except Exception as e:
            self.logger.error(f"Error configuring widget: {e}")
            raise
    
    def validate(self) -> bool:
        """Validate widget configuration and data"""
        try:
            # Basic validation
            if not self.config.title:
                return False
            
            if not self.config.widget_id:
                return False
            
            # Database validation if configured
            if self._db_config and self.db_connector:
                return self.db_connector.connect(self._db_config)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
    
    # Helper methods for database integration
    def _should_use_cache(self) -> bool:
        """Check if cached data is still valid"""
        if not self._data_cache or not self._last_refresh:
            return False
        
        if self.config.refresh_mode == WidgetRefreshMode.STATIC:
            return True
        
        elapsed = (datetime.now() - self._last_refresh).total_seconds()
        return elapsed < self.config.refresh_interval
    
    def _fetch_data_from_db(self) -> Dict[str, Any]:
        """Fetch data using database connector - to be overridden"""
        if not self.db_connector:
            return {}
        
        # Default implementation - subclasses should override
        try:
            query = self._get_widget_query()
            if query:
                return self.db_connector.execute_query(query)
            return {}
        except Exception as e:
            self.logger.error(f"Error fetching data from database: {e}")
            return {"error": str(e)}
    
    def _fetch_default_data(self) -> Dict[str, Any]:
        """Fetch default data - to be overridden by subclasses"""
        return {"message": "No data available"}
    
    def _get_widget_query(self) -> Optional[str]:
        """Get SQL query for this widget - to be overridden"""
        return None
    
    def set_database_connector(self, connector: IDatabaseConnector) -> None:
        """Set database connector for this widget"""
        self.db_connector = connector
    
    def refresh_data(self) -> None:
        """Force refresh widget data"""
        self._data_cache = {}
        self._last_refresh = None
        self.get_data()
    
    def _render_header(self) -> None:
        """Render widget header with controls"""
        if self.config.refresh_mode in [WidgetRefreshMode.MANUAL, WidgetRefreshMode.AUTO]:
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("🔄", key=f"refresh_{self.config.widget_id}", help="Refresh widget"):
                    self.refresh_data()
    
    def _render_footer(self) -> None:
        """Render widget footer with metadata"""
        if self._last_refresh:
            st.caption(f"Last updated: {self._last_refresh.strftime('%H:%M:%S')}")
    
    def _render_with_error_handling(self) -> None:
        """Render content with error handling"""
        try:
            self.render_content()
        except Exception as e:
            self.logger.error(f"Error in widget content: {e}")
            st.error(f"Failed to render widget content: {e}")
    
    def refresh_data(self) -> None:
        """Refresh widget data - can be overridden by subclasses"""
        self._last_refresh = datetime.now()
        self.logger.info(f"Widget {self.config.widget_id} data refreshed")
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get cached data by key"""
        return self._data_cache.get(key, default)
    
    def set_data(self, key: str, value: Any) -> None:
        """Set cached data by key"""
        self._data_cache[key] = value
    
    def clear_cache(self) -> None:
        """Clear data cache"""
        self._data_cache.clear()
    
    @property
    def widget_id(self) -> str:
        """Get widget ID"""
        return self.config.widget_id
    
    @property
    def title(self) -> str:
        """Get widget title"""
        return self.config.title


class MetricWidget(BaseWidget):
    """Widget for displaying metrics"""
    
    def __init__(self, config: WidgetConfig, 
                 value: Any = 0, 
                 delta: Optional[Any] = None,
                 value_formatter: Optional[Callable] = None):
        super().__init__(config)
        self.value = value
        self.delta = delta
        self.value_formatter = value_formatter or str
    
    def render_content(self) -> None:
        """Render metric content"""
        formatted_value = self.value_formatter(self.value)
        st.metric(
            label="",
            value=formatted_value,
            delta=self.delta
        )
    
    def update_value(self, value: Any, delta: Optional[Any] = None) -> None:
        """Update metric value"""
        self.value = value
        self.delta = delta
        self.refresh_data()


class ChartWidget(BaseWidget):
    """Widget for displaying charts"""
    
    def __init__(self, config: WidgetConfig, 
                 chart_type: str = "line",
                 data: Optional[Any] = None):
        super().__init__(config)
        self.chart_type = chart_type
        self.chart_data = data if data is not None else []
    
    def render_content(self) -> None:
        """Render chart content"""
        if self.chart_data is None or (hasattr(self.chart_data, 'empty') and self.chart_data.empty):
            st.info("No data available for chart")
            return
        
        if self.chart_type == "line":
            st.line_chart(self.chart_data)
        elif self.chart_type == "bar":
            st.bar_chart(self.chart_data)
        elif self.chart_type == "area":
            st.area_chart(self.chart_data)
        else:
            st.info(f"Chart type '{self.chart_type}' not supported")
    
    def update_data(self, data: Any) -> None:
        """Update chart data"""
        self.chart_data = data
        self.refresh_data()


class TableWidget(BaseWidget):
    """Widget for displaying tables"""
    
    def __init__(self, config: WidgetConfig, 
                 data: Optional[Any] = None,
                 columns: Optional[List[str]] = None):
        super().__init__(config)
        self.table_data = data if data is not None else []
        self.columns = columns
    
    def render_content(self) -> None:
        """Render table content"""
        if self.table_data is None or (hasattr(self.table_data, 'empty') and self.table_data.empty):
            st.info("No data available for table")
            return
        
        if self.columns:
            # Display specific columns only
            st.dataframe(self.table_data[self.columns])
        else:
            st.dataframe(self.table_data)
    
    def update_data(self, data: Any, columns: Optional[List[str]] = None) -> None:
        """Update table data"""
        self.table_data = data
        if columns:
            self.columns = columns
        self.refresh_data()


class StatusWidget(BaseWidget):
    """Widget for displaying status information"""
    
    def __init__(self, config: WidgetConfig, 
                 status: str = "Unknown",
                 status_color: str = "gray",
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.status = status
        self.status_color = status_color
        self.details = details or {}
    
    def render_content(self) -> None:
        """Render status content"""
        # Status indicator
        status_colors = {
            "green": "🟢",
            "red": "🔴", 
            "yellow": "🟡",
            "blue": "🔵",
            "gray": "⚪"
        }
        
        icon = status_colors.get(self.status_color.lower(), "⚪")
        st.markdown(f"### {icon} {self.status}")
        
        # Show details if available
        if self.details:
            for key, value in self.details.items():
                st.text(f"{key}: {value}")
    
    def update_status(self, status: str, color: str = "gray", details: Optional[Dict[str, Any]] = None) -> None:
        """Update status"""
        self.status = status
        self.status_color = color
        if details:
            self.details = details
        self.refresh_data()


class ActionWidget(BaseWidget):
    """Widget for action buttons and controls"""
    
    def __init__(self, config: WidgetConfig, 
                 actions: Optional[List[Dict[str, Any]]] = None):
        super().__init__(config)
        self.actions = actions or []
    
    def render_content(self) -> None:
        """Render action buttons"""
        if not self.actions:
            st.info("No actions configured")
            return
        
        # Create columns for actions
        if len(self.actions) <= 3:
            cols = st.columns(len(self.actions))
        else:
            # Multiple rows for many actions
            cols = st.columns(3)
        
        for i, action in enumerate(self.actions):
            col_index = i % len(cols)
            with cols[col_index]:
                button_key = f"action_{self.config.widget_id}_{i}"
                if st.button(action.get('label', f'Action {i+1}'), key=button_key):
                    self._execute_action(action)
    
    def _execute_action(self, action: Dict[str, Any]) -> None:
        """Execute an action"""
        try:
            action_type = action.get('type', 'callback')
            
            if action_type == 'callback' and 'callback' in action:
                action['callback']()
            elif action_type == 'message':
                st.success(action.get('message', 'Action executed'))
            else:
                st.info(f"Action type '{action_type}' not implemented")
                
            self.logger.info(f"Action executed: {action.get('label', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error executing action: {e}")
            st.error(f"Action failed: {e}")
    
    def add_action(self, label: str, callback: Optional[Callable] = None, 
                  action_type: str = "callback", **kwargs) -> None:
        """Add new action"""
        action = {
            'label': label,
            'type': action_type,
            'callback': callback,
            **kwargs
        }
        self.actions.append(action)


class TextWidget(BaseWidget):
    """Widget for displaying text content"""
    
    def __init__(self, config: WidgetConfig, 
                 content: str = "",
                 markdown: bool = True):
        super().__init__(config)
        self.content = content
        self.markdown = markdown
    
    def render_content(self) -> None:
        """Render text content"""
        if self.markdown:
            st.markdown(self.content)
        else:
            st.text(self.content)
    
    def update_content(self, content: str) -> None:
        """Update text content"""
        self.content = content
        self.refresh_data()


# Factory function for creating widgets
def create_widget(widget_type: WidgetType, config: WidgetConfig, **kwargs) -> BaseWidget:
    """Factory function to create widgets"""
    
    widget_classes = {
        WidgetType.METRIC: MetricWidget,
        WidgetType.CHART: ChartWidget,
        WidgetType.TABLE: TableWidget,
        WidgetType.STATUS: StatusWidget,
        WidgetType.ACTION: ActionWidget,
        WidgetType.TEXT: TextWidget,
    }
    
    widget_class = widget_classes.get(widget_type)
    if not widget_class:
        raise ValueError(f"Unsupported widget type: {widget_type}")
    
    return widget_class(config, **kwargs)


# Widget utilities
class WidgetUtils:
    """Utility functions for widgets"""
    
    @staticmethod
    def get_column_config(size: WidgetSize) -> int:
        """Get column width for widget size"""
        size_mapping = {
            WidgetSize.SMALL: 1,
            WidgetSize.MEDIUM: 2,
            WidgetSize.LARGE: 3,
            WidgetSize.FULL: 4
        }
        return size_mapping.get(size, 2)
    
    @staticmethod
    def format_number(value: float, precision: int = 2) -> str:
        """Format numbers for display"""
        if value >= 1_000_000:
            return f"{value/1_000_000:.{precision}f}M"
        elif value >= 1_000:
            return f"{value/1_000:.{precision}f}K"
        else:
            return f"{value:.{precision}f}"
    
    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """Format byte values"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"


if __name__ == "__main__":
    # Example usage
    config = WidgetConfig(
        title="Sample Metric",
        widget_type=WidgetType.METRIC,
        size=WidgetSize.MEDIUM
    )
    
    widget = MetricWidget(config, value=42, delta=5)
    print(f"Created widget: {widget.title} ({widget.widget_id})")