"""
Backup Manager Module
Core backup and restore functionality for RedshiftManager.
"""

import json
import logging
import os
import shutil

# Add project root to path
import sys
import threading
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import schedule

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.logging_system import RedshiftLogger
from utils.user_preferences import UserPreferencesManager

from core.plugin_interface import ModuleBase


class BackupManager(ModuleBase):
    """
    Main backup manager class implementing comprehensive backup functionality
    """

    def __init__(self):
        self.logger = RedshiftLogger()
        self.prefs_manager = UserPreferencesManager()
        self._config = self._load_config()
        self.backup_dir = Path(self.config.get("backup_location", "./backup"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._scheduler_thread = None
        self._scheduler_running = False

        self.logger.log_action_start("Backup Manager initialized")

    @property
    def config(self):
        """Get current configuration"""
        return self._config

    @config.setter
    def config(self, value):
        """Set configuration"""
        self._config = value

    def initialize(self) -> bool:
        """Initialize the backup module"""
        try:
            self._setup_backup_directory()
            self._start_scheduler()
            self.logger.log_action_end("Backup Manager initialized successfully")
            return True
        except Exception as e:
            self.logger.log_error(f"Failed to initialize Backup Manager: {e}")
            return False

    def cleanup(self) -> bool:
        """Cleanup backup module resources"""
        try:
            self._stop_scheduler()
            self.logger.log_action_end("Backup Manager cleanup completed")
            return True
        except Exception as e:
            self.logger.log_error(f"Error during Backup Manager cleanup: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            "name": "backup_module",
            "display_name": "System Backup Manager",
            "version": "1.0.0",
            "status": "active" if self._scheduler_running else "inactive",
            "backup_count": self._get_backup_count(),
            "last_backup": self._get_last_backup_time(),
            "next_backup": self._get_next_backup_time(),
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load backup configuration"""
        try:
            config_path = (
                project_root / "data" / "module_configs" / "backup_module.json"
            )
            if config_path.exists():
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                    return config_data.get("custom", {})

            # Default configuration
            return {
                "backup_frequency": "daily",
                "backup_location": "./backup",
                "compress_backups": True,
                "retention_days": 30,
                "include_user_data": True,
                "include_logs": False,
                "encrypt_backups": False,
            }
        except Exception as e:
            self.logger.log_error(f"Error loading backup config: {e}")
            return {}

    def _setup_backup_directory(self):
        """Setup backup directory structure"""
        directories = [
            "full_backups",
            "incremental_backups",
            "config_backups",
            "user_backups",
            "temp",
        ]

        for dir_name in directories:
            (self.backup_dir / dir_name).mkdir(parents=True, exist_ok=True)

    def _start_scheduler(self):
        """Start the backup scheduler"""
        if self._scheduler_running:
            return

        frequency = self.config.get("backup_frequency", "daily")

        if frequency == "hourly":
            schedule.every().hour.do(self._scheduled_backup)
        elif frequency == "daily":
            schedule.every().day.at("02:00").do(self._scheduled_backup)
        elif frequency == "weekly":
            schedule.every().week.do(self._scheduled_backup)
        # Manual frequency doesn't schedule automatic backups

        if frequency != "manual":
            self._scheduler_running = True
            self._scheduler_thread = threading.Thread(
                target=self._run_scheduler, daemon=True
            )
            self._scheduler_thread.start()

            self.logger.log_action_end(
                f"Backup scheduler started with {frequency} frequency"
            )

    def _stop_scheduler(self):
        """Stop the backup scheduler"""
        if not self._scheduler_running:
            return

        self._scheduler_running = False
        schedule.clear()

        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)

        self.logger.log_action_end("Backup scheduler stopped")

    def _run_scheduler(self):
        """Run the backup scheduler loop"""
        while self._scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def _scheduled_backup(self):
        """Perform scheduled backup"""
        try:
            self.logger.log_action_start("Scheduled backup started")
            self.create_full_backup(auto_generated=True)
            self._cleanup_old_backups()
        except Exception as e:
            self.logger.log_error(f"Scheduled backup failed: {e}")

    def create_full_backup(
        self, backup_name: Optional[str] = None, auto_generated: bool = False
    ) -> Tuple[bool, str]:
        """
        Create a complete system backup

        Args:
            backup_name: Custom name for the backup
            auto_generated: Whether this is an automatic backup

        Returns:
            Tuple of (success, backup_file_path)
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if not backup_name:
                prefix = "auto" if auto_generated else "manual"
                backup_name = f"{prefix}_backup_{timestamp}"

            self.logger.log_action_start(f"Creating full backup: {backup_name}")

            # Create temporary directory for backup preparation
            temp_dir = self.backup_dir / "temp" / backup_name
            temp_dir.mkdir(parents=True, exist_ok=True)

            try:
                # Backup system configurations
                self._backup_system_config(temp_dir)

                # Backup user data if enabled
                if self.config.get("include_user_data", True):
                    self._backup_user_data(temp_dir)

                # Backup module configurations
                self._backup_module_configs(temp_dir)

                # Backup database connections
                self._backup_database_connections(temp_dir)

                # Backup application settings
                self._backup_app_settings(temp_dir)

                # Include logs if enabled
                if self.config.get("include_logs", False):
                    self._backup_logs(temp_dir)

                # Create metadata
                self._create_backup_metadata(temp_dir, backup_name, auto_generated)

                # Compress backup if enabled
                if self.config.get("compress_backups", True):
                    backup_file = (
                        self.backup_dir / "full_backups" / f"{backup_name}.zip"
                    )
                    self._create_zip_backup(temp_dir, backup_file)
                else:
                    backup_file = self.backup_dir / "full_backups" / backup_name
                    shutil.copytree(temp_dir, backup_file)

                # Encrypt if enabled
                if self.config.get("encrypt_backups", False):
                    backup_file = self._encrypt_backup(backup_file)

                self.logger.log_action_end(
                    f"Full backup created successfully: {backup_file}"
                )
                return True, str(backup_file)

            finally:
                # Cleanup temporary directory
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

        except Exception as e:
            self.logger.log_error(f"Failed to create full backup: {e}")
            return False, str(e)

    def _backup_system_config(self, temp_dir: Path):
        """Backup system configuration files"""
        config_dir = temp_dir / "system_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Backup main configuration files
        config_files = [
            "config/app_settings.json",
            "config/session.json",
            "config/system.json",
            "requirements.txt",
        ]

        for config_file in config_files:
            source_path = project_root / config_file
            if source_path.exists():
                dest_path = config_dir / Path(config_file).name
                shutil.copy2(source_path, dest_path)

    def _backup_user_data(self, temp_dir: Path):
        """Backup user preferences and personal data"""
        user_dir = temp_dir / "user_data"
        user_dir.mkdir(parents=True, exist_ok=True)

        # Backup user preferences
        prefs_source = project_root / "data" / "user_preferences"
        if prefs_source.exists():
            prefs_dest = user_dir / "user_preferences"
            shutil.copytree(prefs_source, prefs_dest)

        # Backup users.json
        users_source = project_root / "data" / "users.json"
        if users_source.exists():
            shutil.copy2(users_source, user_dir / "users.json")

    def _backup_module_configs(self, temp_dir: Path):
        """Backup module configuration files"""
        modules_dir = temp_dir / "module_configs"
        modules_dir.mkdir(parents=True, exist_ok=True)

        # Backup module configs
        configs_source = project_root / "data" / "module_configs"
        if configs_source.exists():
            for config_file in configs_source.glob("*.json"):
                shutil.copy2(config_file, modules_dir / config_file.name)

    def _backup_database_connections(self, temp_dir: Path):
        """Backup database connection configurations"""
        db_dir = temp_dir / "database_connections"
        db_dir.mkdir(parents=True, exist_ok=True)

        # This would backup database connection info from user preferences
        # Note: Passwords should be handled securely
        all_users_prefs = {}

        prefs_dir = project_root / "data" / "user_preferences"
        if prefs_dir.exists():
            for pref_file in prefs_dir.glob("*.json"):
                try:
                    with open(pref_file, "r") as f:
                        user_prefs = json.load(f)

                    # Remove sensitive data like passwords for security
                    if "database_connections" in user_prefs:
                        for conn in user_prefs["database_connections"]:
                            if "password" in conn:
                                conn["password"] = "***ENCRYPTED***"

                    all_users_prefs[pref_file.stem] = user_prefs
                except Exception as e:
                    self.logger.log_error(
                        f"Error backing up user preferences {pref_file}: {e}"
                    )

        # Save sanitized preferences
        with open(db_dir / "user_database_configs.json", "w") as f:
            json.dump(all_users_prefs, f, indent=2)

    def _backup_app_settings(self, temp_dir: Path):
        """Backup application-specific settings"""
        app_dir = temp_dir / "app_settings"
        app_dir.mkdir(parents=True, exist_ok=True)

        # Backup localization files
        locales_source = project_root / "locales"
        if locales_source.exists():
            locales_dest = app_dir / "locales"
            shutil.copytree(locales_source, locales_dest)

        # Backup translations
        translations_source = project_root / "translations"
        if translations_source.exists():
            translations_dest = app_dir / "translations"
            shutil.copytree(translations_source, translations_dest)

    def _backup_logs(self, temp_dir: Path):
        """Backup system logs"""
        logs_dir = temp_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        logs_source = project_root / "logs"
        if logs_source.exists():
            # Only backup recent logs (last 7 days)
            cutoff_date = datetime.now() - timedelta(days=7)

            for log_file in logs_source.glob("*.log"):
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time > cutoff_date:
                        shutil.copy2(log_file, logs_dir / log_file.name)
                except Exception as e:
                    self.logger.log_error(f"Error backing up log file {log_file}: {e}")

    def _create_backup_metadata(
        self, temp_dir: Path, backup_name: str, auto_generated: bool
    ):
        """Create backup metadata file"""
        metadata = {
            "backup_name": backup_name,
            "created_at": datetime.now().isoformat(),
            "auto_generated": auto_generated,
            "version": "1.0.0",
            "system_info": {
                "platform": os.name,
                "python_version": sys.version,
            },
            "backup_config": self.config.copy(),
            "components": {
                "system_config": True,
                "user_data": self.config.get("include_user_data", True),
                "module_configs": True,
                "database_connections": True,
                "app_settings": True,
                "logs": self.config.get("include_logs", False),
            },
        }

        metadata_file = temp_dir / "backup_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def _create_zip_backup(self, source_dir: Path, backup_file: Path):
        """Create compressed zip backup"""
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)

    def _encrypt_backup(self, backup_file: Path) -> Path:
        """Encrypt backup file (placeholder implementation)"""
        # In a real implementation, this would use proper encryption
        encrypted_file = backup_file.with_suffix(backup_file.suffix + ".encrypted")
        shutil.move(backup_file, encrypted_file)
        return encrypted_file

    def restore_backup(self, backup_file: str) -> Tuple[bool, str]:
        """
        Restore system from backup

        Args:
            backup_file: Path to backup file

        Returns:
            Tuple of (success, message)
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                return False, f"Backup file not found: {backup_file}"

            self.logger.log_action_start(f"Restoring backup: {backup_path.name}")

            # Create temporary restore directory
            temp_restore_dir = (
                self.backup_dir
                / "temp"
                / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            temp_restore_dir.mkdir(parents=True, exist_ok=True)

            try:
                # Extract backup
                if backup_path.suffix == ".zip":
                    with zipfile.ZipFile(backup_path, "r") as zipf:
                        zipf.extractall(temp_restore_dir)
                else:
                    shutil.copytree(backup_path, temp_restore_dir / "backup_content")
                    temp_restore_dir = temp_restore_dir / "backup_content"

                # Validate backup
                metadata_file = temp_restore_dir / "backup_metadata.json"
                if not metadata_file.exists():
                    return False, "Invalid backup: metadata not found"

                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                # Restore components
                success_count = 0

                if (temp_restore_dir / "system_config").exists():
                    if self._restore_system_config(temp_restore_dir / "system_config"):
                        success_count += 1

                if (temp_restore_dir / "user_data").exists():
                    if self._restore_user_data(temp_restore_dir / "user_data"):
                        success_count += 1

                if (temp_restore_dir / "module_configs").exists():
                    if self._restore_module_configs(
                        temp_restore_dir / "module_configs"
                    ):
                        success_count += 1

                self.logger.log_action_end(
                    f"Backup restored successfully: {success_count} components"
                )
                return (
                    True,
                    f"Backup restored successfully. {success_count} components restored.",
                )

            finally:
                # Cleanup temporary directory
                if temp_restore_dir.exists():
                    shutil.rmtree(temp_restore_dir.parent)

        except Exception as e:
            self.logger.log_error(f"Failed to restore backup: {e}")
            return False, str(e)

    def _restore_system_config(self, config_dir: Path) -> bool:
        """Restore system configuration files"""
        try:
            for config_file in config_dir.glob("*.json"):
                dest_path = project_root / "config" / config_file.name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_file, dest_path)
            return True
        except Exception as e:
            self.logger.log_error(f"Error restoring system config: {e}")
            return False

    def _restore_user_data(self, user_dir: Path) -> bool:
        """Restore user data"""
        try:
            # Restore user preferences
            prefs_source = user_dir / "user_preferences"
            if prefs_source.exists():
                prefs_dest = project_root / "data" / "user_preferences"
                if prefs_dest.exists():
                    shutil.rmtree(prefs_dest)
                shutil.copytree(prefs_source, prefs_dest)

            # Restore users.json
            users_source = user_dir / "users.json"
            if users_source.exists():
                users_dest = project_root / "data" / "users.json"
                shutil.copy2(users_source, users_dest)

            return True
        except Exception as e:
            self.logger.log_error(f"Error restoring user data: {e}")
            return False

    def _restore_module_configs(self, modules_dir: Path) -> bool:
        """Restore module configurations"""
        try:
            dest_dir = project_root / "data" / "module_configs"
            dest_dir.mkdir(parents=True, exist_ok=True)

            for config_file in modules_dir.glob("*.json"):
                dest_path = dest_dir / config_file.name
                shutil.copy2(config_file, dest_path)

            return True
        except Exception as e:
            self.logger.log_error(f"Error restoring module configs: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []

        backup_dirs = [
            self.backup_dir / "full_backups",
            self.backup_dir / "incremental_backups",
        ]

        for backup_dir in backup_dirs:
            if not backup_dir.exists():
                continue

            for backup_file in backup_dir.iterdir():
                if backup_file.is_file() or backup_file.is_dir():
                    try:
                        stat = backup_file.stat()
                        backups.append(
                            {
                                "name": backup_file.name,
                                "path": str(backup_file),
                                "size": (
                                    stat.st_size
                                    if backup_file.is_file()
                                    else self._get_dir_size(backup_file)
                                ),
                                "created_at": datetime.fromtimestamp(
                                    stat.st_ctime
                                ).isoformat(),
                                "modified_at": datetime.fromtimestamp(
                                    stat.st_mtime
                                ).isoformat(),
                                "type": (
                                    "full"
                                    if "full_backups" in str(backup_file)
                                    else "incremental"
                                ),
                                "compressed": backup_file.suffix == ".zip",
                            }
                        )
                    except Exception as e:
                        self.logger.log_error(
                            f"Error reading backup info for {backup_file}: {e}"
                        )

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups

    def delete_backup(self, backup_path: str) -> Tuple[bool, str]:
        """Delete a backup file"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return False, "Backup file not found"

            if backup_file.is_file():
                backup_file.unlink()
            else:
                shutil.rmtree(backup_file)

            self.logger.log_action_end(f"Backup deleted: {backup_file.name}")
            return True, "Backup deleted successfully"

        except Exception as e:
            self.logger.log_error(f"Error deleting backup: {e}")
            return False, str(e)

    def _cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        try:
            retention_days = self.config.get("retention_days", 30)
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            for backup_info in self.list_backups():
                backup_date = datetime.fromisoformat(backup_info["created_at"])
                if backup_date < cutoff_date:
                    self.delete_backup(backup_info["path"])
                    self.logger.log_action_end(
                        f"Old backup cleaned up: {backup_info['name']}"
                    )

        except Exception as e:
            self.logger.log_error(f"Error cleaning up old backups: {e}")

    def _get_backup_count(self) -> int:
        """Get total number of backups"""
        return len(self.list_backups())

    def _get_last_backup_time(self) -> Optional[str]:
        """Get timestamp of last backup"""
        backups = self.list_backups()
        return backups[0]["created_at"] if backups else None

    def _get_next_backup_time(self) -> Optional[str]:
        """Get timestamp of next scheduled backup"""
        frequency = self.config.get("backup_frequency", "daily")
        if frequency == "manual":
            return None

        # This is a simplified implementation
        # In reality, you'd check the actual schedule
        if frequency == "hourly":
            next_backup = datetime.now() + timedelta(hours=1)
        elif frequency == "daily":
            next_backup = datetime.now().replace(
                hour=2, minute=0, second=0
            ) + timedelta(days=1)
        elif frequency == "weekly":
            next_backup = datetime.now() + timedelta(weeks=1)
        else:
            return None

        return next_backup.isoformat()

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory"""
        total_size = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
        return total_size

    def export_configuration(self) -> str:
        """Export backup configuration as JSON"""
        return json.dumps(
            {
                "module": "backup_manager",
                "version": "1.0.0",
                "config": self.config,
                "backup_stats": {
                    "total_backups": self._get_backup_count(),
                    "last_backup": self._get_last_backup_time(),
                    "backup_location": str(self.backup_dir),
                },
            },
            indent=2,
        )
