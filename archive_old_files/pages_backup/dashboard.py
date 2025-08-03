"""
RedshiftManager Advanced Dashboard
Central dashboard with dynamic widget loading and user preferences.
Now supports multiple database types and custom layouts.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import json

# Import our core components
try:
    from utils.i18n_helper import get_text, apply_rtl_css
    from models.database_models import get_database_manager
    from core.widget_framework import WidgetConfig, WidgetType, WidgetSize, DatabaseType
    from core.widget_registry import widget_registry, get_available_widgets, create_widget
    from utils.user_preferences import (
        preferences_manager, get_user_dashboard_layout, save_user_dashboard_layout,
        get_user_database_preference, save_user_database_preference
    )
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()

logger = logging.getLogger(__name__)


# User preferences and widget management
def get_user_widgets(user_id: str = "default") -> List[Dict[str, Any]]:
    """Get user's configured widgets with persistent storage"""
    # Try to load from persistent storage first
    try:
        widgets = get_user_dashboard_layout(user_id)
        # Update session state cache
        st.session_state.user_widgets = widgets
        return widgets
    except Exception as e:
        logger.error(f"Error loading user widgets: {e}")
        # Fallback to session state or defaults
        if 'user_widgets' not in st.session_state:
            st.session_state.user_widgets = _get_default_widget_config()
        return st.session_state.user_widgets

def save_user_widgets(widgets: List[Dict[str, Any]], user_id: str = "default") -> None:
    """Save user widget configuration with persistent storage"""
    try:
        # Save to persistent storage
        save_user_dashboard_layout(widgets, user_id)
        # Update session state cache
        st.session_state.user_widgets = widgets
        logger.info(f"Saved {len(widgets)} widget configurations for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving user widgets: {e}")
        # Fallback to session state only
        st.session_state.user_widgets = widgets

def _get_default_widget_config() -> List[Dict[str, Any]]:
    """Get default widget configuration"""
    return [
        {
            'name': 'cluster_status',
            'title': get_text('dashboard.widgets.cluster_status', 'Cluster Status'),
            'type': 'status',
            'size': 'medium',
            'position': {'row': 0, 'col': 0},
            'enabled': True
        },
        {
            'name': 'query_performance', 
            'title': get_text('dashboard.widgets.query_performance', 'Query Performance'),
            'type': 'chart',
            'size': 'large',
            'position': {'row': 0, 'col': 1},
            'enabled': True
        },
        {
            'name': 'storage_usage',
            'title': get_text('dashboard.widgets.storage_usage', 'Storage Usage'),
            'type': 'metric',
            'size': 'small',
            'position': {'row': 1, 'col': 0},
            'enabled': True
        }
    ]

def add_widget_to_dashboard(widget_name: str, widget_config: Dict[str, Any], user_id: str = "default") -> bool:
    """Add a new widget to user's dashboard"""
    try:
        user_widgets = get_user_widgets(user_id)
        new_widget = {
            'name': widget_name,
            'title': widget_config.get('title', widget_name),
            'type': widget_config.get('type', 'custom'),
            'size': widget_config.get('size', 'medium'),
            'position': widget_config.get('position', {'row': len(user_widgets), 'col': 0}),
            'enabled': True,
            'config': widget_config
        }
        user_widgets.append(new_widget)
        save_user_widgets(user_widgets, user_id)
        return True
    except Exception as e:
        logger.error(f"Failed to add widget {widget_name}: {e}")
        return False

def remove_widget_from_dashboard(widget_name: str, user_id: str = "default") -> bool:
    """Remove widget from user's dashboard"""
    try:
        user_widgets = get_user_widgets(user_id)
        user_widgets = [w for w in user_widgets if w['name'] != widget_name]
        save_user_widgets(user_widgets, user_id)
        return True
    except Exception as e:
        logger.error(f"Failed to remove widget {widget_name}: {e}")
        return False

def render_widget_dynamically(widget_config: Dict[str, Any], db_type: DatabaseType = DatabaseType.REDSHIFT) -> None:
    """Render a widget dynamically based on configuration"""
    try:
        # Create widget configuration
        config = WidgetConfig(
            title=widget_config['title'],
            widget_type=WidgetType(widget_config['type']),
            size=WidgetSize(widget_config['size'])
        )
        
        # Create widget instance
        widget_instance = create_widget(widget_config['name'], config, db_type)
        
        if widget_instance:
            # Render the widget
            widget_instance.render()
        else:
            # Fallback to built-in widgets
            render_builtin_widget(widget_config)
            
    except Exception as e:
        logger.error(f"Error rendering widget {widget_config['name']}: {e}")
        st.error(f"Failed to render widget: {widget_config['title']}")

