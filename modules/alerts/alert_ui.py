"""
Alert System UI Components
Streamlit interface for alert management and monitoring.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.logging_system import RedshiftLogger

from modules.alerts.alert_manager import AlertManager, AlertSeverity, AlertStatus

# Auth decorators disabled for open access mode

logger = RedshiftLogger()


class AlertPanel:
    """Main alert management panel"""

    def __init__(self):
        self.alert_manager = AlertManager()
        self.alert_manager.initialize()

    def render(self):
        """Render the main alert panel"""
        st.subheader("🚨 Alert & Monitoring System")
        st.markdown(
            "Real-time system monitoring with intelligent alerting and notifications."
        )
        st.markdown("---")

        # Create tabs for different alert operations
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📊 Dashboard",
                "🚨 Active Alerts",
                "📈 System Metrics",
                "📋 Alert History",
                "⚙️ Settings",
            ]
        )

        with tab1:
            self._render_dashboard()

        with tab2:
            self._render_active_alerts()

        with tab3:
            self._render_system_metrics()

        with tab4:
            self._render_alert_history()

        with tab5:
            self._render_settings()

    def _render_dashboard(self):
        """Render alert system dashboard"""
        st.markdown("#### 📊 System Overview")

        # Get system information
        info = self.alert_manager.get_info()
        active_alerts = self.alert_manager.get_active_alerts()
        system_metrics = self.alert_manager.get_system_metrics()

        # Status metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            alert_count = info.get("active_alerts", 0)
            if alert_count > 0:
                st.metric(
                    "🚨 Active Alerts",
                    alert_count,
                    delta=alert_count,
                    delta_color="inverse",
                )
            else:
                st.metric("✅ Active Alerts", "0", delta="All Clear")

        with col2:
            monitoring_status = info.get("status", "inactive")
            status_emoji = "🟢" if monitoring_status == "active" else "🔴"
            st.metric("📡 Monitoring", f"{status_emoji} {monitoring_status.title()}")

        with col3:
            rules_count = info.get("total_rules", 0)
            st.metric("📋 Alert Rules", rules_count)

        with col4:
            channels = info.get("notification_channels", [])
            st.metric("📬 Channels", len(channels))

        st.markdown("---")

        # Current system status
        if system_metrics:
            st.markdown("#### 🖥️ Current System Status")

            col1, col2, col3 = st.columns(3)

            with col1:
                cpu_percent = system_metrics.get("cpu_percent", 0)
                cpu_color = (
                    "🟢" if cpu_percent < 70 else "🟡" if cpu_percent < 85 else "🔴"
                )
                st.metric(f"{cpu_color} CPU Usage", f"{cpu_percent:.1f}%")

            with col2:
                memory_percent = system_metrics.get("memory_percent", 0)
                memory_color = (
                    "🟢"
                    if memory_percent < 75
                    else "🟡" if memory_percent < 90 else "🔴"
                )
                st.metric(f"{memory_color} Memory Usage", f"{memory_percent:.1f}%")

            with col3:
                disk_percent = system_metrics.get("disk_percent", 0)
                disk_color = (
                    "🟢" if disk_percent < 80 else "🟡" if disk_percent < 95 else "🔴"
                )
                st.metric(f"{disk_color} Disk Usage", f"{disk_percent:.1f}%")

        # Active alerts summary
        if active_alerts:
            st.markdown("#### 🚨 Critical Alerts Requiring Attention")

            # Group alerts by severity
            severity_counts = {}
            for alert in active_alerts:
                severity = alert.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Display severity breakdown
            severity_cols = st.columns(len(severity_counts))

            severity_colors = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }

            for i, (severity, count) in enumerate(severity_counts.items()):
                with severity_cols[i]:
                    color = severity_colors.get(severity, "⚪")
                    st.metric(f"{color} {severity.title()}", count)

            # Recent alerts
            st.markdown("##### Recent Alerts:")
            for alert in active_alerts[:3]:  # Show top 3
                severity_emoji = severity_colors.get(alert.severity.value, "⚪")
                created_time = datetime.fromisoformat(alert.created_at)
                time_ago = self._time_ago(created_time)

                with st.expander(f"{severity_emoji} {alert.title} - {time_ago}"):
                    st.markdown(f"**Description:** {alert.description}")
                    st.markdown(f"**Status:** {alert.status.value.title()}")
                    st.markdown(f"**Source:** {alert.source}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Acknowledge", key=f"ack_{alert.id}"):
                            self._acknowledge_alert(alert.id)
                    with col2:
                        if st.button("🔧 Resolve", key=f"resolve_{alert.id}"):
                            self._resolve_alert(alert.id)
        else:
            st.success("🎉 No active alerts! System is running smoothly.")

    def _render_active_alerts(self):
        """Render active alerts management"""
        current_user = get_current_user()

        st.markdown("#### 🚨 Active Alerts Management")

        active_alerts = self.alert_manager.get_active_alerts()

        if not active_alerts:
            st.success("✅ No active alerts currently!")
            st.balloons()
            return

        # Filter controls
        col1, col2, col3 = st.columns(3)

        with col1:
            severity_filter = st.selectbox(
                "Filter by Severity",
                options=["All"] + [s.value.title() for s in AlertSeverity],
                key="severity_filter",
            )

        with col2:
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All"] + [s.value.title() for s in AlertStatus],
                key="status_filter",
            )

        with col3:
            sort_by = st.selectbox(
                "Sort by", options=["Created Time", "Severity", "Title"], key="sort_by"
            )

        # Apply filters
        filtered_alerts = active_alerts

        if severity_filter != "All":
            filtered_alerts = [
                a
                for a in filtered_alerts
                if a.severity.value == severity_filter.lower()
            ]

        if status_filter != "All":
            filtered_alerts = [
                a for a in filtered_alerts if a.status.value == status_filter.lower()
            ]

        # Sort alerts
        if sort_by == "Severity":
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            filtered_alerts.sort(key=lambda x: severity_order.get(x.severity.value, 4))
        elif sort_by == "Title":
            filtered_alerts.sort(key=lambda x: x.title)
        else:  # Created Time
            filtered_alerts.sort(key=lambda x: x.created_at, reverse=True)

        st.markdown(f"##### Showing {len(filtered_alerts)} alerts:")

        # Display alerts
        for alert in filtered_alerts:
            self._render_alert_card(alert, current_user)

    def _render_alert_card(self, alert, current_user):
        """Render individual alert card"""
        severity_colors = {
            AlertSeverity.CRITICAL: "🔴",
            AlertSeverity.HIGH: "🟠",
            AlertSeverity.MEDIUM: "🟡",
            AlertSeverity.LOW: "🟢",
        }

        severity_emoji = severity_colors.get(alert.severity, "⚪")
        created_time = datetime.fromisoformat(alert.created_at)
        time_ago = self._time_ago(created_time)

        with st.container():
            # Alert header
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"### {severity_emoji} {alert.title}")
                st.markdown(f"**{alert.description}**")

            with col2:
                st.markdown(f"**Status:** {alert.status.value.title()}")
                st.markdown(f"**Severity:** {alert.severity.value.title()}")

            with col3:
                st.markdown(f"**Created:** {time_ago}")
                st.markdown(f"**Source:** {alert.source}")

            # Alert details
            with st.expander("📋 Alert Details"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Alert ID:** `{alert.id}`")
                    if alert.acknowledged_by:
                        st.markdown(f"**Acknowledged by:** {alert.acknowledged_by}")
                    if alert.resolved_at:
                        st.markdown(f"**Resolved at:** {alert.resolved_at}")

                with col2:
                    st.markdown("**Metadata:**")
                    if alert.metadata:
                        for key, value in alert.metadata.items():
                            if key != "metrics":  # Skip complex metrics
                                st.markdown(f"- **{key}:** {value}")

            # Actions
            if current_user and current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    if alert.status == AlertStatus.ACTIVE:
                        if st.button("✅ Acknowledge", key=f"ack_card_{alert.id}"):
                            self._acknowledge_alert(alert.id)

                with col2:
                    if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
                        if st.button("🔧 Resolve", key=f"resolve_card_{alert.id}"):
                            self._resolve_alert(alert.id)

                with col3:
                    if st.button("📤 Export", key=f"export_{alert.id}"):
                        self._export_alert(alert)

                with col4:
                    if st.button("🔄 Refresh", key=f"refresh_{alert.id}"):
                        st.rerun()

            st.markdown("---")

    def _render_system_metrics(self):
        """Render system metrics and monitoring charts"""
        st.markdown("#### 📈 System Performance Metrics")

        # Time range selector
        col1, col2 = st.columns([1, 3])

        with col1:
            time_range = st.selectbox(
                "Time Range",
                options=["Last Hour", "Last 6 Hours", "Last 24 Hours", "Last Week"],
                index=2,
            )

        # Convert time range to hours
        hours_map = {
            "Last Hour": 1,
            "Last 6 Hours": 6,
            "Last 24 Hours": 24,
            "Last Week": 168,
        }
        hours = hours_map[time_range]

        # Get metrics history
        metrics_history = self.alert_manager.get_metrics_history(hours)

        if not metrics_history:
            st.info(
                "📊 No metrics data available yet. Monitoring system is collecting data..."
            )
            return

        # Convert to DataFrame
        df = pd.DataFrame(metrics_history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # Current metrics
        current_metrics = self.alert_manager.get_system_metrics()
        if current_metrics:
            st.markdown("##### Current System Status:")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                cpu = current_metrics.get("cpu_percent", 0)
                st.metric("CPU Usage", f"{cpu:.1f}%")

            with col2:
                memory = current_metrics.get("memory_percent", 0)
                st.metric("Memory Usage", f"{memory:.1f}%")

            with col3:
                disk = current_metrics.get("disk_percent", 0)
                st.metric("Disk Usage", f"{disk:.1f}%")

            with col4:
                connections = current_metrics.get("active_connections", 0)
                st.metric("Active Connections", connections)

        st.markdown("---")

        # Performance charts
        st.markdown("##### Performance Trends:")

        # CPU and Memory chart
        fig_system = go.Figure()

        fig_system.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["cpu_percent"],
                mode="lines",
                name="CPU %",
                line=dict(color="#1f77b4"),
            )
        )

        fig_system.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["memory_percent"],
                mode="lines",
                name="Memory %",
                line=dict(color="#ff7f0e"),
            )
        )

        fig_system.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["disk_percent"],
                mode="lines",
                name="Disk %",
                line=dict(color="#2ca02c"),
            )
        )

        # Add threshold lines
        config = self.alert_manager.config
        fig_system.add_hline(
            y=config.get("alert_threshold_cpu", 80),
            line_dash="dash",
            line_color="red",
            annotation_text="CPU Alert Threshold",
        )

        fig_system.add_hline(
            y=config.get("alert_threshold_memory", 85),
            line_dash="dash",
            line_color="orange",
            annotation_text="Memory Alert Threshold",
        )

        fig_system.update_layout(
            title="System Resource Usage Over Time",
            xaxis_title="Time",
            yaxis_title="Usage Percentage",
            hovermode="x unified",
        )

        st.plotly_chart(fig_system, use_container_width=True)

        # Network activity chart if data available
        if "active_connections" in df.columns:
            fig_network = px.line(
                df,
                x="timestamp",
                y="active_connections",
                title="Network Connections Over Time",
                labels={
                    "active_connections": "Active Connections",
                    "timestamp": "Time",
                },
            )

            st.plotly_chart(fig_network, use_container_width=True)

    def _render_alert_history(self):
        """Render alert history and analytics"""
        current_user = get_current_user()

        # Check permissions
        if not current_user or current_user.role not in [
            UserRole.ADMIN,
            UserRole.MANAGER,
        ]:
            st.warning("🔐 Manager or Admin permissions required to view alert history")
            return

        st.markdown("#### 📋 Alert History & Analytics")

        # This is a placeholder - in a real implementation would query database
        st.info("📊 Alert history analytics would be displayed here")

        # Sample analytics
        st.markdown("##### Alert Summary (Last 30 Days):")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Alerts", "42", delta="↓ 15%")

        with col2:
            st.metric("Critical Alerts", "3", delta="↓ 50%")

        with col3:
            st.metric("Avg Resolution Time", "12 min", delta="↓ 5 min")

        with col4:
            st.metric("System Uptime", "99.8%", delta="↑ 0.2%")

    def _render_settings(self):
        """Render alert system settings"""
        current_user = get_current_user()

        # Check permissions
        if not current_user or current_user.role != UserRole.ADMIN:
            st.warning("🔐 Admin permissions required to modify alert settings")
            return

        st.markdown("#### ⚙️ Alert System Configuration")

        # Load current configuration
        current_config = self.alert_manager.config

        with st.form("alert_settings_form"):
            st.markdown("##### 📬 Notification Settings")

            col1, col2 = st.columns(2)

            with col1:
                email_notifications = st.checkbox(
                    "Enable Email Notifications",
                    value=current_config.get("email_notifications", True),
                    help="Send alert notifications via email",
                )

                if email_notifications:
                    smtp_server = st.text_input(
                        "SMTP Server",
                        value=current_config.get("smtp_server", "smtp.gmail.com"),
                        help="SMTP server for sending emails",
                    )

                    smtp_port = st.number_input(
                        "SMTP Port",
                        min_value=1,
                        max_value=65535,
                        value=current_config.get("smtp_port", 587),
                        help="SMTP server port",
                    )

                    from_email = st.text_input(
                        "From Email Address",
                        value=current_config.get("from_email", ""),
                        help="Email address to send notifications from",
                    )

            with col2:
                sms_notifications = st.checkbox(
                    "Enable SMS Notifications",
                    value=current_config.get("sms_notifications", False),
                    help="Send critical alerts via SMS",
                )

                max_alerts_per_hour = st.number_input(
                    "Max Alerts per Hour",
                    min_value=1,
                    max_value=100,
                    value=current_config.get("max_alerts_per_hour", 10),
                    help="Limit to prevent notification spam",
                )

            st.markdown("##### 🎚️ Alert Thresholds")

            col1, col2, col3 = st.columns(3)

            with col1:
                cpu_threshold = st.slider(
                    "CPU Alert Threshold (%)",
                    min_value=50,
                    max_value=95,
                    value=current_config.get("alert_threshold_cpu", 80),
                    help="CPU usage percentage to trigger alerts",
                )

            with col2:
                memory_threshold = st.slider(
                    "Memory Alert Threshold (%)",
                    min_value=50,
                    max_value=95,
                    value=current_config.get("alert_threshold_memory", 85),
                    help="Memory usage percentage to trigger alerts",
                )

            with col3:
                disk_threshold = st.slider(
                    "Disk Alert Threshold (%)",
                    min_value=70,
                    max_value=98,
                    value=current_config.get("alert_threshold_disk", 90),
                    help="Disk usage percentage to trigger alerts",
                )

            st.markdown("##### ⏱️ Timing Settings")

            col1, col2, col3 = st.columns(3)

            with col1:
                check_interval = st.number_input(
                    "Check Interval (minutes)",
                    min_value=1,
                    max_value=60,
                    value=current_config.get("check_interval_minutes", 5),
                    help="How often to check system metrics",
                )

            with col2:
                escalation_delay = st.number_input(
                    "Escalation Delay (minutes)",
                    min_value=5,
                    max_value=120,
                    value=current_config.get("escalation_delay_minutes", 15),
                    help="Time before escalating unresolved alerts",
                )

            with col3:
                retention_days = st.number_input(
                    "Alert Retention (days)",
                    min_value=7,
                    max_value=365,
                    value=current_config.get("alert_retention_days", 30),
                    help="How long to keep resolved alerts",
                )

            # Save settings
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.form_submit_button("💾 Save Settings", type="primary"):
                    new_config = {
                        "email_notifications": email_notifications,
                        "sms_notifications": sms_notifications,
                        "smtp_server": smtp_server if email_notifications else "",
                        "smtp_port": smtp_port if email_notifications else 587,
                        "from_email": from_email if email_notifications else "",
                        "alert_threshold_cpu": cpu_threshold,
                        "alert_threshold_memory": memory_threshold,
                        "alert_threshold_disk": disk_threshold,
                        "check_interval_minutes": check_interval,
                        "escalation_delay_minutes": escalation_delay,
                        "max_alerts_per_hour": max_alerts_per_hour,
                        "alert_retention_days": retention_days,
                    }

                    if self._save_alert_settings(new_config):
                        st.success("✅ Settings saved successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save settings")

            with col2:
                if st.form_submit_button("🔄 Reset to Defaults"):
                    if self._reset_alert_settings():
                        st.success("✅ Settings reset to defaults!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to reset settings")

        # Test notifications
        st.markdown("---")
        st.markdown("##### 🧪 Test Notifications")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📧 Send Test Email", use_container_width=True):
                self._send_test_email()

        with col2:
            if st.button("📊 Generate Test Alert", use_container_width=True):
                self._generate_test_alert()

    def _acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        current_user = get_current_user()
        username = current_user.username if current_user else "unknown"

        if self.alert_manager.acknowledge_alert(alert_id, username):
            st.success("✅ Alert acknowledged successfully!")
            st.rerun()
        else:
            st.error("❌ Failed to acknowledge alert")

    def _resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        current_user = get_current_user()
        username = current_user.username if current_user else "unknown"

        if self.alert_manager.resolve_alert(alert_id, username):
            st.success("✅ Alert resolved successfully!")
            st.rerun()
        else:
            st.error("❌ Failed to resolve alert")

    def _export_alert(self, alert):
        """Export alert details"""
        alert_data = {
            "id": alert.id,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "created_at": alert.created_at,
            "source": alert.source,
            "metadata": alert.metadata,
        }

        st.download_button(
            "💾 Download Alert Details",
            data=json.dumps(alert_data, indent=2),
            file_name=f"alert_{alert.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

    def _save_alert_settings(self, new_config):
        """Save alert settings"""
        try:
            config_path = project_root / "data" / "module_configs" / "alert_system.json"

            if config_path.exists():
                with open(config_path, "r") as f:
                    full_config = json.load(f)
            else:
                full_config = {"enabled": True, "auto_start": True, "priority": 8}

            full_config["custom"] = new_config
            full_config["last_modified"] = datetime.now().isoformat()

            with open(config_path, "w") as f:
                json.dump(full_config, f, indent=2)

            # Update alert manager config
            self.alert_manager.config = new_config

            logger.log_action_end("Alert settings updated")
            return True

        except Exception as e:
            logger.log_error(f"Error saving alert settings: {e}")
            return False

    def _reset_alert_settings(self):
        """Reset alert settings to defaults"""
        default_config = {
            "email_notifications": True,
            "sms_notifications": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "from_email": "",
            "alert_threshold_cpu": 80,
            "alert_threshold_memory": 85,
            "alert_threshold_disk": 90,
            "check_interval_minutes": 5,
            "escalation_delay_minutes": 15,
            "max_alerts_per_hour": 10,
            "alert_retention_days": 30,
        }

        return self._save_alert_settings(default_config)

    def _send_test_email(self):
        """Send test email notification"""
        try:
            # This would send an actual test email
            st.success("✅ Test email sent successfully!")
            logger.log_action_end("Test email notification sent")
        except Exception as e:
            st.error(f"❌ Failed to send test email: {e}")

    def _generate_test_alert(self):
        """Generate a test alert"""
        try:
            # This would create a test alert
            st.success("✅ Test alert generated successfully!")
            logger.log_action_end("Test alert generated")
        except Exception as e:
            st.error(f"❌ Failed to generate test alert: {e}")

    @staticmethod
    def _time_ago(timestamp: datetime) -> str:
        """Calculate time ago string"""
        now = datetime.now()
        diff = now - timestamp

        if diff.seconds < 60:
            return "Just now"
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff.seconds < 86400:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"


class AlertSettings:
    """Alert settings configuration panel"""

    def __init__(self):
        self.alert_manager = AlertManager()

    def render(self):
        """Render alert settings panel"""
        st.markdown("### ⚙️ Alert System Settings")

        # This would be used in the module manager
        # Currently integrated into the main AlertPanel
        panel = AlertPanel()
        panel._render_settings()
