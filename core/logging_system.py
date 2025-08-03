#!/usr/bin/env python3
"""
מערכת לוגים כללית ומקיפה עבור RedshiftManager
Comprehensive logging system for RedshiftManager
"""

import json
import logging
import logging.handlers
import os
import sqlite3
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class JSONFormatter(logging.Formatter):
    """Formatter לוגים ב-JSON format עם metadata"""

    def __init__(self):
        super().__init__()

    def format(self, record):
        """פורמט הלוג ל-JSON עם מטה-דאטה מלא"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process,
        }

        # הוספת context אם קיים
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "cluster_id"):
            log_entry["cluster_id"] = record.cluster_id
        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation
        if hasattr(record, "duration"):
            log_entry["duration_ms"] = record.duration

        # הוספת exception info אם קיים
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # הוספת extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class DatabaseHandler(logging.Handler):
    """Handler לשמירת לוגים בבסיס נתונים SQLite"""

    def __init__(self, db_path: str = "logs/logs.db"):
        super().__init__()
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """יצירת טבלת הלוגים בבסיס הנתונים"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                logger TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                function TEXT,
                line INTEGER,
                thread INTEGER,
                process INTEGER,
                user_id TEXT,
                session_id TEXT,
                cluster_id TEXT,
                operation TEXT,
                duration_ms REAL,
                exception_type TEXT,
                exception_message TEXT,
                traceback TEXT,
                extra_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # יצירת אינדקסים לביצועים טובים יותר
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_level ON logs(level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logger ON logs(logger)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation ON logs(operation)")

        conn.commit()
        conn.close()

    def emit(self, record):
        """שמירת הלוג בבסיס הנתונים"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # הכנת הנתונים לשמירה
            timestamp = datetime.fromtimestamp(record.created).isoformat()
            user_id = getattr(record, "user_id", None)
            session_id = getattr(record, "session_id", None)
            cluster_id = getattr(record, "cluster_id", None)
            operation = getattr(record, "operation", None)
            duration_ms = getattr(record, "duration", None)

            exception_type = None
            exception_message = None
            traceback_str = None

            if record.exc_info:
                exception_type = record.exc_info[0].__name__
                exception_message = str(record.exc_info[1])
                traceback_str = "".join(traceback.format_exception(*record.exc_info))

            # איסוף extra data
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "user_id",
                    "session_id",
                    "cluster_id",
                    "operation",
                    "duration",
                ]:
                    extra_data[key] = value

            cursor.execute(
                """
                INSERT INTO logs (
                    timestamp, level, logger, message, module, function, line,
                    thread, process, user_id, session_id, cluster_id, operation,
                    duration_ms, exception_type, exception_message, traceback, extra_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    record.levelname,
                    record.name,
                    record.getMessage(),
                    record.module,
                    record.funcName,
                    record.lineno,
                    record.thread,
                    record.process,
                    user_id,
                    session_id,
                    cluster_id,
                    operation,
                    duration_ms,
                    exception_type,
                    exception_message,
                    traceback_str,
                    json.dumps(extra_data) if extra_data else None,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            # אם נכשל בשמירה, נדפיס לקונסול
            print(f"Failed to save log to database: {e}")


class SlackHandler(logging.Handler):
    """Handler לשליחת התראות ל-Slack"""

    def __init__(self, webhook_url: str = None, level: int = logging.ERROR):
        super().__init__(level)
        self.webhook_url = webhook_url

    def emit(self, record):
        """שליחת התראה ל-Slack"""
        if not self.webhook_url:
            return

        try:
            import requests

            message = {
                "text": f"🚨 *RedshiftManager Alert*",
                "attachments": [
                    {
                        "color": "danger" if record.levelno >= logging.ERROR else "warning",
                        "fields": [
                            {"title": "Level", "value": record.levelname, "short": True},
                            {"title": "Logger", "value": record.name, "short": True},
                            {"title": "Message", "value": record.getMessage(), "short": False},
                            {"title": "Module", "value": record.module, "short": True},
                            {"title": "Function", "value": record.funcName, "short": True},
                            {
                                "title": "Time",
                                "value": datetime.fromtimestamp(record.created).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "short": True,
                            },
                        ],
                    }
                ],
            }

            requests.post(self.webhook_url, json=message, timeout=5)

        except Exception as e:
            print(f"Failed to send Slack notification: {e}")


class RedshiftManagerLogger:
    """מחלקה מרכזית לניהול כל מערכת הלוגים"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.loggers = {}
        self._setup_logging()

    def _default_config(self) -> Dict[str, Any]:
        """קונפיגורציה ברירת מחדל"""
        return {
            "log_dir": "logs",
            "log_level": "INFO",
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "backup_count": 10,
            "database_enabled": True,
            "console_enabled": True,
            "json_enabled": True,
            "slack_webhook": None,
            "retention_days": 30,
        }

    def _setup_logging(self):
        """הגדרת מערכת הלוגים"""
        # יצירת תיקיית לוגים
        os.makedirs(self.config["log_dir"], exist_ok=True)

        # הגדרת רמת לוגים
        log_level = getattr(logging, self.config["log_level"].upper())

        # יצירת formatters
        standard_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        json_formatter = JSONFormatter()

        # הגדרת root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # ניקוי handlers קיימים
        root_logger.handlers.clear()

        # Console handler
        if self.config["console_enabled"]:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(standard_formatter)
            root_logger.addHandler(console_handler)

        # File handler עם rotation
        file_handler = logging.handlers.RotatingFileHandler(
            f"{self.config['log_dir']}/redshift_manager.log",
            maxBytes=self.config["max_file_size"],
            backupCount=self.config["backup_count"],
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(standard_formatter)
        root_logger.addHandler(file_handler)

        # JSON file handler
        if self.config["json_enabled"]:
            json_handler = logging.handlers.RotatingFileHandler(
                f"{self.config['log_dir']}/redshift_manager.json",
                maxBytes=self.config["max_file_size"],
                backupCount=self.config["backup_count"],
                encoding="utf-8",
            )
            json_handler.setLevel(log_level)
            json_handler.setFormatter(json_formatter)
            root_logger.addHandler(json_handler)

        # Database handler
        if self.config["database_enabled"]:
            db_handler = DatabaseHandler(f"{self.config['log_dir']}/logs.db")
            db_handler.setLevel(log_level)
            root_logger.addHandler(db_handler)

        # Slack handler for errors
        if self.config["slack_webhook"]:
            slack_handler = SlackHandler(self.config["slack_webhook"], logging.ERROR)
            root_logger.addHandler(slack_handler)

        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            f"{self.config['log_dir']}/errors.log",
            maxBytes=self.config["max_file_size"],
            backupCount=self.config["backup_count"],
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(standard_formatter)
        root_logger.addHandler(error_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """קבלת logger עם השם הנתון"""
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]

    def log_operation(
        self,
        operation: str,
        level: str = "INFO",
        user_id: str = None,
        session_id: str = None,
        cluster_id: str = None,
        duration: float = None,
        **kwargs,
    ):
        """לוג פעולה עם context מלא"""
        logger = self.get_logger("operations")
        log_level = getattr(logging, level.upper())

        extra = {
            "operation": operation,
            "user_id": user_id,
            "session_id": session_id,
            "cluster_id": cluster_id,
            "duration": duration,
            **kwargs,
        }

        logger.log(log_level, f"Operation: {operation}", extra=extra)

    def log_query(
        self,
        query: str,
        cluster_id: str,
        user_id: str = None,
        duration: float = None,
        rows_affected: int = None,
        status: str = "SUCCESS",
    ):
        """לוג ביצוע שאילתה"""
        logger = self.get_logger("queries")

        extra = {
            "operation": "QUERY_EXECUTION",
            "cluster_id": cluster_id,
            "user_id": user_id,
            "duration": duration,
            "rows_affected": rows_affected,
            "status": status,
            "query_hash": hash(query),
            "query_length": len(query),
        }

        logger.info(f"Query executed on cluster {cluster_id}: {status}", extra=extra)

    def log_user_action(
        self, action: str, user_id: str, session_id: str = None, **kwargs
    ):
        """לוג פעולת משתמש"""
        logger = self.get_logger("user_actions")

        extra = {
            "operation": "USER_ACTION",
            "user_id": user_id,
            "session_id": session_id,
            "action": action,
            **kwargs,
        }

        logger.info(f"User action: {action}", extra=extra)

    def log_system_event(self, event: str, severity: str = "INFO", **kwargs):
        """לוג אירוע מערכת"""
        logger = self.get_logger("system")
        log_level = getattr(logging, severity.upper())

        extra = {
            "operation": "SYSTEM_EVENT",
            "event": event,
            **kwargs,
        }

        logger.log(log_level, f"System event: {event}", extra=extra)

    def cleanup_old_logs(self):
        """ניקוי לוגים ישנים"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config["retention_days"])

            # ניקוי מבסיס הנתונים
            if self.config["database_enabled"]:
                conn = sqlite3.connect(f"{self.config['log_dir']}/logs.db")
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM logs WHERE timestamp < ?", (cutoff_date.isoformat(),)
                )
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()

                self.log_system_event(
                    "LOG_CLEANUP", severity="INFO", deleted_count=deleted_count
                )

        except Exception as e:
            self.log_system_event(
                "LOG_CLEANUP_ERROR", severity="ERROR", error=str(e)
            )

    def get_logs(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        level: str = None,
        logger: str = None,
        operation: str = None,
        user_id: str = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """שליפת לוגים עם סינון"""
        try:
            conn = sqlite3.connect(f"{self.config['log_dir']}/logs.db")

            query = "SELECT * FROM logs WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            if level:
                query += " AND level = ?"
                params.append(level)

            if logger:
                query += " AND logger = ?"
                params.append(logger)

            if operation:
                query += " AND operation = ?"
                params.append(operation)

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            df = pd.read_sql_query(query, conn, params=params)
            conn.close()

            return df

        except Exception as e:
            print(f"Error querying logs: {e}")
            return pd.DataFrame()

    def get_log_statistics(self) -> Dict[str, Any]:
        """סטטיסטיקות על הלוגים"""
        try:
            conn = sqlite3.connect(f"{self.config['log_dir']}/logs.db")

            stats = {}

            # ספירה כללית
            cursor = conn.execute("SELECT COUNT(*) FROM logs")
            stats["total_logs"] = cursor.fetchone()[0]

            # ספירה לפי רמות
            cursor = conn.execute(
                "SELECT level, COUNT(*) FROM logs GROUP BY level ORDER BY COUNT(*) DESC"
            )
            stats["by_level"] = dict(cursor.fetchall())

            # ספירה לפי logger
            cursor = conn.execute(
                "SELECT logger, COUNT(*) FROM logs GROUP BY logger ORDER BY COUNT(*) DESC LIMIT 10"
            )
            stats["by_logger"] = dict(cursor.fetchall())

            # לוגים מהיום האחרון
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor = conn.execute(
                "SELECT COUNT(*) FROM logs WHERE timestamp >= ?", (yesterday,)
            )
            stats["last_24h"] = cursor.fetchone()[0]

            # שגיאות מהשבוע האחרון
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor = conn.execute(
                "SELECT COUNT(*) FROM logs WHERE level IN ('ERROR', 'CRITICAL') AND timestamp >= ?",
                (week_ago,),
            )
            stats["errors_last_week"] = cursor.fetchone()[0]

            conn.close()
            return stats

        except Exception as e:
            print(f"Error getting log statistics: {e}")
            return {}


# יצירת instance גלובלי
logger_system = RedshiftManagerLogger()

# קיצורי דרך לשימוש נוח
def get_logger(name: str) -> logging.Logger:
    """קבלת logger"""
    return logger_system.get_logger(name)


def log_operation(operation: str, level: str = "INFO", user_id: str = None, session_id: str = None, **kwargs):
    """לוג פעולה"""
    return logger_system.log_operation(operation, level, user_id, session_id, **kwargs)


def log_query(**kwargs):
    """לוג שאילתה"""
    return logger_system.log_query(**kwargs)


def log_user_action(action: str, user_id: str, session_id: str = None, **kwargs):
    """לוג פעולת משתמש"""
    return logger_system.log_user_action(action, user_id, session_id, **kwargs)


def log_system_event(event: str, severity: str = "INFO", **kwargs):
    """לוג אירוע מערכת"""
    return logger_system.log_system_event(event, severity, **kwargs)