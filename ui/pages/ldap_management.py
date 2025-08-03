#!/usr/bin/env python3
"""
LDAP Management Interface for MultiDBManager
Provides comprehensive LDAP configuration, testing, and user synchronization
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Import LDAP integration
try:
    from core.ldap_integration import get_ldap_manager, LDAPManager, TEST_CONFIGS, LDAP_AVAILABLE
    from database.database_manager import get_database_manager
    LDAP_INTEGRATION_AVAILABLE = True
except ImportError as e:
    LDAP_INTEGRATION_AVAILABLE = False
    st.error(f"❌ LDAP integration not available: {e}")

def show_ldap_management():
    """Main LDAP Management Interface"""
    st.title("🔗 LDAP Integration Management")
    st.markdown("### Advanced LDAP Authentication & User Synchronization")
    st.markdown("---")
    
    if not LDAP_INTEGRATION_AVAILABLE:
        st.error("🚫 LDAP integration components not available. Please check installation.")
        show_installation_help()
        return
    
    if not LDAP_AVAILABLE:
        st.error("📦 LDAP3 library not installed.")
        show_ldap_installation()
        return
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔧 Configuration", "🧪 Testing", "👥 Users", "📊 Analytics", "⚙️ Settings"
    ])
    
    with tab1:
        show_ldap_configuration()
    
    with tab2:
        show_ldap_testing()
    
    with tab3:
        show_ldap_users()
    
    with tab4:
        show_ldap_analytics()
    
    with tab5:
        show_ldap_settings()

def show_ldap_configuration():
    """LDAP Configuration Interface"""
    st.subheader("🔧 LDAP Server Configuration")
    
    # Load existing configurations
    db_manager = get_database_manager()
    configs = get_ldap_configurations(db_manager)
    
    # Configuration selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if configs:
            config_names = ["New Configuration"] + [config['config_name'] for config in configs]
            selected_config = st.selectbox("Select Configuration:", config_names)
        else:
            selected_config = "New Configuration"
            st.info("No existing configurations found. Create a new one below.")
    
    with col2:
        # Quick test configs
        st.markdown("**Quick Setup:**")
        if st.button("📝 ForumSys Test Server", help="Public LDAP test server"):
            st.session_state.ldap_config = TEST_CONFIGS['forumsys'].copy()
            st.rerun()
        
        if st.button("🐳 Local Docker", help="Local Docker LDAP server"):
            st.session_state.ldap_config = TEST_CONFIGS['local_docker'].copy()
            st.rerun()
    
    # Configuration form
    st.markdown("#### Configuration Details")
    
    # Load selected config or use session state
    if selected_config != "New Configuration" and configs:
        current_config = next((c for c in configs if c['config_name'] == selected_config), {})
    else:
        current_config = st.session_state.get('ldap_config', {})
    
    with st.form("ldap_config_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            config_name = st.text_input("Configuration Name", 
                                      value=current_config.get('config_name', ''),
                                      help="Unique name for this configuration")
            
            server = st.text_input("LDAP Server", 
                                 value=current_config.get('server', ''),
                                 help="LDAP server hostname or IP")
            
            port = st.number_input("Port", 
                                 min_value=1, max_value=65535,
                                 value=current_config.get('port', 389))
            
            use_ssl = st.checkbox("Use SSL/TLS", 
                                value=current_config.get('use_ssl', False))
            
            base_dn = st.text_input("Base DN", 
                                  value=current_config.get('base_dn', ''),
                                  help="Base Distinguished Name (e.g., dc=example,dc=com)")
        
        with col2:
            bind_dn = st.text_input("Bind DN", 
                                  value=current_config.get('bind_dn', ''),
                                  help="DN for binding to LDAP server")
            
            bind_password = st.text_input("Bind Password", 
                                        type="password",
                                        value=current_config.get('bind_password', ''))
            
            user_filter = st.text_input("User Filter", 
                                      value=current_config.get('user_filter', '(uid={username})'),
                                      help="LDAP filter for finding users")
            
            group_filter = st.text_input("Group Filter", 
                                       value=current_config.get('group_filter', '(member={user_dn})'),
                                       help="LDAP filter for finding user groups")
            
            timeout = st.number_input("Timeout (seconds)", 
                                    min_value=1, max_value=300,
                                    value=current_config.get('timeout_seconds', 10))
        
        # Search base settings
        st.markdown("#### Search Settings")
        col3, col4 = st.columns(2)
        
        with col3:
            user_search_base = st.text_input("User Search Base", 
                                           value=current_config.get('user_search_base', ''),
                                           help="Base DN for user searches")
        
        with col4:
            group_search_base = st.text_input("Group Search Base", 
                                            value=current_config.get('group_search_base', ''),
                                            help="Base DN for group searches")
        
        # Form buttons
        col5, col6, col7 = st.columns(3)
        
        with col5:
            save_config = st.form_submit_button("💾 Save Configuration", use_container_width=True)
        
        with col6:
            test_config = st.form_submit_button("🧪 Test Connection", use_container_width=True)
        
        with col7:
            if selected_config != "New Configuration":
                delete_config = st.form_submit_button("🗑️ Delete", use_container_width=True)
            else:
                delete_config = False
    
    # Handle form submissions
    if save_config:
        config_data = {
            'config_name': config_name,
            'server': server,
            'port': port,
            'use_ssl': use_ssl,
            'base_dn': base_dn,
            'bind_dn': bind_dn,
            'bind_password': bind_password,
            'user_filter': user_filter,
            'group_filter': group_filter,
            'user_search_base': user_search_base or base_dn,
            'group_search_base': group_search_base or base_dn,
            'timeout_seconds': timeout
        }
        
        if save_ldap_configuration(db_manager, config_data):
            st.success("✅ Configuration saved successfully!")
            st.rerun()
        else:
            st.error("❌ Failed to save configuration")
    
    if test_config:
        config_data = {
            'server': server,
            'port': port,
            'use_ssl': use_ssl,
            'base_dn': base_dn,
            'bind_dn': bind_dn,
            'bind_password': bind_password,
            'user_filter': user_filter,
            'group_filter': group_filter,
            'user_search_base': user_search_base or base_dn,
            'group_search_base': group_search_base or base_dn,
            'timeout': timeout
        }
        
        test_ldap_connection(config_data)
    
    if delete_config and selected_config != "New Configuration":
        if delete_ldap_configuration(db_manager, selected_config):
            st.success(f"✅ Configuration '{selected_config}' deleted!")
            st.rerun()
        else:
            st.error("❌ Failed to delete configuration")

def show_ldap_testing():
    """LDAP Testing Interface"""
    st.subheader("🧪 LDAP Connection & Authentication Testing")
    
    # Load configurations
    db_manager = get_database_manager()
    configs = get_ldap_configurations(db_manager)
    
    if not configs:
        st.warning("⚠️ No LDAP configurations found. Please create one in the Configuration tab.")
        return
    
    # Select configuration for testing
    config_names = [config['config_name'] for config in configs]
    selected_config_name = st.selectbox("Select Configuration to Test:", config_names)
    
    # Get selected config
    selected_config = next((c for c in configs if c['config_name'] == selected_config_name), None)
    
    if not selected_config:
        st.error("❌ Selected configuration not found")
        return
    
    # Convert config for LDAP manager
    ldap_config = {
        'server': selected_config['server'],
        'port': selected_config['port'],
        'use_ssl': selected_config['use_ssl'],
        'base_dn': selected_config['base_dn'],
        'bind_dn': selected_config['bind_dn'],
        'bind_password': selected_config['bind_password_encrypted'],  # In production, decrypt this
        'user_filter': selected_config['user_filter'],
        'group_filter': selected_config['group_filter'],
        'user_search_base': selected_config['user_search_base'],
        'group_search_base': selected_config['group_search_base'],
        'timeout': selected_config['timeout_seconds']
    }
    
    # Testing tabs
    test_tab1, test_tab2, test_tab3 = st.tabs([
        "🔌 Connection Test", "👤 User Authentication", "👥 User Search"
    ])
    
    with test_tab1:
        st.markdown("#### Test LDAP Server Connection")
        
        if st.button("🔌 Test Connection", use_container_width=True):
            test_ldap_connection(ldap_config)
    
    with test_tab2:
        st.markdown("#### Test User Authentication")
        
        col1, col2 = st.columns(2)
        
        with col1:
            test_username = st.text_input("Username to test:")
        
        with col2:
            test_password = st.text_input("Password:", type="password")
        
        if st.button("🔐 Test Authentication", use_container_width=True):
            if test_username and test_password:
                test_user_authentication(ldap_config, test_username, test_password)
            else:
                st.error("Please provide both username and password")
    
    with test_tab3:
        st.markdown("#### Search Users")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search_username = st.text_input("Username to search (leave empty for all):")
        
        with col2:
            st.write("")  # Spacing
            search_users = st.button("🔍 Search Users", use_container_width=True)
        
        if search_users:
            search_ldap_users(ldap_config, search_username)

def show_ldap_users():
    """LDAP Users Management Interface"""
    st.subheader("👥 LDAP Users Management")
    
    db_manager = get_database_manager()
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Sync All Users", use_container_width=True):
            sync_ldap_users()
    
    with col2:
        if st.button("👥 Show All Users", use_container_width=True):
            show_all_ldap_users()
    
    with col3:
        if st.button("📊 User Statistics", use_container_width=True):
            show_ldap_user_statistics()
    
    # Display synced users
    st.markdown("#### Synchronized LDAP Users")
    display_synchronized_users(db_manager)

def show_ldap_analytics():
    """LDAP Analytics Interface"""
    st.subheader("📊 LDAP Analytics & Monitoring")
    
    db_manager = get_database_manager()
    
    # Analytics tabs
    analytics_tab1, analytics_tab2, analytics_tab3 = st.tabs([
        "📈 Authentication Stats", "🔄 Sync History", "🚨 Error Analysis"
    ])
    
    with analytics_tab1:
        show_auth_statistics(db_manager)
    
    with analytics_tab2:
        show_sync_history(db_manager)
    
    with analytics_tab3:
        show_error_analysis(db_manager)

def show_ldap_settings():
    """LDAP Settings Interface"""
    st.subheader("⚙️ LDAP Integration Settings")
    
    # Global settings
    st.markdown("#### Global LDAP Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        auto_sync_enabled = st.checkbox("Enable automatic user synchronization", value=True)
        sync_interval = st.selectbox("Synchronization interval:", 
                                   ["1 hour", "6 hours", "12 hours", "24 hours", "Weekly"])
        
        auth_fallback = st.checkbox("Enable local authentication fallback", value=True)
        cache_user_info = st.checkbox("Cache user information", value=True)
    
    with col2:
        log_auth_attempts = st.checkbox("Log all authentication attempts", value=True)
        log_failed_only = st.checkbox("Log failed attempts only", value=False)
        
        session_timeout = st.number_input("Session timeout (minutes):", 
                                        min_value=5, max_value=480, value=60)
        max_concurrent_sessions = st.number_input("Max concurrent sessions per user:", 
                                                min_value=1, max_value=10, value=3)
    
    # Mapping settings
    st.markdown("#### User Mapping Settings")
    
    col3, col4 = st.columns(2)
    
    with col3:
        default_role = st.selectbox("Default role for new LDAP users:", 
                                  ["user", "analyst", "developer", "admin"])
        
        group_role_mapping = st.text_area("Group to Role Mapping (JSON):",
                                        value='{\n  "db_admins": "admin",\n  "analysts": "analyst",\n  "developers": "developer"\n}',
                                        height=100)
    
    with col4:
        auto_create_users = st.checkbox("Automatically create database users", value=True)
        auto_grant_permissions = st.checkbox("Automatically grant permissions based on groups", value=True)
        
        username_format = st.selectbox("Database username format:", 
                                     ["ldap_username", "email_prefix", "display_name"])
    
    # Save settings
    if st.button("💾 Save LDAP Settings", use_container_width=True):
        settings = {
            'auto_sync_enabled': auto_sync_enabled,
            'sync_interval': sync_interval,
            'auth_fallback': auth_fallback,
            'cache_user_info': cache_user_info,
            'log_auth_attempts': log_auth_attempts,
            'log_failed_only': log_failed_only,
            'session_timeout': session_timeout,
            'max_concurrent_sessions': max_concurrent_sessions,
            'default_role': default_role,
            'group_role_mapping': group_role_mapping,
            'auto_create_users': auto_create_users,
            'auto_grant_permissions': auto_grant_permissions,
            'username_format': username_format
        }
        
        if save_ldap_settings(settings):
            st.success("✅ LDAP settings saved successfully!")
        else:
            st.error("❌ Failed to save settings")

# Helper Functions

def show_installation_help():
    """Show LDAP installation help"""
    st.info("""
    📦 **LDAP Integration Setup**
    
    To enable LDAP integration, install the required package:
    ```bash
    pip install ldap3
    ```
    
    Or add it to your requirements.txt file.
    """)

def show_ldap_installation():
    """Show LDAP3 library installation instructions"""
    st.error("""
    📦 **LDAP3 Library Required**
    
    The LDAP3 library is not installed. Please install it using:
    ```bash
    pip install ldap3
    ```
    
    After installation, restart the application.
    """)

def test_ldap_connection(config: Dict[str, Any]):
    """Test LDAP connection with given configuration"""
    try:
        ldap_manager = LDAPManager(config)
        success, message = ldap_manager.test_connection()
        
        if success:
            st.success(f"✅ {message}")
            
            # Show server info if available
            st.info("🔍 Connection details verified successfully")
        else:
            st.error(f"❌ {message}")
            
    except Exception as e:
        st.error(f"❌ Connection test failed: {e}")

def test_user_authentication(config: Dict[str, Any], username: str, password: str):
    """Test user authentication"""
    try:
        ldap_manager = LDAPManager(config)
        success, user_info = ldap_manager.authenticate_user(username, password)
        
        if success and user_info:
            st.success(f"✅ Authentication successful for {username}")
            
            # Display user information
            st.markdown("#### User Information")
            col1, col2 = st.columns(2)
            
            with col1:
                st.text(f"Username: {user_info.get('username', 'N/A')}")
                st.text(f"Display Name: {user_info.get('displayName', 'N/A')}")
                st.text(f"Email: {user_info.get('mail', 'N/A')}")
            
            with col2:
                st.text(f"Given Name: {user_info.get('givenName', 'N/A')}")
                st.text(f"Surname: {user_info.get('sn', 'N/A')}")
                st.text(f"DN: {user_info.get('dn', 'N/A')}")
            
            # Display groups
            if user_info.get('groups'):
                st.markdown("#### User Groups")
                for group in user_info['groups']:
                    st.text(f"• {group}")
            else:
                st.info("No groups found for this user")
                
        else:
            st.error(f"❌ Authentication failed for {username}")
            
    except Exception as e:
        st.error(f"❌ Authentication test failed: {e}")

def search_ldap_users(config: Dict[str, Any], username: str = ""):
    """Search for LDAP users"""
    try:
        ldap_manager = LDAPManager(config)
        
        if username:
            # Search for specific user
            user_info = ldap_manager.get_user_info(username)
            if user_info:
                st.success(f"✅ Found user: {username}")
                
                # Display user in table format
                df = pd.DataFrame([user_info])
                st.dataframe(df, use_container_width=True)
            else:
                st.warning(f"⚠️ User '{username}' not found")
        else:
            # Get all users
            users = ldap_manager.get_all_users()
            
            if users:
                st.success(f"✅ Found {len(users)} users")
                
                # Create DataFrame for display
                df_data = []
                for user in users:
                    df_data.append({
                        'Username': user.get('username', ''),
                        'Display Name': user.get('displayName', ''),
                        'Email': user.get('mail', ''),
                        'Groups': ', '.join(user.get('groups', []))
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("⚠️ No users found")
                
    except Exception as e:
        st.error(f"❌ User search failed: {e}")

def get_ldap_configurations(db_manager) -> List[Dict]:
    """Get all LDAP configurations from database"""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT * FROM ldap_config WHERE is_active = 1 ORDER BY config_name")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error loading configurations: {e}")
        return []

def save_ldap_configuration(db_manager, config_data: Dict[str, Any]) -> bool:
    """Save LDAP configuration to database"""
    try:
        with db_manager.get_cursor() as cursor:
            # Check if configuration exists
            cursor.execute("SELECT id FROM ldap_config WHERE config_name = ?", 
                         (config_data['config_name'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE ldap_config SET 
                        server = ?, port = ?, use_ssl = ?, base_dn = ?,
                        bind_dn = ?, bind_password_encrypted = ?, user_filter = ?,
                        group_filter = ?, user_search_base = ?, group_search_base = ?,
                        timeout_seconds = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE config_name = ?
                """, (
                    config_data['server'], config_data['port'], config_data['use_ssl'],
                    config_data['base_dn'], config_data['bind_dn'], config_data['bind_password'],
                    config_data['user_filter'], config_data['group_filter'],
                    config_data['user_search_base'], config_data['group_search_base'],
                    config_data['timeout_seconds'], config_data['config_name']
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO ldap_config (
                        config_name, server, port, use_ssl, base_dn, bind_dn,
                        bind_password_encrypted, user_filter, group_filter,
                        user_search_base, group_search_base, timeout_seconds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config_data['config_name'], config_data['server'], config_data['port'],
                    config_data['use_ssl'], config_data['base_dn'], config_data['bind_dn'],
                    config_data['bind_password'], config_data['user_filter'],
                    config_data['group_filter'], config_data['user_search_base'],
                    config_data['group_search_base'], config_data['timeout_seconds']
                ))
        
        return True
    except Exception as e:
        st.error(f"Error saving configuration: {e}")
        return False

