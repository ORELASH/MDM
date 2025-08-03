"""
Alert Manager Module
Core alert and notification system for RedshiftManager with real-time monitoring.
"""

import json
import os
import smtplib
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil
import schedule

try:
    from email.mime.multipart import MimeMultipart
    from email.mime.text import MimeText
except ImportError:
    # Fallback for systems with limited email support
    MimeText = None
    MimeMultipart = None
import sqlite3

# Add project root to path
import sys
from enum import Enum

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.logging_system import RedshiftLogger

from core.plugin_interface import ModuleBase


class AlertSeverity(Enum):
    """Alert severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status states"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class NotificationChannel(Enum):
    """Available notification channels"""

    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DESKTOP = "desktop"


@dataclass
class Alert:
    """Alert data structure"""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    created_at: str
    updated_at: str
    source: str
    metadata: Dict[str, Any]
    resolved_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    escalated_at: Optional[str] = None


@dataclass
class AlertRule:
    """Alert rule configuration"""

    id: str
    name: str
    description: str
    condition: str
    severity: AlertSeverity
    enabled: bool
    notification_channels: List[NotificationChannel]
    threshold_value: float
    check_interval_minutes: int
    cooldown_minutes: int
    escalation_minutes: int


@dataclass
class NotificationConfig:
    """Notification system configuration"""

    email_enabled: bool
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str
    sms_enabled: bool
    sms_api_key: str
    webhook_url: str


class AlertManager(ModuleBase):
    """
    Main alert manager class implementing comprehensive alerting functionality
    """

    def __init__(self):
        self.logger = RedshiftLogger()
        self._config = self._load_config()

        # Initialize database
        self.db_path = project_root / "data" / "alerts.db"
        self._init_database()

        # Monitoring state
        self._monitoring_thread = None
        self._monitoring_running = False
        self._last_check_time = None

        # Alert throttling
        self._alert_count = {}  # Channel -> count per hour
        self._alert_history = []

        # System monitoring
        self._system_metrics = {}
        self._metric_history = []

        # Predefined alert rules
        self._default_rules = self._create_default_rules()
        self._active_rules = {}

        self.logger.log_action_start("Alert Manager initialized")

    @property
    def config(self):
        """Get current configuration"""
        return self._config

    @config.setter
    def config(self, value):
        """Set configuration"""
        self._config = value

    def initialize(self) -> bool:
        """Initialize the alert module"""
        try:
            self._load_alert_rules()
            self._start_monitoring()
            self.logger.log_action_end("Alert Manager initialized successfully")
            return True
        except Exception as e:
            self.logger.log_error(f"Failed to initialize Alert Manager: {e}")
            return False

    def cleanup(self) -> bool:
        """Cleanup alert module resources"""
        try:
            self._stop_monitoring()
            self.logger.log_action_end("Alert Manager cleanup completed")
            return True
        except Exception as e:
            self.logger.log_error(f"Error during Alert Manager cleanup: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """Get module information"""
        active_alerts = self._get_active_alerts_count()

        return {
            "name": "alert_system",
            "display_name": "Alert & Notification System",
            "version": "1.0.0",
            "status": "active" if self._monitoring_running else "inactive",
            "active_alerts": active_alerts,
            "total_rules": len(self._active_rules),
            "last_check": (
                self._last_check_time.isoformat() if self._last_check_time else None
            ),
            "notification_channels": self._get_enabled_channels(),
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load alert configuration"""
        try:
            config_path = project_root / "data" / "module_configs" / "alert_system.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                    return config_data.get("custom", {})

            # Default configuration
            return {
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
        except Exception as e:
            self.logger.log_error(f"Error loading alert config: {e}")
            return {}

    def _init_database(self):
        """Initialize SQLite database for alerts"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Alerts table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT,
                        severity TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        source TEXT NOT NULL,
                        metadata TEXT,
                        resolved_at TEXT,
                        acknowledged_by TEXT,
                        escalated_at TEXT
                    )
                """
                )

                # Alert rules table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alert_rules (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        condition TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        enabled BOOLEAN NOT NULL,
                        notification_channels TEXT,
                        threshold_value REAL,
                        check_interval_minutes INTEGER,
                        cooldown_minutes INTEGER,
                        escalation_minutes INTEGER
                    )
                """
                )

                # System metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        cpu_percent REAL,
                        memory_percent REAL,
                        disk_percent REAL,
                        active_connections INTEGER,
                        query_count INTEGER
                    )
                """
                )

                conn.commit()

        except Exception as e:
            self.logger.log_error(f"Error initializing alert database: {e}")
            raise

    def _create_default_rules(self) -> List[AlertRule]:
        """Create default alert rules"""
        return [
            AlertRule(
                id="cpu_high",
                name="High CPU Usage",
                description="CPU usage exceeded threshold",
                condition="cpu_percent > threshold",
                severity=AlertSeverity.HIGH,
                enabled=True,
                notification_channels=[NotificationChannel.EMAIL],
                threshold_value=self.config.get("alert_threshold_cpu", 80),
                check_interval_minutes=5,
                cooldown_minutes=10,
                escalation_minutes=15,
            ),
            AlertRule(
                id="memory_high",
                name="High Memory Usage",
                description="Memory usage exceeded threshold",
                condition="memory_percent > threshold",
                severity=AlertSeverity.HIGH,
                enabled=True,
                notification_channels=[NotificationChannel.EMAIL],
                threshold_value=self.config.get("alert_threshold_memory", 85),
                check_interval_minutes=5,
                cooldown_minutes=10,
                escalation_minutes=15,
            ),
            AlertRule(
                id="disk_full",
                name="Disk Space Critical",
                description="Disk usage exceeded critical threshold",
                condition="disk_percent > threshold",
                severity=AlertSeverity.CRITICAL,
                enabled=True,
                notification_channels=[NotificationChannel.EMAIL],
                threshold_value=self.config.get("alert_threshold_disk", 90),
                check_interval_minutes=2,
                cooldown_minutes=5,
                escalation_minutes=10,
            ),
            AlertRule(
                id="service_down",
                name="Service Unavailable",
                description="Critical service is not responding",
                condition="service_status == 'down'",
                severity=AlertSeverity.CRITICAL,
                enabled=True,
                notification_channels=[NotificationChannel.EMAIL],
                threshold_value=1,
                check_interval_minutes=1,
                cooldown_minutes=2,
                escalation_minutes=5,
            ),
            AlertRule(
                id="query_slow",
                name="Slow Query Performance",
                description="Database queries are taking too long",
                condition="avg_query_time > threshold",
                severity=AlertSeverity.MEDIUM,
                enabled=True,
                notification_channels=[NotificationChannel.EMAIL],
                threshold_value=5000,  # 5 seconds in milliseconds
                check_interval_minutes=10,
                cooldown_minutes=15,
                escalation_minutes=30,
            ),
        ]

    def _load_alert_rules(self):
        """Load alert rules from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM alert_rules WHERE enabled = 1")
                rows = cursor.fetchall()

                if not rows:
                    # Load default rules if none exist
                    self._save_default_rules()
                    rows = cursor.execute(
                        "SELECT * FROM alert_rules WHERE enabled = 1"
                    ).fetchall()

                self._active_rules = {}
                for row in rows:
                    rule = AlertRule(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        condition=row[3],
                        severity=AlertSeverity(row[4]),
                        enabled=bool(row[5]),
                        notification_channels=[
                            NotificationChannel(ch) for ch in json.loads(row[6])
                        ],
                        threshold_value=row[7],
                        check_interval_minutes=row[8],
                        cooldown_minutes=row[9],
                        escalation_minutes=row[10],
                    )
                    self._active_rules[rule.id] = rule

        except Exception as e:
            self.logger.log_error(f"Error loading alert rules: {e}")

    def _save_default_rules(self):
        """Save default rules to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for rule in self._default_rules:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO alert_rules 
                        (id, name, description, condition, severity, enabled, 
                         notification_channels, threshold_value, check_interval_minutes,
                         cooldown_minutes, escalation_minutes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            rule.id,
                            rule.name,
                            rule.description,
                            rule.condition,
                            rule.severity.value,
                            rule.enabled,
                            json.dumps([ch.value for ch in rule.notification_channels]),
                            rule.threshold_value,
                            rule.check_interval_minutes,
                            rule.cooldown_minutes,
                            rule.escalation_minutes,
                        ),
                    )

                conn.commit()

        except Exception as e:
            self.logger.log_error(f"Error saving default rules: {e}")

    def _start_monitoring(self):
        """Start system monitoring"""
        if self._monitoring_running:
            return

        self._monitoring_running = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self._monitoring_thread.start()

        self.logger.log_action_end("Alert monitoring started")

    def _stop_monitoring(self):
        """Stop system monitoring"""
        if not self._monitoring_running:
            return

        self._monitoring_running = False

        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)

        self.logger.log_action_end("Alert monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_running:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                self._system_metrics = metrics
                self._last_check_time = datetime.now()

                # Store metrics in database
                self._store_metrics(metrics)

                # Check alert rules
                self._check_alert_rules(metrics)

                # Clean up old data
                self._cleanup_old_data()

                # Sleep until next check
                interval = self.config.get("check_interval_minutes", 5)
                time.sleep(interval * 60)

            except Exception as e:
                self.logger.log_error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # Network and process info
            network = psutil.net_io_counters()
            active_connections = len(psutil.net_connections())

            # Application-specific metrics (placeholder)
            query_count = self._get_query_count()
            avg_query_time = self._get_avg_query_time()

            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "active_connections": active_connections,
                "query_count": query_count,
                "avg_query_time_ms": avg_query_time,
            }

        except Exception as e:
            self.logger.log_error(f"Error collecting system metrics: {e}")
            return {}

    def _store_metrics(self, metrics: Dict[str, Any]):
        """Store metrics in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO system_metrics 
                    (timestamp, cpu_percent, memory_percent, disk_percent, 
                     active_connections, query_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        metrics["timestamp"],
                        metrics.get("cpu_percent", 0),
                        metrics.get("memory_percent", 0),
                        metrics.get("disk_percent", 0),
                        metrics.get("active_connections", 0),
                        metrics.get("query_count", 0),
                    ),
                )
                conn.commit()

        except Exception as e:
            self.logger.log_error(f"Error storing metrics: {e}")

    def _check_alert_rules(self, metrics: Dict[str, Any]):
        """Check all active alert rules against current metrics"""
        for rule_id, rule in self._active_rules.items():
            try:
                if not rule.enabled:
                    continue

                # Check if rule condition is met
                if self._evaluate_rule_condition(rule, metrics):
                    # Check if we're in cooldown period
                    if not self._is_in_cooldown(rule_id):
                        self._trigger_alert(rule, metrics)

            except Exception as e:
                self.logger.log_error(f"Error checking rule {rule_id}: {e}")

    def _evaluate_rule_condition(
        self, rule: AlertRule, metrics: Dict[str, Any]
    ) -> bool:
        """Evaluate if a rule condition is met"""
        try:
            if rule.condition == "cpu_percent > threshold":
                return metrics.get("cpu_percent", 0) > rule.threshold_value

            elif rule.condition == "memory_percent > threshold":
                return metrics.get("memory_percent", 0) > rule.threshold_value

            elif rule.condition == "disk_percent > threshold":
                return metrics.get("disk_percent", 0) > rule.threshold_value

            elif rule.condition == "avg_query_time > threshold":
                return metrics.get("avg_query_time_ms", 0) > rule.threshold_value

            elif rule.condition == "service_status == 'down'":
                # Placeholder for service health check
                return self._check_service_health() == "down"

            return False

        except Exception as e:
            self.logger.log_error(f"Error evaluating rule condition: {e}")
            return False

    def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Trigger an alert based on rule"""
        try:
            alert_id = f"{rule.id}_{int(time.time())}"

            # Create alert
            alert = Alert(
                id=alert_id,
                title=rule.name,
                description=self._format_alert_description(rule, metrics),
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                source="system_monitor",
                metadata={
                    "rule_id": rule.id,
                    "metrics": metrics,
                    "threshold": rule.threshold_value,
                },
            )

            # Save alert to database
            self._save_alert(alert)

            # Send notifications
            self._send_notifications(alert, rule.notification_channels)

            self.logger.log_action_end(f"Alert triggered: {rule.name}")

        except Exception as e:
            self.logger.log_error(f"Error triggering alert: {e}")

    def _format_alert_description(
        self, rule: AlertRule, metrics: Dict[str, Any]
    ) -> str:
        """Format alert description with current metrics"""
        base_desc = rule.description

        if rule.id == "cpu_high":
            return f"{base_desc}. Current: {metrics.get('cpu_percent', 0):.1f}%, Threshold: {rule.threshold_value}%"

        elif rule.id == "memory_high":
            return f"{base_desc}. Current: {metrics.get('memory_percent', 0):.1f}%, Threshold: {rule.threshold_value}%"

        elif rule.id == "disk_full":
            return f"{base_desc}. Current: {metrics.get('disk_percent', 0):.1f}%, Threshold: {rule.threshold_value}%"

        elif rule.id == "query_slow":
            return f"{base_desc}. Average: {metrics.get('avg_query_time_ms', 0):.0f}ms, Threshold: {rule.threshold_value}ms"

        return base_desc

    def _save_alert(self, alert: Alert):
        """Save alert to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO alerts 
                    (id, title, description, severity, status, created_at, updated_at,
                     source, metadata, resolved_at, acknowledged_by, escalated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        alert.id,
                        alert.title,
                        alert.description,
                        alert.severity.value,
                        alert.status.value,
                        alert.created_at,
                        alert.updated_at,
                        alert.source,
                        json.dumps(alert.metadata),
                        alert.resolved_at,
                        alert.acknowledged_by,
                        alert.escalated_at,
                    ),
                )
                conn.commit()

        except Exception as e:
            self.logger.log_error(f"Error saving alert: {e}")

    def _send_notifications(self, alert: Alert, channels: List[NotificationChannel]):
        """Send notifications through specified channels"""
        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL and self.config.get(
                    "email_notifications", False
                ):
                    self._send_email_notification(alert)

                elif channel == NotificationChannel.SMS and self.config.get(
                    "sms_notifications", False
                ):
                    self._send_sms_notification(alert)

                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook_notification(alert)

                elif channel == NotificationChannel.DESKTOP:
                    self._send_desktop_notification(alert)

            except Exception as e:
                self.logger.log_error(
                    f"Error sending {channel.value} notification: {e}"
                )

    def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        try:
            if not self._check_rate_limit(NotificationChannel.EMAIL):
                return

            # Email configuration
            smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
            smtp_port = self.config.get("smtp_port", 587)
            from_email = self.config.get("from_email", "")

            if not from_email:
                self.logger.log_error(
                    "No from_email configured for email notifications"
                )
                return

            if not MimeMultipart or not MimeText:
                self.logger.log_error("Email MIME modules not available")
                return

            # Create email message
            msg = MimeMultipart()
            msg["From"] = from_email
            msg["To"] = from_email  # For now, send to same address
            msg["Subject"] = (
                f"🚨 RedshiftManager Alert: {alert.title} [{alert.severity.value.upper()}]"
            )

            # Email body
            body = self._create_email_body(alert)
            msg.attach(MimeText(body, "html"))

            # Send email (placeholder - would need actual SMTP credentials)
            self.logger.log_action_end(f"Email notification sent for alert: {alert.id}")

        except Exception as e:
            self.logger.log_error(f"Error sending email notification: {e}")

    def _create_email_body(self, alert: Alert) -> str:
        """Create HTML email body for alert"""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107",
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545",
        }

        color = severity_colors.get(alert.severity, "#6c757d")

        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                    <h2>🚨 RedshiftManager Alert</h2>
                    <h3>{alert.title}</h3>
                    <p><strong>Severity: {alert.severity.value.upper()}</strong></p>
                </div>
                
                <div style="padding: 20px; background-color: #f8f9fa;">
                    <h4>Alert Details:</h4>
                    <p><strong>Description:</strong> {alert.description}</p>
                    <p><strong>Time:</strong> {alert.created_at}</p>
                    <p><strong>Source:</strong> {alert.source}</p>
                    <p><strong>Alert ID:</strong> {alert.id}</p>
                </div>
                
                <div style="padding: 20px;">
                    <h4>System Information:</h4>
                    <p>Please check the RedshiftManager dashboard for more details.</p>
                    <p>If this is a critical alert, please take immediate action.</p>
                </div>
                
                <div style="background-color: #e9ecef; padding: 10px; text-align: center; font-size: 12px;">
                    <p>This is an automated message from RedshiftManager Alert System</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _send_sms_notification(self, alert: Alert):
        """Send SMS notification (placeholder)"""
        # In a real implementation, this would integrate with SMS API like Twilio
        self.logger.log_action_end(
            f"SMS notification would be sent for alert: {alert.id}"
        )

    def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification (placeholder)"""
        # In a real implementation, this would send HTTP POST to webhook URL
        self.logger.log_action_end(
            f"Webhook notification would be sent for alert: {alert.id}"
        )

    def _send_desktop_notification(self, alert: Alert):
        """Send desktop notification (placeholder)"""
        # In a real implementation, this would show system notification
        self.logger.log_action_end(
            f"Desktop notification would be shown for alert: {alert.id}"
        )

    def _check_rate_limit(self, channel: NotificationChannel) -> bool:
        """Check if notification is within rate limits"""
        try:
            max_per_hour = self.config.get("max_alerts_per_hour", 10)
            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)

            # Clean old entries
            self._alert_count = {
                ch: count
                for ch, (hour, count) in self._alert_count.items()
                if hour >= current_hour - timedelta(hours=1)
            }

            # Check current count
            channel_key = channel.value
            if channel_key in self._alert_count:
                hour, count = self._alert_count[channel_key]
                if hour == current_hour and count >= max_per_hour:
                    return False
                elif hour == current_hour:
                    self._alert_count[channel_key] = (hour, count + 1)
                else:
                    self._alert_count[channel_key] = (current_hour, 1)
            else:
                self._alert_count[channel_key] = (current_hour, 1)

            return True

        except Exception as e:
            self.logger.log_error(f"Error checking rate limit: {e}")
            return True  # Allow notification on error

    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period"""
        # Placeholder implementation
        return False

    def _get_query_count(self) -> int:
        """Get current query count (placeholder)"""
        # In a real implementation, this would query the database
        return 0

    def _get_avg_query_time(self) -> float:
        """Get average query time in milliseconds (placeholder)"""
        # In a real implementation, this would calculate from query logs
        return 0.0

    def _check_service_health(self) -> str:
        """Check service health status"""
        # In a real implementation, this would check service endpoints
        return "up"

    def _cleanup_old_data(self):
        """Clean up old alerts and metrics"""
        try:
            retention_days = self.config.get("alert_retention_days", 30)
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cutoff_str = cutoff_date.isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Delete old resolved alerts
                cursor.execute(
                    "DELETE FROM alerts WHERE status = 'resolved' AND created_at < ?",
                    (cutoff_str,),
                )

                # Delete old metrics (keep only last 7 days)
                metrics_cutoff = datetime.now() - timedelta(days=7)
                cursor.execute(
                    "DELETE FROM system_metrics WHERE timestamp < ?",
                    (metrics_cutoff.isoformat(),),
                )

                conn.commit()

        except Exception as e:
            self.logger.log_error(f"Error cleaning up old data: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM alerts WHERE status IN ('active', 'escalated') ORDER BY created_at DESC"
                )
                rows = cursor.fetchall()

                alerts = []
                for row in rows:
                    alert = Alert(
                        id=row[0],
                        title=row[1],
                        description=row[2],
                        severity=AlertSeverity(row[3]),
                        status=AlertStatus(row[4]),
                        created_at=row[5],
                        updated_at=row[6],
                        source=row[7],
                        metadata=json.loads(row[8]) if row[8] else {},
                        resolved_at=row[9],
                        acknowledged_by=row[10],
                        escalated_at=row[11],
                    )
                    alerts.append(alert)

                return alerts

        except Exception as e:
            self.logger.log_error(f"Error getting active alerts: {e}")
            return []

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE alerts 
                    SET status = 'acknowledged', acknowledged_by = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (user, datetime.now().isoformat(), alert_id),
                )

                conn.commit()

                if cursor.rowcount > 0:
                    self.logger.log_action_end(
                        f"Alert acknowledged: {alert_id} by {user}"
                    )
                    return True

        except Exception as e:
            self.logger.log_error(f"Error acknowledging alert: {e}")

        return False

    def resolve_alert(self, alert_id: str, user: str) -> bool:
        """Resolve an alert"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE alerts 
                    SET status = 'resolved', resolved_at = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (datetime.now().isoformat(), datetime.now().isoformat(), alert_id),
                )

                conn.commit()

                if cursor.rowcount > 0:
                    self.logger.log_action_end(f"Alert resolved: {alert_id} by {user}")
                    return True

        except Exception as e:
            self.logger.log_error(f"Error resolving alert: {e}")

        return False

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return self._system_metrics.copy()

    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get system metrics history"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM system_metrics 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1000
                """,
                    (start_time.isoformat(),),
                )

                rows = cursor.fetchall()

                metrics = []
                for row in rows:
                    metrics.append(
                        {
                            "timestamp": row[1],
                            "cpu_percent": row[2],
                            "memory_percent": row[3],
                            "disk_percent": row[4],
                            "active_connections": row[5],
                            "query_count": row[6],
                        }
                    )

                return metrics

        except Exception as e:
            self.logger.log_error(f"Error getting metrics history: {e}")
            return []

    def _get_active_alerts_count(self) -> int:
        """Get count of active alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM alerts WHERE status IN ('active', 'escalated')"
                )
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def _get_enabled_channels(self) -> List[str]:
        """Get list of enabled notification channels"""
        channels = []
        if self.config.get("email_notifications"):
            channels.append("email")
        if self.config.get("sms_notifications"):
            channels.append("sms")
        return channels

    def export_configuration(self) -> str:
        """Export alert configuration as JSON"""
        return json.dumps(
            {
                "module": "alert_system",
                "version": "1.0.0",
                "config": self.config,
                "active_rules": len(self._active_rules),
                "monitoring_status": (
                    "active" if self._monitoring_running else "inactive"
                ),
            },
            indent=2,
        )