def render_builtin_widget(widget_config: Dict[str, Any]) -> None:
    """Render built-in widgets as fallback"""
    widget_type = widget_config.get('type', 'status')
    
    with st.container():
        st.subheader(widget_config['title'])
        
        if widget_type == 'status':
            show_cluster_status_widget()
        elif widget_type == 'chart':
            show_query_performance_widget()
        elif widget_type == 'metric':
            show_storage_usage_widget()
        else:
            st.info(f"Widget type '{widget_type}' not implemented yet")

def dashboard_page():
    """
    Advanced dashboard page with dynamic widget loading.
    Supports user customization and multiple database types.
    """
    
    # Apply RTL CSS if needed
    apply_rtl_css()
    
    # Page configuration
    st.set_page_config(
        page_title="RedshiftManager Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Page header with widget management
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("📊 " + get_text("nav.dashboard", "Dashboard"))
        st.markdown("### " + get_text("dashboard.subtitle", "Dynamic Control Center"))
    
    with col2:
        if st.button("⚙️ " + get_text("dashboard.customize", "Customize")):
            st.session_state.show_widget_manager = not st.session_state.get('show_widget_manager', False)
    
    with col3:
        # Database type selector
        db_options = [db.value for db in DatabaseType]
        selected_db = st.selectbox(
            "🗄️ Database",
            db_options,
            index=0,
            key="dashboard_db_type"
        )
        current_db_type = DatabaseType(selected_db)
    
    st.markdown("---")
    
    # Widget management panel (if enabled)
    if st.session_state.get('show_widget_manager', False):
        show_widget_management_panel()
    
    # Quick status bar
    show_status_bar()
    
    # Dynamic dashboard layout
    show_dynamic_dashboard(current_db_type)
    
    # Footer with last update time
    show_dashboard_footer()


def show_widget_management_panel():
    """Display widget management panel for customization"""
    st.subheader("🔧 " + get_text("dashboard.widget_manager", "Widget Manager"))
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("**Available Widgets:**")
        available_widgets = get_available_widgets()
        
        if available_widgets:
            for widget_desc in available_widgets:
                with st.expander(f"{widget_desc.icon} {widget_desc.name}"):
                    st.write(f"**Description:** {widget_desc.description}")
                    st.write(f"**Category:** {widget_desc.category}")
                    st.write(f"**Supported DBs:** {[db.value for db in widget_desc.supported_databases]}")
                    
                    if st.button(f"Add {widget_desc.name}", key=f"add_{widget_desc.name}"):
                        config = {
                            'title': widget_desc.name.title(),
                            'type': 'custom',
                            'size': 'medium'
                        }
                        if add_widget_to_dashboard(widget_desc.name, config):
                            st.success(f"Added {widget_desc.name} to dashboard!")
                            st.experimental_rerun()
        else:
            st.info("No external widgets available. Register widgets using the Widget Registry.")
    
    with col2:
        st.write("**Current Layout:**")
        user_widgets = get_user_widgets()
        
        for i, widget in enumerate(user_widgets):
            with st.container():
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.write(f"• {widget['title']}")
                with col_b:
                    if st.button("❌", key=f"remove_{i}"):
                        if remove_widget_from_dashboard(widget['name']):
                            st.success("Widget removed!")
                            st.experimental_rerun()

def show_dynamic_dashboard(db_type: DatabaseType):
    """Display dashboard with dynamic widgets"""
    user_widgets = get_user_widgets()
    
    if not user_widgets:
        st.info("No widgets configured. Use the Customize button to add widgets.")
        return
    
    # Group widgets by row
    rows = {}
    for widget in user_widgets:
        if widget['enabled']:
            row = widget['position']['row']
            if row not in rows:
                rows[row] = []
            rows[row].append(widget)
    
    # Render widgets row by row
    for row_num in sorted(rows.keys()):
        row_widgets = rows[row_num]
        
        # Determine column layout based on widget sizes
        cols = st.columns(len(row_widgets))
        
        for i, widget in enumerate(row_widgets):
            with cols[i]:
                try:
                    render_widget_dynamically(widget, db_type)
                except Exception as e:
                    logger.error(f"Error rendering widget {widget['name']}: {e}")
                    st.error(f"Failed to render {widget['title']}")

def show_status_bar():
    """Display quick status information at the top"""
    
    st.subheader("🚦 " + get_text("dashboard.system_status", "System Status"))
    
    # Create status columns
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label=get_text("dashboard.system", "System"),
            value=get_text("dashboard.online", "Online"),
            delta="✅ " + get_text("dashboard.healthy", "Healthy")
        )
    
    with col2:
        # Get cluster count (simplified for now)
        cluster_count = get_cluster_count()
        st.metric(
            label=get_text("dashboard.clusters", "Clusters"),
            value=str(cluster_count),
            delta=f"+0" if cluster_count > 0 else "⚠️ " + get_text("dashboard.no_clusters", "No clusters")
        )
    
    with col3:
        # Get user count (simplified for now)
        user_count = get_user_count()
        st.metric(
            label=get_text("dashboard.users", "Users"),
            value=str(user_count),
            delta=f"+0" if user_count > 0 else "⚠️ " + get_text("dashboard.no_users", "No users")
        )
    
    with col4:
        # Get recent queries count
        recent_queries = get_recent_queries_count()
        st.metric(
            label=get_text("dashboard.recent_queries", "Recent Queries (24h)"),
            value=str(recent_queries),
            delta=f"+{recent_queries}" if recent_queries > 0 else "0"
        )
    
    with col5:
        # Show current time and uptime
        current_time = datetime.now().strftime("%H:%M:%S")
        st.metric(
            label=get_text("dashboard.current_time", "Current Time"),
            value=current_time,
            delta="🕐 " + get_text("dashboard.live", "Live")
        )


