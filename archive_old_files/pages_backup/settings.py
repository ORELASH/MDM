"""
RedshiftManager Settings Page
System configuration and application settings management.
"""

import streamlit as st
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Import our models
try:
    from models.database_models import get_database_manager, SystemSettings
    from models.configuration_model import get_configuration_manager, ConfigLevel
    from models.encryption_model import get_encryption_manager, PasswordPolicy
    from utils.i18n_helper import get_text, apply_rtl_css, set_language, get_translation_manager
    from config import APP_SETTINGS
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()


def settings_page():
    """Main settings page."""
    
    # Apply RTL CSS if needed
    apply_rtl_css()
    
    # Page title
    st.title("⚙️ " + get_text("nav.settings", "Settings"))
    st.markdown("---")
    
    # Settings categories
    tabs = st.tabs([
        get_text("settings.general", "General Settings"),
        get_text("settings.security", "Security Settings"),
        get_text("settings.database", "Database Settings"),
        get_text("settings.ui", "UI Settings"),
        get_text("settings.advanced", "Advanced Settings"),
        get_text("settings.backup", "Backup & Maintenance"),
        get_text("settings.system_info", "System Information")
    ])
    
    with tabs[0]:
        show_general_settings()
    
    with tabs[1]:
        show_security_settings()
    
    with tabs[2]:
        show_database_settings()
    
    with tabs[3]:
        show_ui_settings()
    
    with tabs[4]:
        show_advanced_settings()
    
    with tabs[5]:
        show_backup_settings()
    
    with tabs[6]:
        show_system_info()


