"""
RedshiftManager Enhanced Dashboard v2
Enhanced dashboard with dynamic widget framework integration.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import sys
from pathlib import Path

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import widget framework
try:
    from core.widget_framework import (
        WidgetConfig, WidgetType, WidgetSize, WidgetRefreshMode,
        BaseWidget, MetricWidget, ChartWidget, TableWidget, 
        StatusWidget, ActionWidget, TextWidget
    )
    from core.widget_registry import get_widget_registry, get_widget_factory
except ImportError as e:
    st.error(f"Failed to import widget framework: {e}")
    st.stop()

# Import our core components
try:
    from utils.i18n_helper import get_text, apply_rtl_css
    from models.database_models import get_database_manager
except ImportError as e:
    # Fallback for missing components
    def get_text(key, default):
        return default
    def apply_rtl_css():
        pass


logger = logging.getLogger(__name__)


class DashboardManager:
    """Manages dashboard widgets and layouts"""
    
    def __init__(self):
        self.registry = get_widget_registry()
        self.factory = get_widget_factory()
        self.widgets: Dict[str, BaseWidget] = {}
        self.current_layout = "default"
        
        # Initialize session state for widgets
        if 'dashboard_widgets' not in st.session_state:
            st.session_state.dashboard_widgets = {}
        if 'dashboard_layout' not in st.session_state:
            st.session_state.dashboard_layout = "default"
    
    def create_default_widgets(self) -> None:
        """Create default dashboard widgets"""
        
        # System status widget
        status_config = WidgetConfig(
            title="System Status",
            widget_type=WidgetType.STATUS,
            size=WidgetSize.MEDIUM,
            refresh_mode=WidgetRefreshMode.AUTO,
            refresh_interval=30
        )
        status_widget = self.registry.create_widget(
            'status', 
            status_config,
            status="Online",
            status_color="green",
            details={"uptime": "99.9%", "version": "2.0.0"}
        )
        if status_widget:
            self.widgets["system_status"] = status_widget
        
        # Cluster metrics widget
        cluster_config = WidgetConfig(
            title="Active Clusters",
            widget_type=WidgetType.METRIC,
            size=WidgetSize.SMALL,
            refresh_mode=WidgetRefreshMode.MANUAL
        )
        cluster_widget = self.registry.create_widget(
            'metric',
            cluster_config,
            value=self._get_cluster_count(),
            delta=0
        )
        if cluster_widget:
            self.widgets["cluster_count"] = cluster_widget
        
        # User metrics widget
        user_config = WidgetConfig(
            title="Total Users",
            widget_type=WidgetType.METRIC,
            size=WidgetSize.SMALL,
            refresh_mode=WidgetRefreshMode.MANUAL
        )
        user_widget = self.registry.create_widget(
            'metric',
            user_config,
            value=self._get_user_count(),
            delta=0
        )
        if user_widget:
            self.widgets["user_count"] = user_widget
        
        # Recent queries chart
        chart_config = WidgetConfig(
            title="Query Activity (24h)",
            widget_type=WidgetType.CHART,
            size=WidgetSize.LARGE,
            refresh_mode=WidgetRefreshMode.AUTO,
            refresh_interval=60
        )
        chart_data = self._get_query_activity_data()
        chart_widget = self.registry.create_widget(
            'chart',
            chart_config,
            chart_type="line",
            data=chart_data
        )
        if chart_widget:
            self.widgets["query_activity"] = chart_widget
        
        # Recent activity table
        table_config = WidgetConfig(
            title="Recent Activity",
            widget_type=WidgetType.TABLE,
            size=WidgetSize.FULL,
            refresh_mode=WidgetRefreshMode.MANUAL
        )
        table_data = self._get_recent_activity_data()
        table_widget = self.registry.create_widget(
            'table',
            table_config,
            data=table_data,
            columns=['time', 'activity', 'user', 'status']
        )
        if table_widget:
            self.widgets["recent_activity"] = table_widget
        
        # Quick actions widget
        actions_config = WidgetConfig(
            title="Quick Actions",
            widget_type=WidgetType.ACTION,
            size=WidgetSize.MEDIUM,
            refresh_mode=WidgetRefreshMode.STATIC
        )
        actions_widget = self.registry.create_widget(
            'action',
            actions_config,
            actions=[
                {
                    'label': '🔄 Refresh Data',
                    'type': 'callback',
                    'callback': self._refresh_all_data
                },
                {
                    'label': '📊 Generate Report',
                    'type': 'message',
                    'message': 'Report generation started...'
                },
                {
                    'label': '🧹 System Cleanup',
                    'type': 'message',
                    'message': 'System cleanup initiated...'
                }
            ]
        )
        if actions_widget:
            self.widgets["quick_actions"] = actions_widget
    
    def render_dashboard(self) -> None:
        """Render the complete dashboard"""
        
        # Dashboard header
        self._render_header()
        
        # Widget management controls
        self._render_widget_controls()
        
        # Main dashboard content
        self._render_dashboard_content()
        
        # Dashboard footer
        self._render_footer()
    
    def _render_header(self) -> None:
        """Render dashboard header"""
        st.title("📊 Enhanced Dashboard v2.0")
        st.markdown("### Dynamic Widget Framework")
        st.markdown("---")
        
        # Quick metrics bar
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("System", "Online", "✅ Healthy")
        
        with col2:
            st.metric("Widgets", str(len(self.widgets)), f"+{len(self.widgets)}")
        
        with col3:
            st.metric("Registry", f"{len(self.registry.list_widgets())}", "Available")
        
        with col4:
            current_time = datetime.now().strftime("%H:%M:%S")
            st.metric("Time", current_time, "🕐 Live")
    
    def _render_widget_controls(self) -> None:
        """Render widget management controls"""
        
        with st.expander("🔧 Widget Management", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("Add Widget")
                widget_types = [w.name for w in self.registry.list_widgets()]
                selected_type = st.selectbox("Widget Type", widget_types)
                widget_title = st.text_input("Widget Title", value=f"New {selected_type.title()}")
                
                if st.button("Add Widget"):
                    self._add_new_widget(selected_type, widget_title)
            
            with col2:
                st.subheader("Layout")
                layouts = ["default", "minimal", "detailed", "custom"]
                selected_layout = st.selectbox("Layout", layouts, index=0)
                
                if st.button("Apply Layout"):
                    self.current_layout = selected_layout
                    st.success(f"Applied {selected_layout} layout")
            
            with col3:
                st.subheader("Actions")
                if st.button("Refresh All"):
                    self._refresh_all_widgets()
                    st.success("All widgets refreshed")
                
                if st.button("Reset Dashboard"):
                    self._reset_dashboard()
                    st.success("Dashboard reset to defaults")
    
    def _render_dashboard_content(self) -> None:
        """Render main dashboard content with widgets"""
        
        if not self.widgets:
            self.create_default_widgets()
        
        st.markdown("---")
        
        # Render widgets based on layout
        if self.current_layout == "default":
            self._render_default_layout()
        elif self.current_layout == "minimal":
            self._render_minimal_layout()
        elif self.current_layout == "detailed":
            self._render_detailed_layout()
        else:
            self._render_custom_layout()
    
    def _render_default_layout(self) -> None:
        """Render default widget layout"""
        
        # Top row - Status and metrics
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if "system_status" in self.widgets:
                self.widgets["system_status"].render()
        
        with col2:
            if "cluster_count" in self.widgets:
                self.widgets["cluster_count"].render()
        
        with col3:
            if "user_count" in self.widgets:
                self.widgets["user_count"].render()
        
        # Second row - Chart and actions
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if "query_activity" in self.widgets:
                self.widgets["query_activity"].render()
        
        with col2:
            if "quick_actions" in self.widgets:
                self.widgets["quick_actions"].render()
        
        # Bottom row - Full width table
        if "recent_activity" in self.widgets:
            self.widgets["recent_activity"].render()
    
    def _render_minimal_layout(self) -> None:
        """Render minimal layout with essential widgets only"""
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if "system_status" in self.widgets:
                self.widgets["system_status"].render()
        
        with col2:
            if "cluster_count" in self.widgets:
                self.widgets["cluster_count"].render()
        
        with col3:
            if "user_count" in self.widgets:
                self.widgets["user_count"].render()
    
    def _render_detailed_layout(self) -> None:
        """Render detailed layout with all widgets"""
        
        # All widgets in grid layout
        widget_keys = list(self.widgets.keys())
        
        # Create grid based on number of widgets
        if len(widget_keys) <= 2:
            cols = st.columns(len(widget_keys))
        elif len(widget_keys) <= 4:
            cols = st.columns(2)
        else:
            cols = st.columns(3)
        
        for i, widget_key in enumerate(widget_keys):
            col_index = i % len(cols)
            with cols[col_index]:
                self.widgets[widget_key].render()
    
    def _render_custom_layout(self) -> None:
        """Render custom user-defined layout"""
        # For now, same as default
        self._render_default_layout()
        
        st.info("Custom layout coming soon! You can drag and drop widgets to customize.")
    
    def _render_footer(self) -> None:
        """Render dashboard footer"""
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.caption(f"Dashboard v2.0 | Widgets: {len(self.widgets)}")
        
        with col2:
            st.caption(f"Layout: {self.current_layout.title()}")
        
        with col3:
            st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    def _add_new_widget(self, widget_type: str, title: str) -> None:
        """Add new widget to dashboard"""
        
        config = WidgetConfig(
            title=title,
            widget_type=WidgetType.CUSTOM,
            size=WidgetSize.MEDIUM
        )
        
        # Create widget with defaults based on type
        if widget_type == "metric":
            widget = self.registry.create_widget(widget_type, config, value=0, delta=0)
        elif widget_type == "status":
            widget = self.registry.create_widget(widget_type, config, status="Ready", status_color="blue")
        elif widget_type == "chart":
            widget = self.registry.create_widget(widget_type, config, chart_type="line", data=[])
        elif widget_type == "table":
            widget = self.registry.create_widget(widget_type, config, data=[], columns=[])
        elif widget_type == "text":
            widget = self.registry.create_widget(widget_type, config, content="New text widget", markdown=True)
        else:
            widget = self.registry.create_widget(widget_type, config)
        
        if widget:
            widget_key = f"custom_{len(self.widgets)}_{widget_type}"
            self.widgets[widget_key] = widget
            st.success(f"Added {title} widget")
    
    def _refresh_all_widgets(self) -> None:
        """Refresh all widgets"""
        for widget in self.widgets.values():
            widget.refresh_data()
    
    def _refresh_all_data(self) -> None:
        """Callback for refresh all data action"""
        self._refresh_all_widgets()
        st.success("All data refreshed successfully!")
    
    def _reset_dashboard(self) -> None:
        """Reset dashboard to default state"""
        self.widgets.clear()
        self.create_default_widgets()
    
    # Data helper methods
    def _get_cluster_count(self) -> int:
        """Get cluster count"""
        try:
            # This would connect to actual database
            return 0  # Placeholder
        except Exception:
            return 0
    
    def _get_user_count(self) -> int:
        """Get user count"""
        try:
            # This would connect to actual database
            return 0  # Placeholder
        except Exception:
            return 0
    
    def _get_query_activity_data(self) -> List[Dict[str, Any]]:
        """Get query activity chart data"""
        # Generate sample data for demo
        hours = list(range(24))
        queries = [max(0, int(10 * (1 + 0.5 * ((h - 12) ** 2) / 144))) for h in hours]
        
        return pd.DataFrame({
            'Hour': hours,
            'Queries': queries
        })
    
    def _get_recent_activity_data(self) -> pd.DataFrame:
        """Get recent activity table data"""
        # Generate sample activity data
        activities = [
            {'time': '10:30:15', 'activity': 'User Login', 'user': 'admin', 'status': '✅'},
            {'time': '10:29:45', 'activity': 'Query Executed', 'user': 'analyst', 'status': '✅'},
            {'time': '10:28:20', 'activity': 'Cluster Added', 'user': 'admin', 'status': '✅'},
            {'time': '10:27:55', 'activity': 'User Created', 'user': 'admin', 'status': '✅'},
            {'time': '10:26:30', 'activity': 'Backup Created', 'user': 'system', 'status': '✅'}
        ]
        
        return pd.DataFrame(activities)


def dashboard_v2_page():
    """Main enhanced dashboard page"""
    
    # Apply RTL CSS
    apply_rtl_css()
    
    # Create dashboard manager
    dashboard = DashboardManager()
    
    # Render dashboard
    dashboard.render_dashboard()


def main():
    """Test the enhanced dashboard"""
    dashboard_v2_page()


if __name__ == "__main__":
    main()