def show_main_dashboard():
    """Display the main dashboard content with widget areas"""
    
    st.markdown("---")
    
    # Dashboard tabs for different views
    tab1, tab2, tab3 = st.tabs([
        "📊 " + get_text("dashboard.overview", "Overview"),
        "🔧 " + get_text("dashboard.management", "Management"),
        "📈 " + get_text("dashboard.analytics", "Analytics")
    ])
    
    with tab1:
        show_overview_dashboard()
    
    with tab2:
        show_management_dashboard()
    
    with tab3:
        show_analytics_dashboard()


def show_overview_dashboard():
    """Show overview widgets"""
    
    st.subheader("🏠 " + get_text("dashboard.system_overview", "System Overview"))
    
    # Top row - Key metrics
    col1, col2 = st.columns(2)
    
    with col1:
        show_cluster_overview_widget()
    
    with col2:
        show_activity_summary_widget()
    
    # Bottom row - Recent activity
    st.subheader("📋 " + get_text("dashboard.recent_activity", "Recent Activity"))
    show_recent_activity_widget()


def show_management_dashboard():
    """Show management widgets"""
    
    st.subheader("🔧 " + get_text("dashboard.management_tools", "Management Tools"))
    
    # Management action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🗄️ " + get_text("dashboard.manage_clusters", "Manage Clusters"), 
                    use_container_width=True):
            st.info(get_text("dashboard.redirect_clusters", "Redirecting to Cluster Management..."))
    
    with col2:
        if st.button("👥 " + get_text("dashboard.manage_users", "Manage Users"), 
                    use_container_width=True):
            st.info(get_text("dashboard.redirect_users", "Redirecting to User Management..."))
    
    with col3:
        if st.button("🔍 " + get_text("dashboard.query_console", "Query Console"), 
                    use_container_width=True):
            st.info(get_text("dashboard.redirect_queries", "Redirecting to Query Console..."))
    
    with col4:
        if st.button("⚙️ " + get_text("dashboard.system_settings", "System Settings"), 
                    use_container_width=True):
            st.info(get_text("dashboard.redirect_settings", "Redirecting to Settings..."))
    
    # Management overview
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        show_system_health_widget()
    
    with col2:
        show_quick_actions_widget()


def show_analytics_dashboard():
    """Show analytics widgets"""
    
    st.subheader("📈 " + get_text("dashboard.analytics_overview", "Analytics Overview"))
    
    # Placeholder for analytics widgets
    col1, col2 = st.columns(2)
    
    with col1:
        show_performance_metrics_widget()
    
    with col2:
        show_usage_trends_widget()


# Widget Functions