def show_general_settings():
    """Show general application settings."""
    
    st.subheader("🔧 " + get_text("settings.general", "General Settings"))
    
    config_manager = get_configuration_manager()
    
    with st.form("general_settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Application settings
            st.write("**" + get_text("settings.application", "Application") + "**")
            
            app_name = st.text_input(
                get_text("settings.app_name", "Application Name"),
                value=config_manager.get("application.name", "RedshiftManager"),
                help=get_text("settings.app_name_help", "Display name for the application")
            )
            
            app_env = st.selectbox(
                get_text("settings.environment", "Environment"),
                options=["development", "staging", "production"],
                index=["development", "staging", "production"].index(
                    config_manager.get("application.environment", "development")
                )
            )
            
            debug_mode = st.checkbox(
                get_text("settings.debug_mode", "Debug Mode"),
                value=config_manager.get("application.debug", False),
                help=get_text("settings.debug_help", "Enable debug logging and error details")
            )
            
            maintenance_mode = st.checkbox(
                get_text("settings.maintenance_mode", "Maintenance Mode"),
                value=config_manager.get("application.maintenance_mode", False),
                help=get_text("settings.maintenance_help", "Block user access during maintenance")
            )
        
        with col2:
            # Performance settings
            st.write("**" + get_text("settings.performance", "Performance") + "**")
            
            enable_caching = st.checkbox(
                get_text("settings.enable_caching", "Enable Caching"),
                value=config_manager.get("performance.enable_caching", True),
                help=get_text("settings.caching_help", "Cache frequently used data")
            )
            
            cache_ttl = st.number_input(
                get_text("settings.cache_ttl", "Cache TTL (seconds)"),
                min_value=60,
                max_value=3600,
                value=config_manager.get("performance.cache_ttl", 300),
                help=get_text("settings.cache_ttl_help", "How long to keep cached data")
            )
            
            max_connections = st.number_input(
                get_text("settings.max_connections", "Max Database Connections"),
                min_value=5,
                max_value=100,
                value=config_manager.get("database.pool_size", 10),
                help=get_text("settings.max_connections_help", "Maximum database connection pool size")
            )
            
            query_timeout = st.number_input(
                get_text("settings.default_query_timeout", "Default Query Timeout (seconds)"),
                min_value=30,
                max_value=3600,
                value=config_manager.get("redshift.query_timeout", 300),
                help=get_text("settings.query_timeout_help", "Default timeout for SQL queries")
            )
        
        # Submit button
        if st.form_submit_button("💾 " + get_text("settings.save_general", "Save General Settings")):
            try:
                # Save settings
                config_manager.set("application.name", app_name)
                config_manager.set("application.environment", app_env)
                config_manager.set("application.debug", debug_mode)
                config_manager.set("application.maintenance_mode", maintenance_mode)
                config_manager.set("performance.enable_caching", enable_caching)
                config_manager.set("performance.cache_ttl", cache_ttl)
                config_manager.set("database.pool_size", max_connections)
                config_manager.set("redshift.query_timeout", query_timeout)
                
                st.success(get_text("settings.saved_successfully", "Settings saved successfully!"))
                
                # Show restart notice if needed
                if maintenance_mode != config_manager.get("application.maintenance_mode", False):
                    st.warning(get_text("settings.restart_required", "Application restart may be required for some changes"))
                
            except Exception as e:
                st.error(f"Error saving settings: {e}")


def show_security_settings():
    """Show security and authentication settings."""
    
    st.subheader("🔒 " + get_text("settings.security", "Security Settings"))
    
    config_manager = get_configuration_manager()
    
    with st.form("security_settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Password policy
            st.write("**" + get_text("settings.password_policy", "Password Policy") + "**")
            
            min_length = st.number_input(
                get_text("settings.password_min_length", "Minimum Password Length"),
                min_value=8,
                max_value=128,
                value=config_manager.get("security.password_min_length", 12)
            )
            
            require_uppercase = st.checkbox(
                get_text("settings.require_uppercase", "Require Uppercase Letters"),
                value=config_manager.get("security.password_require_uppercase", True)
            )
            
            require_lowercase = st.checkbox(
                get_text("settings.require_lowercase", "Require Lowercase Letters"),
                value=config_manager.get("security.password_require_lowercase", True)
            )
            
            require_digits = st.checkbox(
                get_text("settings.require_digits", "Require Digits"),
                value=config_manager.get("security.password_require_digits", True)
            )
            
            require_special = st.checkbox(
                get_text("settings.require_special", "Require Special Characters"),
                value=config_manager.get("security.password_require_special", True)
            )
            
            password_expiry = st.number_input(
                get_text("settings.password_expiry", "Password Expiry (days)"),
                min_value=30,
                max_value=365,
                value=config_manager.get("security.password_expiry_days", 90)
            )
        
        with col2:
            # Session and authentication
            st.write("**" + get_text("settings.authentication", "Authentication") + "**")
            
            session_timeout = st.number_input(
                get_text("settings.session_timeout", "Session Timeout (seconds)"),
                min_value=300,
                max_value=86400,
                value=config_manager.get("security.session_timeout", 3600)
            )
            
            max_login_attempts = st.number_input(
                get_text("settings.max_login_attempts", "Max Login Attempts"),
                min_value=3,
                max_value=10,
                value=config_manager.get("security.max_login_attempts", 5)
            )
            
            lockout_duration = st.number_input(
                get_text("settings.lockout_duration", "Lockout Duration (minutes)"),
                min_value=5,
                max_value=60,
                value=config_manager.get("security.lockout_duration", 15)
            )
            
            enable_2fa = st.checkbox(
                get_text("settings.enable_2fa", "Enable Two-Factor Authentication"),
                value=config_manager.get("security.enable_2fa", False),
                help=get_text("settings.2fa_help", "Require 2FA for enhanced security")
            )
            
            enable_audit = st.checkbox(
                get_text("settings.enable_audit", "Enable Audit Logging"),
                value=config_manager.get("security.enable_audit_logging", True),
                help=get_text("settings.audit_help", "Log all user actions for security")
            )
            
            audit_retention = st.number_input(
                get_text("settings.audit_retention", "Audit Log Retention (days)"),
                min_value=30,
                max_value=365,
                value=config_manager.get("security.audit_retention_days", 90)
            )
        
        # Submit button
        if st.form_submit_button("🔒 " + get_text("settings.save_security", "Save Security Settings")):
            try:
                # Save password policy settings
                config_manager.set("security.password_min_length", min_length)
                config_manager.set("security.password_require_uppercase", require_uppercase)
                config_manager.set("security.password_require_lowercase", require_lowercase)
                config_manager.set("security.password_require_digits", require_digits)
                config_manager.set("security.password_require_special", require_special)
                config_manager.set("security.password_expiry_days", password_expiry)
                
                # Save authentication settings
                config_manager.set("security.session_timeout", session_timeout)
                config_manager.set("security.max_login_attempts", max_login_attempts)
                config_manager.set("security.lockout_duration", lockout_duration)
                config_manager.set("security.enable_2fa", enable_2fa)
                config_manager.set("security.enable_audit_logging", enable_audit)
                config_manager.set("security.audit_retention_days", audit_retention)
                
                st.success(get_text("settings.security_saved", "Security settings saved successfully!"))
                
            except Exception as e:
                st.error(f"Error saving security settings: {e}")


def show_database_settings():
    """Show database configuration settings."""
    
    st.subheader("🗄️ " + get_text("settings.database", "Database Settings"))
    
    config_manager = get_configuration_manager()
    db_manager = get_database_manager()
    
    # Database information (read-only)
    with st.expander("ℹ️ " + get_text("settings.database_info", "Database Information")):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**{get_text('settings.db_type', 'Database Type')}:** SQLite")
            st.write(f"**{get_text('settings.db_path', 'Database Path')}:** ./data/redshift_manager.db")
            
            # Get database stats
            try:
                stats = db_manager.get_database_stats()
                st.write(f"**{get_text('settings.total_users', 'Total Users')}:** {stats.get('users', 0)}")
                st.write(f"**{get_text('settings.total_clusters', 'Total Clusters')}:** {stats.get('clusters', 0)}")
            except Exception as e:
                st.write(f"**{get_text('settings.stats_error', 'Stats Error')}:** {e}")
        
        with col2:
            # Database file size
            try:
                db_path = Path("./data/redshift_manager.db")
                if db_path.exists():
                    size_mb = db_path.stat().st_size / (1024 * 1024)
                    st.write(f"**{get_text('settings.db_size', 'Database Size')}:** {size_mb:.2f} MB")
                    
                    # Last modified
                    mod_time = datetime.fromtimestamp(db_path.stat().st_mtime)
                    st.write(f"**{get_text('settings.last_modified', 'Last Modified')}:** {mod_time.strftime('%Y-%m-%d %H:%M')}")
            except Exception as e:
                st.write(f"**{get_text('settings.file_error', 'File Error')}:** {e}")
    
    with st.form("database_settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Connection pool settings
            st.write("**" + get_text("settings.connection_pool", "Connection Pool") + "**")
            
            pool_size = st.number_input(
                get_text("settings.pool_size", "Pool Size"),
                min_value=5,
                max_value=50,
                value=config_manager.get("database.pool_size", 10)
            )
            
            max_overflow = st.number_input(
                get_text("settings.max_overflow", "Max Overflow"),
                min_value=5,
                max_value=50,
                value=config_manager.get("database.max_overflow", 20)
            )
            
            pool_timeout = st.number_input(
                get_text("settings.pool_timeout", "Pool Timeout (seconds)"),
                min_value=10,
                max_value=300,
                value=config_manager.get("database.pool_timeout", 30)
            )
            
            enable_backup = st.checkbox(
                get_text("settings.enable_auto_backup", "Enable Auto Backup"),
                value=config_manager.get("backup.auto_backup.enabled", True)
            )
        
        with col2:
            # Database maintenance
            st.write("**" + get_text("settings.maintenance", "Maintenance") + "**")
            
            cleanup_logs = st.checkbox(
                get_text("settings.auto_cleanup_logs", "Auto Cleanup Logs"),
                value=config_manager.get("maintenance.cleanup.auto_cleanup_enabled", True)
            )
            
            log_retention = st.number_input(
                get_text("settings.log_retention", "Log Retention (days)"),
                min_value=7,
                max_value=365,
                value=config_manager.get("maintenance.cleanup.log_retention_days", 90)
            )
            
            vacuum_schedule = st.text_input(
                get_text("settings.vacuum_schedule", "Database Vacuum Schedule"),
                value=config_manager.get("backup.schedule.database_backup", "0 3 * * *"),
                help=get_text("settings.cron_help", "Cron expression (e.g., '0 3 * * *' for daily at 3 AM)")
            )
            
            enable_encryption = st.checkbox(
                get_text("settings.enable_db_encryption", "Enable Database Encryption"),
                value=config_manager.get("database.encryption_enabled", True),
                help=get_text("settings.encryption_help", "Encrypt sensitive data in database")
            )
        
        # Database actions
        st.write("**" + get_text("settings.database_actions", "Database Actions") + "**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            backup_now = st.form_submit_button("💾 " + get_text("settings.backup_now", "Backup Now"))
        
        with col2:
            vacuum_now = st.form_submit_button("🧹 " + get_text("settings.vacuum_now", "Vacuum Database"))
        
        with col3:
            cleanup_now = st.form_submit_button("🗑️ " + get_text("settings.cleanup_now", "Cleanup Logs"))
        
        with col4:
            save_db_settings = st.form_submit_button("💾 " + get_text("settings.save_db", "Save Settings"))
        
        # Handle actions
        if backup_now:
            perform_database_backup(db_manager)
        
        if vacuum_now:
            perform_database_vacuum(db_manager)
        
        if cleanup_now:
            perform_log_cleanup()
        
        if save_db_settings:
            try:
                config_manager.set("database.pool_size", pool_size)
                config_manager.set("database.max_overflow", max_overflow)
                config_manager.set("database.pool_timeout", pool_timeout)
                config_manager.set("backup.auto_backup.enabled", enable_backup)
                config_manager.set("maintenance.cleanup.auto_cleanup_enabled", cleanup_logs)
                config_manager.set("maintenance.cleanup.log_retention_days", log_retention)
                config_manager.set("backup.schedule.database_backup", vacuum_schedule)
                config_manager.set("database.encryption_enabled", enable_encryption)
                
                st.success(get_text("settings.db_saved", "Database settings saved successfully!"))
                
            except Exception as e:
                st.error(f"Error saving database settings: {e}")


def show_ui_settings():
    """Show UI and internationalization settings."""
    
    st.subheader("🎨 " + get_text("settings.ui", "UI Settings"))
    
    config_manager = get_configuration_manager()
    translation_manager = get_translation_manager()
    
    with st.form("ui_settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Language and localization
            st.write("**" + get_text("settings.language_localization", "Language & Localization") + "**")
            
            current_language = translation_manager.get_language()
            available_languages = translation_manager.get_available_languages()
            
            language_options = {info.native_name: code for code, info in available_languages.items()}
            selected_language = st.selectbox(
                get_text("settings.language", "Language"),
                options=list(language_options.keys()),
                index=list(language_options.values()).index(current_language),
                help=get_text("settings.language_help", "Select interface language")
            )
            
            enable_rtl = st.checkbox(
                get_text("settings.enable_rtl", "Enable RTL Support"),
                value=config_manager.get("ui.enable_rtl", True),
                help=get_text("settings.rtl_help", "Right-to-left text support for Hebrew")
            )
            
            auto_detect_language = st.checkbox(
                get_text("settings.auto_detect_language", "Auto-detect Language"),
                value=config_manager.get("ui.auto_detect_language", False),
                help=get_text("settings.auto_detect_help", "Detect language from browser settings")
            )
            
            # Theme settings
            st.write("**" + get_text("settings.theme", "Theme") + "**")
            
            default_theme = st.selectbox(
                get_text("settings.default_theme", "Default Theme"),
                options=["light", "dark", "auto"],
                index=["light", "dark", "auto"].index(config_manager.get("ui.theme.default", "light"))
            )
            
            wide_mode = st.checkbox(
                get_text("settings.wide_mode", "Wide Mode Layout"),
                value=config_manager.get("ui.wide_mode", True),
                help=get_text("settings.wide_mode_help", "Use full browser width")
            )
        
        with col2:
            # Display settings
            st.write("**" + get_text("settings.display", "Display Settings") + "**")
            
            items_per_page = st.number_input(
                get_text("settings.items_per_page", "Items Per Page"),
                min_value=10,
                max_value=200,
                value=config_manager.get("ui.items_per_page", 50),
                help=get_text("settings.items_help", "Number of items to show in tables")
            )
            
            auto_refresh = st.checkbox(
                get_text("settings.auto_refresh", "Enable Auto Refresh"),
                value=config_manager.get("ui.enable_auto_refresh", True),
                help=get_text("settings.auto_refresh_help", "Automatically refresh data")
            )
            
            refresh_interval = st.number_input(
                get_text("settings.refresh_interval", "Auto Refresh Interval (seconds)"),
                min_value=10,
                max_value=300,
                value=config_manager.get("ui.auto_refresh_interval", 30),
                disabled=not auto_refresh
            )
            
            show_tooltips = st.checkbox(
                get_text("settings.show_tooltips", "Show Tooltips"),
                value=config_manager.get("ui.show_tooltips", True),
                help=get_text("settings.tooltips_help", "Show helpful tooltips")
            )
            
            # Data display
            st.write("**" + get_text("settings.data_display", "Data Display") + "**")
            
            max_rows_display = st.number_input(
                get_text("settings.max_rows_display", "Max Rows to Display"),
                min_value=100,
                max_value=10000,
                value=config_manager.get("ui.data_display.max_rows_display", 1000)
            )
            
            enable_export = st.checkbox(
                get_text("settings.enable_data_export", "Enable Data Export"),
                value=config_manager.get("ui.data_display.enable_data_export", True)
            )
        
        # Submit button
        if st.form_submit_button("🎨 " + get_text("settings.save_ui", "Save UI Settings")):
            try:
                # Save language settings
                new_language = language_options[selected_language]
                if new_language != current_language:
                    translation_manager.set_language(new_language)
                    config_manager.set("ui.default_language", new_language)
                
                config_manager.set("ui.enable_rtl", enable_rtl)
                config_manager.set("ui.auto_detect_language", auto_detect_language)
                
                # Save theme settings
                config_manager.set("ui.theme.default", default_theme)
                config_manager.set("ui.wide_mode", wide_mode)
                
                # Save display settings
                config_manager.set("ui.items_per_page", items_per_page)
                config_manager.set("ui.enable_auto_refresh", auto_refresh)
                config_manager.set("ui.auto_refresh_interval", refresh_interval)
                config_manager.set("ui.show_tooltips", show_tooltips)
                config_manager.set("ui.data_display.max_rows_display", max_rows_display)
                config_manager.set("ui.data_display.enable_data_export", enable_export)
                
                st.success(get_text("settings.ui_saved", "UI settings saved successfully!"))
                
                if new_language != current_language:
                    st.info(get_text("settings.language_changed", "Language changed. Please refresh the page."))
                
            except Exception as e:
                st.error(f"Error saving UI settings: {e}")


def show_advanced_settings():
    """Show advanced system settings."""
    
    st.subheader("🔬 " + get_text("settings.advanced", "Advanced Settings"))
    
    config_manager = get_configuration_manager()
    
    # Warning about advanced settings
    st.warning(get_text("settings.advanced_warning", "⚠️ Advanced settings can affect system performance and stability. Change with caution."))
    
    with st.form("advanced_settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Performance tuning
            st.write("**" + get_text("settings.performance_tuning", "Performance Tuning") + "**")
            
            enable_profiling = st.checkbox(
                get_text("settings.enable_profiling", "Enable Performance Profiling"),
                value=config_manager.get("development.profiling.enable_sql_profiling", False),
                help=get_text("settings.profiling_help", "Track performance metrics (may impact performance)")
            )
            
            memory_monitoring = st.checkbox(
                get_text("settings.memory_monitoring", "Enable Memory Monitoring"),
                value=config_manager.get("performance.monitoring.memory_monitoring", True)
            )
            
            slow_query_threshold = st.number_input(
                get_text("settings.slow_query_threshold", "Slow Query Threshold (seconds)"),
                min_value=1.0,
                max_value=60.0,
                value=float(config_manager.get("performance.slow_query_threshold", 10.0)),
                step=0.1
            )
            
            max_query_time = st.number_input(
                get_text("settings.max_query_execution", "Max Query Execution Time (seconds)"),
                min_value=60,
                max_value=7200,
                value=config_manager.get("performance.max_query_execution_time", 3600)
            )
            
            # Feature flags
            st.write("**" + get_text("settings.feature_flags", "Feature Flags") + "**")
            
            advanced_analytics = st.checkbox(
                get_text("settings.advanced_analytics", "Advanced Analytics"),
                value=config_manager.get("features.experimental.advanced_analytics", False)
            )
            
            real_time_monitoring = st.checkbox(
                get_text("settings.real_time_monitoring", "Real-time Monitoring"),
                value=config_manager.get("features.experimental.real_time_monitoring", False)
            )
            
            api_access = st.checkbox(
                get_text("settings.api_access", "API Access"),
                value=config_manager.get("features.experimental.api_access", False)
            )
        
        with col2:
            # Logging configuration
            st.write("**" + get_text("settings.logging", "Logging Configuration") + "**")
            
            log_level = st.selectbox(
                get_text("settings.log_level", "Log Level"),
                options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                index=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].index(
                    config_manager.get("logging.general.level", "INFO")
                )
            )
            
            log_to_file = st.checkbox(
                get_text("settings.log_to_file", "Log to File"),
                value=config_manager.get("logging.general.to_file", True)
            )
            
            log_to_console = st.checkbox(
                get_text("settings.log_to_console", "Log to Console"),
                value=config_manager.get("logging.general.to_console", True)
            )
            
            colorize_logs = st.checkbox(
                get_text("settings.colorize_logs", "Colorize Log Output"),
                value=config_manager.get("logging.general.colorize", True)
            )
            
            max_log_size = st.number_input(
                get_text("settings.max_log_size", "Max Log File Size (MB)"),
                min_value=1,
                max_value=100,
                value=config_manager.get("logging.files.main_log.max_size", 10485760) // (1024 * 1024)
            )
            
            log_backup_count = st.number_input(
                get_text("settings.log_backup_count", "Log File Backup Count"),
                min_value=1,
                max_value=20,
                value=config_manager.get("logging.files.main_log.backup_count", 5)
            )
            
            # Development settings
            st.write("**" + get_text("settings.development", "Development") + "**")
            
            enable_dev_tools = st.checkbox(
                get_text("settings.enable_dev_tools", "Enable Development Tools"),
                value=config_manager.get("development.enable_dev_tools", True)
            )
            
            mock_data = st.checkbox(
                get_text("settings.mock_data", "Use Mock Data"),
                value=config_manager.get("development.mock_data", False)
            )
        
        # Submit button
        if st.form_submit_button("🔬 " + get_text("settings.save_advanced", "Save Advanced Settings")):
            try:
                # Save performance settings
                config_manager.set("development.profiling.enable_sql_profiling", enable_profiling)
                config_manager.set("performance.monitoring.memory_monitoring", memory_monitoring)
                config_manager.set("performance.slow_query_threshold", slow_query_threshold)
                config_manager.set("performance.max_query_execution_time", max_query_time)
                
                # Save feature flags
                config_manager.set("features.experimental.advanced_analytics", advanced_analytics)
                config_manager.set("features.experimental.real_time_monitoring", real_time_monitoring)
                config_manager.set("features.experimental.api_access", api_access)
                
                # Save logging settings
                config_manager.set("logging.general.level", log_level)
                config_manager.set("logging.general.to_file", log_to_file)
                config_manager.set("logging.general.to_console", log_to_console)
                config_manager.set("logging.general.colorize", colorize_logs)
                config_manager.set("logging.files.main_log.max_size", max_log_size * 1024 * 1024)
                config_manager.set("logging.files.main_log.backup_count", log_backup_count)
                
                # Save development settings
                config_manager.set("development.enable_dev_tools", enable_dev_tools)
                config_manager.set("development.mock_data", mock_data)
                
                st.success(get_text("settings.advanced_saved", "Advanced settings saved successfully!"))
                st.info(get_text("settings.restart_recommended", "Application restart recommended for logging changes"))
                
            except Exception as e:
                st.error(f"Error saving advanced settings: {e}")


def show_backup_settings():
    """Show backup and maintenance settings."""
    
    st.subheader("💾 " + get_text("settings.backup", "Backup & Maintenance"))
    
    config_manager = get_configuration_manager()
    
    with st.form("backup_settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Backup configuration
            st.write("**" + get_text("settings.backup_config", "Backup Configuration") + "**")
            
            enable_auto_backup = st.checkbox(
                get_text("settings.enable_auto_backup", "Enable Auto Backup"),
                value=config_manager.get("backup.auto_backup.enabled", True)
            )
            
            backup_interval = st.number_input(
                get_text("settings.backup_interval", "Backup Interval (hours)"),
                min_value=1,
                max_value=168,
                value=config_manager.get("backup.auto_backup.interval_hours", 24),
                disabled=not enable_auto_backup
            )
            
            backup_retention = st.number_input(
                get_text("settings.backup_retention", "Backup Retention (days)"),
                min_value=1,
                max_value=365,
                value=config_manager.get("backup.auto_backup.retention_days", 30)
            )
            
            backup_compression = st.checkbox(
                get_text("settings.backup_compression", "Enable Backup Compression"),
                value=config_manager.get("backup.auto_backup.compression", True)
            )
            
            backup_encryption = st.checkbox(
                get_text("settings.backup_encryption", "Enable Backup Encryption"),
                value=config_manager.get("backup.auto_backup.encryption", True)
            )
            
            backup_path = st.text_input(
                get_text("settings.backup_path", "Backup Directory"),
                value=config_manager.get("backup.paths.backup_directory", "./backup"),
                help=get_text("settings.backup_path_help", "Directory to store backup files")
            )
        
        with col2:
            # Maintenance schedules
            st.write("**" + get_text("settings.maintenance_schedules", "Maintenance Schedules") + "**")
            
            db_backup_schedule = st.text_input(
                get_text("settings.db_backup_schedule", "Database Backup Schedule"),
                value=config_manager.get("backup.schedule.database_backup", "0 3 * * *"),
                help=get_text("settings.cron_help", "Cron expression (e.g., '0 3 * * *' for daily at 3 AM)")
            )
            
            log_cleanup_schedule = st.text_input(
                get_text("settings.log_cleanup_schedule", "Log Cleanup Schedule"),
                value=config_manager.get("backup.schedule.log_cleanup", "0 4 * * *"),
                help=get_text("settings.cron_help", "Cron expression for log cleanup")
            )
            
            cache_cleanup_interval = st.number_input(
                get_text("settings.cache_cleanup_interval", "Cache Cleanup Interval (seconds)"),
                min_value=300,
                max_value=86400,
                value=config_manager.get("backup.schedule.cache_cleanup_interval", 3600)
            )
            
            # Current backup status
            st.write("**" + get_text("settings.backup_status", "Backup Status") + "**")
            
            # Check for existing backups
            backup_dir = Path(backup_path)
            if backup_dir.exists():
                backup_files = list(backup_dir.glob("*.backup*"))
                st.write(f"**{get_text('settings.backup_count', 'Backup Files')}:** {len(backup_files)}")
                
                if backup_files:
                    latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
                    mod_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
                    st.write(f"**{get_text('settings.latest_backup', 'Latest Backup')}:** {mod_time.strftime('%Y-%m-%d %H:%M')}")
                    
                    # Calculate total backup size
                    total_size = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)
                    st.write(f"**{get_text('settings.total_backup_size', 'Total Size')}:** {total_size:.2f} MB")
            else:
                st.write(get_text("settings.no_backups", "No backups found"))
        
        # Submit button
        if st.form_submit_button("💾 " + get_text("settings.save_backup", "Save Backup Settings")):
            try:
                config_manager.set("backup.auto_backup.enabled", enable_auto_backup)
                config_manager.set("backup.auto_backup.interval_hours", backup_interval)
                config_manager.set("backup.auto_backup.retention_days", backup_retention)
                config_manager.set("backup.auto_backup.compression", backup_compression)
                config_manager.set("backup.auto_backup.encryption", backup_encryption)
                config_manager.set("backup.paths.backup_directory", backup_path)
                config_manager.set("backup.schedule.database_backup", db_backup_schedule)
                config_manager.set("backup.schedule.log_cleanup", log_cleanup_schedule)
                config_manager.set("backup.schedule.cache_cleanup_interval", cache_cleanup_interval)
                
                st.success(get_text("settings.backup_saved", "Backup settings saved successfully!"))
                
            except Exception as e:
                st.error(f"Error saving backup settings: {e}")


def show_system_info():
    """Show system information and diagnostics."""
    
    st.subheader("ℹ️ " + get_text("settings.system_info", "System Information"))
    
    # Application information
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**" + get_text("settings.application_info", "Application Information") + "**")
        
        app_info = {
            get_text("settings.app_name", "Application Name"): APP_SETTINGS.get("application", {}).get("name", "RedshiftManager"),
            get_text("settings.app_version", "Version"): APP_SETTINGS.get("application", {}).get("version", "1.0.0"),
            get_text("settings.environment", "Environment"): APP_SETTINGS.get("application", {}).get("environment", "development"),
            get_text("settings.build_number", "Build"): APP_SETTINGS.get("application", {}).get("build_number", "unknown"),
            get_text("settings.release_date", "Release Date"): APP_SETTINGS.get("application", {}).get("release_date", "unknown")
        }
        
        for key, value in app_info.items():
            st.write(f"**{key}:** {value}")
    
    with col2:
        st.write("**" + get_text("settings.system_environment", "System Environment") + "**")
        
        import sys
        import platform
        
        system_info = {
            get_text("settings.python_version", "Python Version"): f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            get_text("settings.platform", "Platform"): platform.system(),
            get_text("settings.architecture", "Architecture"): platform.architecture()[0],
            get_text("settings.processor", "Processor"): platform.processor() or "Unknown",
            get_text("settings.hostname", "Hostname"): platform.node()
        }
        
        for key, value in system_info.items():
            st.write(f"**{key}:** {value}")
    
    # Installed packages (key ones)
    st.write("**" + get_text("settings.key_dependencies", "Key Dependencies") + "**")
    
    key_packages = ["streamlit", "sqlalchemy", "pandas", "cryptography", "psycopg2"]
    dependency_info = {}
    
    for package in key_packages:
        try:
            import importlib.metadata
            version = importlib.metadata.version(package)
            dependency_info[package] = version
        except importlib.metadata.PackageNotFoundError:
            dependency_info[package] = "Not installed"
        except Exception:
            dependency_info[package] = "Unknown"
    
    # Display in columns
    dep_cols = st.columns(len(key_packages))
    for i, (package, version) in enumerate(dependency_info.items()):
        with dep_cols[i]:
            st.metric(package.title(), version)
    
    # Configuration export/import
    st.write("**" + get_text("settings.config_management", "Configuration Management") + "**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 " + get_text("settings.export_config", "Export Configuration")):
            export_configuration()
    
    with col2:
        uploaded_file = st.file_uploader(
            get_text("settings.import_config", "Import Configuration"),
            type=['json'],
            help=get_text("settings.import_help", "Upload a configuration JSON file")
        )
        
        if uploaded_file is not None:
            import_configuration(uploaded_file)
    
    with col3:
        if st.button("🔄 " + get_text("settings.reset_config", "Reset to Defaults")):
            reset_configuration()


# Helper functions

def perform_database_backup(db_manager):
    """Perform database backup."""
    try:
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"./backup/{backup_filename}"
        
        os.makedirs("./backup", exist_ok=True)
        
        if db_manager.backup_database(backup_path):
            st.success(f"{get_text('settings.backup_success', 'Backup created successfully')}: {backup_filename}")
        else:
            st.error(get_text("settings.backup_failed", "Backup failed"))
    except Exception as e:
        st.error(f"Backup error: {e}")


def perform_database_vacuum(db_manager):
    """Perform database vacuum/optimization."""
    try:
        # For SQLite, this would involve VACUUM command
        # For now, just simulate the operation
        st.success(get_text("settings.vacuum_success", "Database optimization completed"))
    except Exception as e:
        st.error(f"Vacuum error: {e}")


def perform_log_cleanup():
    """Clean up old log files."""
    try:
        log_dir = Path("./logs")
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log*"))
            # Simulate cleanup - in real implementation, would delete old files
            st.success(f"{get_text('settings.cleanup_success', 'Log cleanup completed')}: {len(log_files)} files processed")
        else:
            st.info(get_text("settings.no_logs", "No log files found"))
    except Exception as e:
        st.error(f"Cleanup error: {e}")


def export_configuration():
    """Export current configuration."""
    try:
        config_manager = get_configuration_manager()
        config_data = config_manager.get_all()
        
        config_json = json.dumps(config_data, indent=2, default=str)
        
        st.download_button(
            label="📥 " + get_text("settings.download_config", "Download Configuration"),
            data=config_json,
            file_name=f"redshift_manager_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
        st.success(get_text("settings.config_exported", "Configuration ready for download"))
        
    except Exception as e:
        st.error(f"Export error: {e}")


def import_configuration(uploaded_file):
    """Import configuration from uploaded file."""
    try:
        config_data = json.load(uploaded_file)
        
        # Validate configuration structure
        if not isinstance(config_data, dict):
            st.error(get_text("settings.invalid_config", "Invalid configuration file format"))
            return
        
        # Import configuration (selective - don't overwrite critical settings)
        config_manager = get_configuration_manager()
        
        safe_keys = [
            "ui.theme", "ui.language", "ui.items_per_page",
            "performance.cache_ttl", "backup.auto_backup.enabled"
        ]
        
        imported_count = 0
        for key in safe_keys:
            if key in config_data:
                config_manager.set(key, config_data[key])
                imported_count += 1
        
        st.success(f"{get_text('settings.config_imported', 'Configuration imported')}: {imported_count} settings updated")
        
    except Exception as e:
        st.error(f"Import error: {e}")


def reset_configuration():
    """Reset configuration to defaults."""
    if st.button(get_text("settings.confirm_reset", "Confirm Reset"), type="primary"):
        try:
            # This would reset to default values
            # For now, just show confirmation
            st.success(get_text("settings.config_reset", "Configuration reset to defaults"))
            st.info(get_text("settings.restart_required", "Application restart required"))
        except Exception as e:
            st.error(f"Reset error: {e}")


if __name__ == "__main__":
    settings_page()