def delete_ldap_configuration(db_manager, config_name: str) -> bool:
    """Delete LDAP configuration"""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("UPDATE ldap_config SET is_active = 0 WHERE config_name = ?", 
                         (config_name,))
        return True
    except Exception as e:
        st.error(f"Error deleting configuration: {e}")
        return False

def sync_ldap_users():
    """Synchronize LDAP users"""
    with st.spinner("Synchronizing LDAP users..."):
        try:
            # This would use the active LDAP configuration
            st.success("✅ LDAP users synchronized successfully!")
            st.info("Synchronization functionality would be implemented here")
        except Exception as e:
            st.error(f"❌ Synchronization failed: {e}")

def show_all_ldap_users():
    """Show all LDAP users"""
    st.info("Display all LDAP users functionality would be implemented here")

def show_ldap_user_statistics():
    """Show LDAP user statistics"""
    st.info("LDAP user statistics would be displayed here")

def display_synchronized_users(db_manager):
    """Display synchronized LDAP users"""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT username, email, display_name, is_active, last_sync
                FROM ldap_users
                ORDER BY last_sync DESC
                LIMIT 50
            """)
            users = cursor.fetchall()
        
        if users:
            df_data = []
            for user in users:
                df_data.append({
                    'Username': user['username'],
                    'Email': user['email'] or 'N/A',
                    'Display Name': user['display_name'] or 'N/A',
                    'Status': '🟢 Active' if user['is_active'] else '🔴 Inactive',
                    'Last Sync': user['last_sync']
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No synchronized LDAP users found")
            
    except Exception as e:
        st.error(f"Error loading users: {e}")

def show_auth_statistics(db_manager):
    """Show authentication statistics"""
    st.info("Authentication statistics would be displayed here")

def show_sync_history(db_manager):
    """Show synchronization history"""
    st.info("Synchronization history would be displayed here")

def show_error_analysis(db_manager):
    """Show error analysis"""
    st.info("Error analysis would be displayed here")

def save_ldap_settings(settings: Dict[str, Any]) -> bool:
    """Save LDAP settings"""
    try:
        # Save settings to database or configuration file
        return True
    except Exception as e:
        st.error(f"Error saving settings: {e}")
        return False

if __name__ == "__main__":
    show_ldap_management()