def show_cluster_overview_widget():
    """Display cluster overview widget"""
    
    st.markdown("#### 🗄️ " + get_text("dashboard.cluster_status", "Cluster Status"))
    
    try:
        # Get cluster information
        clusters = get_cluster_info()
        
        if clusters:
            # Create a simple status display
            for cluster in clusters[:3]:  # Show only first 3 clusters
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{cluster.get('name', 'Unknown')}**")
                
                with col2:
                    status = cluster.get('status', 'unknown')
                    status_icon = "🟢" if status == 'active' else "🔴"
                    st.write(f"{status_icon} {status.title()}")
                
                with col3:
                    env = cluster.get('environment', 'unknown')
                    st.write(f"📂 {env.title()}")
            
            if len(clusters) > 3:
                st.info(f"... and {len(clusters) - 3} more clusters")
        else:
            st.info(get_text("dashboard.no_clusters_configured", "No clusters configured yet"))
            
    except Exception as e:
        st.error(f"Error loading cluster information: {e}")


def show_activity_summary_widget():
    """Display activity summary widget"""
    
    st.markdown("#### 📊 " + get_text("dashboard.activity_summary", "Activity Summary"))
    
    # Generate sample metrics (will be replaced with real data)
    import random
    
    metrics = {
        get_text("dashboard.queries_today", "Queries Today"): random.randint(50, 500),
        get_text("dashboard.avg_response_time", "Avg Response Time"): f"{random.uniform(0.5, 5.0):.2f}s",
        get_text("dashboard.active_sessions", "Active Sessions"): random.randint(1, 25),
        get_text("dashboard.data_processed", "Data Processed"): f"{random.uniform(1.0, 100.0):.1f} GB"
    }
    
    for label, value in metrics.items():
        st.metric(label, value)


def show_recent_activity_widget():
    """Display recent activity widget"""
    
    # Generate sample recent activity
    activities = generate_sample_activity()
    
    if activities:
        # Create DataFrame for better display
        df = pd.DataFrame(activities)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(get_text("dashboard.no_recent_activity", "No recent activity"))


def show_system_health_widget():
    """Display system health widget"""
    
    st.markdown("#### 🏥 " + get_text("dashboard.system_health", "System Health"))
    
    # Health metrics
    health_metrics = {
        get_text("dashboard.cpu_usage", "CPU Usage"): "45%",
        get_text("dashboard.memory_usage", "Memory Usage"): "62%", 
        get_text("dashboard.disk_usage", "Disk Usage"): "38%",
        get_text("dashboard.network", "Network"): get_text("dashboard.normal", "Normal")
    }
    
    for metric, value in health_metrics.items():
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(metric)
        with col2:
            # Color code based on value
            if "%" in str(value):
                percentage = int(value.replace("%", ""))
                color = "🟢" if percentage < 70 else "🟡" if percentage < 90 else "🔴"
                st.write(f"{color} {value}")
            else:
                st.write(f"🟢 {value}")


def show_quick_actions_widget():
    """Display quick actions widget"""
    
    st.markdown("#### ⚡ " + get_text("dashboard.quick_actions", "Quick Actions"))
    
    # Quick action buttons
    if st.button("🔄 " + get_text("dashboard.refresh_data", "Refresh Data"), 
                use_container_width=True):
        st.success(get_text("dashboard.data_refreshed", "Data refreshed successfully"))
        st.experimental_rerun()
    
    if st.button("📊 " + get_text("dashboard.generate_report", "Generate Quick Report"), 
                use_container_width=True):
        st.info(get_text("dashboard.report_generating", "Report generation started..."))
    
    if st.button("🧹 " + get_text("dashboard.cleanup", "System Cleanup"), 
                use_container_width=True):
        st.info(get_text("dashboard.cleanup_started", "System cleanup initiated..."))


