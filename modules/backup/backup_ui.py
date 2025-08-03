"""
Backup Module UI Components
Streamlit interface for backup management functionality.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.logging_system import RedshiftLogger

from modules.backup.backup_manager import BackupManager

# Auth decorators disabled for open access mode

logger = RedshiftLogger()


class BackupPanel:
    """Main backup management panel"""

    def __init__(self):
        self.backup_manager = BackupManager()
        self.backup_manager.initialize()

    def render(self):
        """Render the main backup panel"""
        st.subheader("💾 System Backup Manager")
        st.markdown(
            "Manage system backups, restore configurations, and schedule automatic backups."
        )
        st.markdown("---")

        # Create tabs for different backup operations
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Overview", "💾 Create Backup", "📋 Manage Backups", "⚖️ Settings"]
        )

        with tab1:
            self._render_overview()

        with tab2:
            self._render_create_backup()

        with tab3:
            self._render_manage_backups()

        with tab4:
            self._render_settings()

    def _render_overview(self):
        """Render backup overview dashboard"""
        st.markdown("#### 📊 Backup System Status")

        # Get backup statistics
        backups = self.backup_manager.list_backups()
        info = self.backup_manager.get_info()

        # Status metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Backups", len(backups))

        with col2:
            last_backup = info.get("last_backup")
            if last_backup:
                last_backup_dt = datetime.fromisoformat(last_backup)
                formatted_time = last_backup_dt.strftime("%m/%d %H:%M")
                st.metric("Last Backup", formatted_time)
            else:
                st.metric("Last Backup", "Never")

        with col3:
            next_backup = info.get("next_backup")
            if next_backup:
                next_backup_dt = datetime.fromisoformat(next_backup)
                formatted_time = next_backup_dt.strftime("%m/%d %H:%M")
                st.metric("Next Backup", formatted_time)
            else:
                st.metric("Next Backup", "Manual Only")

        with col4:
            status = info.get("status", "unknown")
            status_emoji = "🟢" if status == "active" else "🔴"
            st.metric("Status", f"{status_emoji} {status.title()}")

        st.markdown("---")

        # Recent backups
        if backups:
            st.markdown("#### 📋 Recent Backups")

            recent_backups = backups[:5]  # Show last 5 backups

            backup_data = []
            for backup in recent_backups:
                backup_data.append(
                    {
                        "Name": backup["name"],
                        "Type": backup["type"].title(),
                        "Size": self._format_size(backup["size"]),
                        "Created": datetime.fromisoformat(
                            backup["created_at"]
                        ).strftime("%Y-%m-%d %H:%M"),
                        "Compressed": "✅" if backup.get("compressed", False) else "❌",
                    }
                )

            st.dataframe(backup_data, use_container_width=True)
        else:
            st.info(
                "🔍 No backups found. Create your first backup using the 'Create Backup' tab."
            )

        # System health check
        st.markdown("#### 🏥 System Health")
        self._render_system_health()

    def _render_create_backup(self):
        """Render backup creation interface"""
        current_user = get_current_user()

        # Check permissions
        if not current_user or current_user.role not in [
            UserRole.ADMIN,
            UserRole.MANAGER,
        ]:
            st.warning("🔐 Manager or Admin permissions required to create backups")
            return

        st.markdown("#### 💾 Create New Backup")

        # Backup options
        col1, col2 = st.columns(2)

        with col1:
            backup_name = st.text_input(
                "Backup Name (optional)",
                placeholder="Leave empty for auto-generated name",
                help="Custom name for this backup",
            )

            backup_type = st.selectbox(
                "Backup Type",
                options=["Full Backup", "Configuration Only", "User Data Only"],
                help="Select what to include in the backup",
            )

        with col2:
            compress_backup = st.checkbox(
                "Compress Backup",
                value=True,
                help="Compress backup to save storage space",
            )

            include_logs = st.checkbox(
                "Include Recent Logs",
                value=False,
                help="Include system logs from the last 7 days",
            )

        # Advanced options
        with st.expander("🔧 Advanced Options"):
            encrypt_backup = st.checkbox(
                "Encrypt Backup",
                value=False,
                help="Encrypt backup for security (requires decryption key for restore)",
            )

            if encrypt_backup:
                st.warning(
                    "⚠️ Encrypted backups require the encryption key for restoration. Store it securely!"
                )

            custom_location = st.text_input(
                "Custom Backup Location",
                placeholder="Leave empty to use default location",
                help="Custom directory to store this backup",
            )

        # Create backup button
        st.markdown("---")

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("💾 Create Backup", type="primary", use_container_width=True):
                with st.spinner("Creating backup..."):
                    self._create_backup_with_options(
                        backup_name,
                        backup_type,
                        compress_backup,
                        include_logs,
                        encrypt_backup,
                        custom_location,
                    )

        with col2:
            if st.button("🧪 Test Backup", use_container_width=True):
                with st.spinner("Testing backup configuration..."):
                    self._test_backup_configuration()

        with col3:
            st.markdown(
                "*Backup creation may take several minutes depending on data size*"
            )

    def _render_manage_backups(self):
        """Render backup management interface"""
        st.markdown("#### 📋 Manage Existing Backups")

        backups = self.backup_manager.list_backups()

        if not backups:
            st.info("🔍 No backups found. Create your first backup to see it here.")
            return

        # Backup management table
        st.markdown("##### Available Backups")

        # Add selection column
        selected_backups = []

        for i, backup in enumerate(backups):
            col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 1, 1, 1, 1.5])

            with col1:
                select = st.checkbox("", key=f"select_{i}")
                if select:
                    selected_backups.append(backup)

            with col2:
                st.markdown(f"**{backup['name']}**")
                st.caption(f"Type: {backup['type'].title()}")

            with col3:
                st.markdown(self._format_size(backup["size"]))

            with col4:
                created_dt = datetime.fromisoformat(backup["created_at"])
                st.markdown(created_dt.strftime("%m/%d/%Y"))
                st.caption(created_dt.strftime("%H:%M:%S"))

            with col5:
                if backup.get("compressed", False):
                    st.success("✅ ZIP")
                else:
                    st.info("📁 Folder")

            with col6:
                # Individual backup actions
                col_restore, col_delete = st.columns(2)

                with col_restore:
                    if st.button("🔄", key=f"restore_{i}", help="Restore this backup"):
                        self._restore_backup(backup)

                with col_delete:
                    if st.button("🗑️", key=f"delete_{i}", help="Delete this backup"):
                        self._delete_backup(backup)

        # Bulk operations
        if selected_backups:
            st.markdown("---")
            st.markdown("##### Bulk Operations")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(
                    f"🗑️ Delete Selected ({len(selected_backups)})", type="secondary"
                ):
                    self._bulk_delete_backups(selected_backups)

            with col2:
                if st.button("📤 Export Selected", type="secondary"):
                    self._export_selected_backups(selected_backups)

            with col3:
                if st.button("📊 Compare Selected", type="secondary"):
                    if len(selected_backups) == 2:
                        self._compare_backups(selected_backups)
                    else:
                        st.warning("Please select exactly 2 backups to compare")

    def _render_settings(self):
        """Render backup settings interface"""
        current_user = get_current_user()

        # Check permissions
        if not current_user or current_user.role != UserRole.ADMIN:
            st.warning("🔐 Admin permissions required to modify backup settings")
            return

        st.markdown("#### ⚙️ Backup Settings")

        # Load current configuration
        current_config = self.backup_manager.config

        with st.form("backup_settings_form"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("##### 🕐 Scheduling")

                backup_frequency = st.selectbox(
                    "Automatic Backup Frequency",
                    options=["manual", "hourly", "daily", "weekly"],
                    index=["manual", "hourly", "daily", "weekly"].index(
                        current_config.get("backup_frequency", "daily")
                    ),
                    help="How often to create automatic backups",
                )

                retention_days = st.number_input(
                    "Backup Retention (days)",
                    min_value=1,
                    max_value=365,
                    value=current_config.get("retention_days", 30),
                    help="Number of days to keep backup files",
                )

                st.markdown("##### 💾 Storage")

                backup_location = st.text_input(
                    "Backup Location",
                    value=current_config.get("backup_location", "./backup"),
                    help="Directory to store backup files",
                )

                compress_backups = st.checkbox(
                    "Compress Backups by Default",
                    value=current_config.get("compress_backups", True),
                    help="Automatically compress backup files",
                )

            with col2:
                st.markdown("##### 📋 Content")

                include_user_data = st.checkbox(
                    "Include User Data",
                    value=current_config.get("include_user_data", True),
                    help="Include user preferences and personal data",
                )

                include_logs = st.checkbox(
                    "Include System Logs",
                    value=current_config.get("include_logs", False),
                    help="Include system logs in backups",
                )

                st.markdown("##### 🔐 Security")

                encrypt_backups = st.checkbox(
                    "Encrypt Backups by Default",
                    value=current_config.get("encrypt_backups", False),
                    help="Automatically encrypt backup files",
                )

                if encrypt_backups:
                    encryption_key = st.text_input(
                        "Encryption Key",
                        type="password",
                        help="Key used to encrypt/decrypt backups",
                    )

            # Save settings
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.form_submit_button("💾 Save Settings", type="primary"):
                    new_config = {
                        "backup_frequency": backup_frequency,
                        "retention_days": retention_days,
                        "backup_location": backup_location,
                        "compress_backups": compress_backups,
                        "include_user_data": include_user_data,
                        "include_logs": include_logs,
                        "encrypt_backups": encrypt_backups,
                    }

                    if self._save_backup_settings(new_config):
                        st.success("✅ Settings saved successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save settings")

            with col2:
                if st.form_submit_button("🔄 Reset to Defaults"):
                    if self._reset_backup_settings():
                        st.success("✅ Settings reset to defaults!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to reset settings")

        # Export/Import settings
        st.markdown("---")
        st.markdown("##### 📤 Export/Import Settings")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📤 Export Settings", use_container_width=True):
                config_json = self.backup_manager.export_configuration()
                st.download_button(
                    "💾 Download Configuration",
                    data=config_json,
                    file_name=f"backup_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )

        with col2:
            uploaded_file = st.file_uploader(
                "📤 Import Settings",
                type=["json"],
                help="Upload a backup configuration file",
            )

            if uploaded_file:
                try:
                    config_data = json.loads(uploaded_file.read())
                    if self._import_backup_settings(config_data):
                        st.success("✅ Settings imported successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to import settings")
                except Exception as e:
                    st.error(f"❌ Invalid configuration file: {e}")

    def _render_system_health(self):
        """Render system health information"""
        health_data = self._get_system_health()

        col1, col2, col3 = st.columns(3)

        with col1:
            storage_status = health_data["storage_status"]
            if storage_status == "healthy":
                st.success(f"💾 Storage: {storage_status.title()}")
            else:
                st.warning(f"💾 Storage: {storage_status.title()}")

        with col2:
            permissions_status = health_data["permissions_status"]
            if permissions_status == "healthy":
                st.success(f"🔐 Permissions: {permissions_status.title()}")
            else:
                st.error(f"🔐 Permissions: {permissions_status.title()}")

        with col3:
            scheduler_status = health_data["scheduler_status"]
            if scheduler_status == "running":
                st.success(f"⏰ Scheduler: {scheduler_status.title()}")
            else:
                st.info(f"⏰ Scheduler: {scheduler_status.title()}")

    def _create_backup_with_options(
        self, name, backup_type, compress, include_logs, encrypt, location
    ):
        """Create backup with specified options"""
        try:
            # Update temporary config for this backup
            temp_config = self.backup_manager.config.copy()
            temp_config["compress_backups"] = compress
            temp_config["include_logs"] = include_logs
            temp_config["encrypt_backups"] = encrypt

            if location:
                temp_config["backup_location"] = location

            # Temporarily update config
            original_config = self.backup_manager.config
            self.backup_manager.config = temp_config

            try:
                success, result = self.backup_manager.create_full_backup(
                    backup_name=name if name else None
                )

                if success:
                    st.success(f"✅ Backup created successfully!")
                    st.info(f"📁 Backup location: {result}")
                    logger.log_action_end(f"Manual backup created: {result}")
                else:
                    st.error(f"❌ Backup failed: {result}")

            finally:
                # Restore original config
                self.backup_manager.config = original_config

        except Exception as e:
            st.error(f"❌ Error creating backup: {e}")
            logger.log_error(f"Backup creation error: {e}")

    def _test_backup_configuration(self):
        """Test backup configuration without creating actual backup"""
        try:
            # Perform validation checks
            checks = [
                ("Storage location accessible", self._check_storage_access()),
                ("Permissions valid", self._check_permissions()),
                ("Required components available", self._check_components()),
                ("Configuration valid", self._check_configuration()),
            ]

            all_passed = True

            for check_name, passed in checks:
                if passed:
                    st.success(f"✅ {check_name}")
                else:
                    st.error(f"❌ {check_name}")
                    all_passed = False

            if all_passed:
                st.success("🎉 All backup configuration tests passed!")
            else:
                st.warning("⚠️ Some configuration issues found. Please review settings.")

        except Exception as e:
            st.error(f"❌ Configuration test failed: {e}")

    def _restore_backup(self, backup_info):
        """Restore a specific backup"""
        if st.session_state.get(f'confirm_restore_{backup_info["name"]}'):
            with st.spinner(f"Restoring backup: {backup_info['name']}..."):
                success, message = self.backup_manager.restore_backup(
                    backup_info["path"]
                )

                if success:
                    st.success(f"✅ {message}")
                    logger.log_action_end(f"Backup restored: {backup_info['name']}")
                else:
                    st.error(f"❌ {message}")

            # Reset confirmation
            del st.session_state[f'confirm_restore_{backup_info["name"]}']
            st.rerun()
        else:
            st.session_state[f'confirm_restore_{backup_info["name"]}'] = True
            st.warning(
                f"⚠️ Click restore again to confirm restoring: {backup_info['name']}"
            )

    def _delete_backup(self, backup_info):
        """Delete a specific backup"""
        if st.session_state.get(f'confirm_delete_{backup_info["name"]}'):
            success, message = self.backup_manager.delete_backup(backup_info["path"])

            if success:
                st.success(f"✅ {message}")
                logger.log_action_end(f"Backup deleted: {backup_info['name']}")
            else:
                st.error(f"❌ {message}")

            # Reset confirmation
            del st.session_state[f'confirm_delete_{backup_info["name"]}']
            st.rerun()
        else:
            st.session_state[f'confirm_delete_{backup_info["name"]}'] = True
            st.warning(
                f"⚠️ Click delete again to confirm deletion of: {backup_info['name']}"
            )

    def _bulk_delete_backups(self, selected_backups):
        """Delete multiple backups"""
        if st.session_state.get("confirm_bulk_delete"):
            deleted_count = 0

            for backup in selected_backups:
                success, _ = self.backup_manager.delete_backup(backup["path"])
                if success:
                    deleted_count += 1

            st.success(f"✅ Deleted {deleted_count}/{len(selected_backups)} backups")
            logger.log_action_end(f"Bulk delete: {deleted_count} backups")

            del st.session_state["confirm_bulk_delete"]
            st.rerun()
        else:
            st.session_state["confirm_bulk_delete"] = True
            st.warning(
                f"⚠️ Click again to confirm deletion of {len(selected_backups)} backups"
            )

    def _export_selected_backups(self, selected_backups):
        """Export selected backups information"""
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "backups": selected_backups,
        }

        st.download_button(
            "💾 Download Backup List",
            data=json.dumps(export_data, indent=2),
            file_name=f"backup_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

    def _compare_backups(self, backups):
        """Compare two backups"""
        if len(backups) != 2:
            return

        st.markdown("##### 📊 Backup Comparison")

        backup1, backup2 = backups

        comparison_data = {
            "Attribute": ["Name", "Type", "Size", "Created", "Compressed"],
            "Backup 1": [
                backup1["name"],
                backup1["type"].title(),
                self._format_size(backup1["size"]),
                datetime.fromisoformat(backup1["created_at"]).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "Yes" if backup1.get("compressed", False) else "No",
            ],
            "Backup 2": [
                backup2["name"],
                backup2["type"].title(),
                self._format_size(backup2["size"]),
                datetime.fromisoformat(backup2["created_at"]).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "Yes" if backup2.get("compressed", False) else "No",
            ],
        }

        st.dataframe(comparison_data, use_container_width=True)

    def _save_backup_settings(self, new_config):
        """Save backup settings"""
        try:
            config_path = (
                project_root / "data" / "module_configs" / "backup_module.json"
            )

            if config_path.exists():
                with open(config_path, "r") as f:
                    full_config = json.load(f)
            else:
                full_config = {"enabled": True, "auto_start": True, "priority": 3}

            full_config["custom"] = new_config
            full_config["last_modified"] = datetime.now().isoformat()

            with open(config_path, "w") as f:
                json.dump(full_config, f, indent=2)

            # Update backup manager config
            self.backup_manager.config = new_config

            logger.log_action_end("Backup settings updated")
            return True

        except Exception as e:
            logger.log_error(f"Error saving backup settings: {e}")
            return False

    def _reset_backup_settings(self):
        """Reset backup settings to defaults"""
        default_config = {
            "backup_frequency": "daily",
            "backup_location": "./backup",
            "compress_backups": True,
            "retention_days": 30,
            "include_user_data": True,
            "include_logs": False,
            "encrypt_backups": False,
        }

        return self._save_backup_settings(default_config)

    def _import_backup_settings(self, config_data):
        """Import backup settings from uploaded file"""
        try:
            if "config" in config_data:
                return self._save_backup_settings(config_data["config"])
            else:
                return False
        except Exception as e:
            logger.log_error(f"Error importing backup settings: {e}")
            return False

    def _get_system_health(self):
        """Get system health information"""
        return {
            "storage_status": "healthy" if self._check_storage_access() else "warning",
            "permissions_status": "healthy" if self._check_permissions() else "error",
            "scheduler_status": (
                "running" if self.backup_manager._scheduler_running else "stopped"
            ),
        }

    def _check_storage_access(self):
        """Check if backup storage location is accessible"""
        try:
            backup_dir = Path(
                self.backup_manager.config.get("backup_location", "./backup")
            )
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Try to create a test file
            test_file = backup_dir / ".test_access"
            test_file.write_text("test")
            test_file.unlink()

            return True
        except Exception:
            return False

    def _check_permissions(self):
        """Check if we have required permissions"""
        try:
            # Check read/write permissions on key directories
            test_dirs = [
                project_root / "data",
                project_root / "config",
                project_root / "logs",
            ]

            for test_dir in test_dirs:
                if test_dir.exists():
                    # Try to create a test file
                    test_file = test_dir / ".permission_test"
                    test_file.write_text("test")
                    test_file.unlink()

            return True
        except Exception:
            return False

    def _check_components(self):
        """Check if required components are available"""
        try:
            # Check if key directories exist
            required_dirs = [
                project_root / "data",
                project_root / "config",
                project_root / "utils",
            ]

            return all(dir_path.exists() for dir_path in required_dirs)
        except Exception:
            return False

    def _check_configuration(self):
        """Check if configuration is valid"""
        try:
            config = self.backup_manager.config

            # Basic validation
            if not isinstance(config.get("retention_days"), int):
                return False

            if config.get("backup_frequency") not in [
                "manual",
                "hourly",
                "daily",
                "weekly",
            ]:
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def _format_size(size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math

        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"


class BackupSettings:
    """Backup settings configuration panel"""

    def __init__(self):
        self.backup_manager = BackupManager()

    def render(self):
        """Render backup settings panel"""
        st.markdown("### ⚙️ Backup Module Settings")

        # This would be used in the module manager
        # Currently integrated into the main BackupPanel
        panel = BackupPanel()
        panel._render_settings()