def show_performance_metrics_widget():
    """Display performance metrics widget"""
    
    st.markdown("#### ⚡ " + get_text("dashboard.performance_metrics", "Performance Metrics"))
    
    # Generate sample performance data
    import plotly.graph_objects as go
    import numpy as np
    
    # Sample data for the last 24 hours
    hours = list(range(24))
    response_times = np.random.normal(2.5, 0.8, 24)
    response_times = np.maximum(response_times, 0.1)  # Ensure positive values
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours,
        y=response_times,
        mode='lines+markers',
        name=get_text("dashboard.response_time", "Response Time"),
        line=dict(color='#1f77b4')
    ))
    
    fig.update_layout(
        title=get_text("dashboard.response_time_trend", "Response Time Trend (24h)"),
        xaxis_title=get_text("dashboard.hour", "Hour"),
        yaxis_title=get_text("dashboard.seconds", "Seconds"),
        height=300,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def show_usage_trends_widget():
    """Display usage trends widget"""
    
    st.markdown("#### 📈 " + get_text("dashboard.usage_trends", "Usage Trends"))
    
    # Generate sample usage data
    import plotly.express as px
    
    days = [f"Day {i+1}" for i in range(7)]
    queries = np.random.randint(50, 200, 7)
    users = np.random.randint(5, 25, 7)
    
    # Create DataFrame
    df = pd.DataFrame({
        get_text("dashboard.day", "Day"): days,
        get_text("dashboard.queries", "Queries"): queries,
        get_text("dashboard.active_users", "Active Users"): users
    })
    
    fig = px.bar(df, x=get_text("dashboard.day", "Day"), 
                 y=get_text("dashboard.queries", "Queries"),
                 title=get_text("dashboard.weekly_usage", "Weekly Usage Pattern"))
    
    fig.update_layout(height=300)
    
    st.plotly_chart(fig, use_container_width=True)


def show_dashboard_footer():
    """Display dashboard footer with update information"""
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.caption(f"🕐 {get_text('dashboard.last_updated', 'Last updated')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    with col2:
        if st.button("🔄 " + get_text("dashboard.refresh", "Refresh"), key="footer_refresh"):
            st.experimental_rerun()
    
    with col3:
        st.caption(f"📊 {get_text('dashboard.version', 'Dashboard v1.0')}")


# Helper Functions

def get_cluster_count() -> int:
    """Get total number of clusters"""
    try:
        db_manager = get_database_manager()
        with db_manager.session_scope() as session:
            from models.database_models import RedshiftCluster
            count = session.query(RedshiftCluster).filter_by(is_active=True).count()
            return count
    except Exception:
        return 0


def get_user_count() -> int:
    """Get total number of users"""
    try:
        db_manager = get_database_manager()
        with db_manager.session_scope() as session:
            from models.database_models import User
            count = session.query(User).filter_by(is_active=True).count()
            return count
    except Exception:
        return 0


def get_recent_queries_count() -> int:
    """Get count of recent queries (last 24 hours)"""
    try:
        db_manager = get_database_manager()
        with db_manager.session_scope() as session:
            from models.database_models import QueryHistory
            yesterday = datetime.now() - timedelta(days=1)
            count = session.query(QueryHistory).filter(
                QueryHistory.created_at >= yesterday
            ).count()
            return count
    except Exception:
        return 0


def get_cluster_info() -> List[Dict[str, Any]]:
    """Get cluster information"""
    try:
        db_manager = get_database_manager()
        with db_manager.session_scope() as session:
            from models.database_models import RedshiftCluster
            clusters = session.query(RedshiftCluster).filter_by(is_active=True).all()
            
            return [
                {
                    'name': cluster.name,
                    'status': 'active' if cluster.is_active else 'inactive',
                    'environment': cluster.environment,
                    'host': cluster.host
                }
                for cluster in clusters
            ]
    except Exception as e:
        logging.error(f"Error getting cluster info: {e}")
        return []


def generate_sample_activity() -> List[Dict[str, Any]]:
    """Generate sample recent activity for display"""
    
    import random
    from datetime import datetime, timedelta
    
    activities = []
    activity_types = [
        get_text("dashboard.activity_login", "User Login"),
        get_text("dashboard.activity_query", "Query Executed"),
        get_text("dashboard.activity_cluster", "Cluster Added"),
        get_text("dashboard.activity_user", "User Created"),
        get_text("dashboard.activity_backup", "Backup Created")
    ]
    
    users = ["admin", "analyst", "developer", "manager"]
    
    for i in range(10):
        time_ago = datetime.now() - timedelta(minutes=random.randint(1, 1440))
        activities.append({
            get_text("dashboard.time", "Time"): time_ago.strftime("%H:%M"),
            get_text("dashboard.activity", "Activity"): random.choice(activity_types),
            get_text("dashboard.user", "User"): random.choice(users),
            get_text("dashboard.status", "Status"): "✅" if random.random() > 0.1 else "❌"
        })
    
    return activities


if __name__ == "__main__":
    dashboard_page()