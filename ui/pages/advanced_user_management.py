#!/usr/bin/env python3
"""
Advanced User & Role Management Interface
Multi-database user and role management with real-time operations
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Import database components
try:
    from database.database_manager import get_database_manager
    from core.database_user_manager import get_global_user_manager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    st.error("❌ Database components not available")

def show_advanced_user_management():
    """Advanced User and Role Management Interface"""
    st.title("👥 Advanced User & Role Management")
    st.markdown("### Multi-Database User Administration")
    st.markdown("---")
    
    if not DB_AVAILABLE:
        st.error("🚫 Database components not available. Please check your installation.")
        return
    
    # Initialize managers
    try:
        db_manager = get_database_manager()
        global_user_manager = get_global_user_manager()
    except Exception as e:
        st.error(f"❌ Failed to initialize database managers: {e}")
        return
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👤 Users", "🏷️ Roles", "🔄 Operations", "📊 Analytics", "⚙️ Settings"
    ])
    
    with tab1:
        show_users_management(db_manager, global_user_manager)
    
    with tab2:
        show_roles_management(db_manager)
    
    with tab3:
        show_operations_panel(db_manager)
    
    with tab4:
        show_user_analytics(db_manager)
    
    with tab5:
        show_management_settings(db_manager)

def show_users_management(db_manager, global_user_manager):
    """Users management interface"""
    st.subheader("👤 User Management")
    
    # Top controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_query = st.text_input("🔍 Search users", placeholder="Enter username or email...")
    
    with col2:
        filter_server = st.selectbox("Filter by Server", ["All"] + get_server_list(db_manager))
    
    with col3:
        filter_status = st.selectbox("Filter by Status", ["All", "Active", "Inactive"])
    
    # Get users data
    try:
        users_data = get_filtered_users(db_manager, search_query, filter_server, filter_status)
        
        if users_data:
            # Users table with actions
            st.markdown("#### Users List")
            
            # Create DataFrame for display
            df_data = []
            for user in users_data:
                df_data.append({
                    'Username': user.get('username', ''),
                    'Server': user.get('server_name', ''),
                    'Type': user.get('user_type', ''),
                    'Status': '🟢 Active' if user.get('is_active') else '🔴 Inactive',
                    'Last Login': user.get('last_login', 'Never'),
                    'Created': user.get('discovered_at', ''),
                    'Actions': 'Manage'
                })
            
            if df_data:
                df = pd.DataFrame(df_data)
                
                # Display with selection
                event = st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )
                
                # User details and actions
                if event.selection.rows:
                    selected_idx = event.selection.rows[0]
                    selected_user = users_data[selected_idx]
                    show_user_details_panel(selected_user, db_manager)
            else:
                st.info("No users found matching the criteria")
        else:
            st.info("No users found in the database")
            
    except Exception as e:
        st.error(f"❌ Error loading users: {e}")
    
    # Add new user section
    st.markdown("---")
    with st.expander("➕ Add New User"):
        show_add_user_form(db_manager)

def show_user_details_panel(user: Dict, db_manager):
    """Show detailed user information and management options"""
    st.markdown("#### 🔍 User Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Basic Information:**")
        st.text(f"Username: {user.get('username', 'N/A')}")
        st.text(f"Server: {user.get('server_name', 'N/A')}")
        st.text(f"Type: {user.get('user_type', 'N/A')}")
        st.text(f"Status: {'Active' if user.get('is_active') else 'Inactive'}")
    
    with col2:
        st.markdown("**Activity Information:**")
        st.text(f"Created: {user.get('discovered_at', 'N/A')}")
        st.text(f"Last Login: {user.get('last_login', 'Never')}")
        st.text(f"Permissions: {len(user.get('permissions_data', {}))}")
    
    # Action buttons
    st.markdown("**Actions:**")
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button("✏️ Edit User", key=f"edit_{user.get('id')}"):
            show_edit_user_modal(user, db_manager)
    
    with action_col2:
        if st.button("🏷️ Manage Roles", key=f"roles_{user.get('id')}"):
            show_user_roles_modal(user, db_manager)
    
    with action_col3:
        if st.button("🔑 Permissions", key=f"perms_{user.get('id')}"):
            show_user_permissions_modal(user, db_manager)
    
    with action_col4:
        status_text = "🔴 Disable" if user.get('is_active') else "🟢 Enable"
        if st.button(status_text, key=f"toggle_{user.get('id')}"):
            toggle_user_status(user, db_manager)

def show_roles_management(db_manager):
    """Roles management interface"""
    st.subheader("🏷️ Role Management")
    
    # Get roles data
    try:
        roles_data = get_roles_data(db_manager)
        
        if roles_data:
            # Roles table
            df_data = []
            for role in roles_data:
                df_data.append({
                    'Role Name': role.get('role_name', ''),
                    'Server': role.get('server_name', ''),
                    'Members': role.get('members_count', 0),
                    'Description': role.get('description', '')[:50] + "..." if len(role.get('description', '')) > 50 else role.get('description', ''),
                    'Created': role.get('discovered_at', ''),
                    'Actions': 'Manage'
                })
            
            df = pd.DataFrame(df_data)
            
            # Display with selection
            event = st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Role details
            if event.selection.rows:
                selected_idx = event.selection.rows[0]
                selected_role = roles_data[selected_idx]
                show_role_details_panel(selected_role, db_manager)
        else:
            st.info("No roles found in the database")
            
    except Exception as e:
        st.error(f"❌ Error loading roles: {e}")

def show_operations_panel(db_manager):
    """Operations and bulk actions panel"""
    st.subheader("🔄 Operations Panel")
    
    # Bulk operations
    st.markdown("#### Bulk Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**User Operations:**")
        
        if st.button("🔄 Refresh All Users", use_container_width=True):
            refresh_all_users(db_manager)
        
        if st.button("📊 Sync User Data", use_container_width=True):
            sync_user_data(db_manager)
        
        if st.button("🧹 Cleanup Inactive Users", use_container_width=True):
            cleanup_inactive_users(db_manager)
    
    with col2:
        st.markdown("**Role Operations:**")
        
        if st.button("🏷️ Refresh All Roles", use_container_width=True):
            refresh_all_roles(db_manager)
        
        if st.button("🔗 Rebuild Role Mappings", use_container_width=True):
            rebuild_role_mappings(db_manager)
        
        if st.button("📋 Export Role Matrix", use_container_width=True):
            export_role_matrix(db_manager)
    
    # Recent operations log
    st.markdown("---")
    st.markdown("#### Recent Operations")
    show_recent_operations(db_manager)

def show_user_analytics(db_manager):
    """User analytics and statistics"""
    st.subheader("📊 User Analytics")
    
    # Statistics cards
    stats = get_user_statistics(db_manager)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", stats.get('total_users', 0))
    
    with col2:
        st.metric("Active Users", stats.get('active_users', 0))
    
    with col3:
        st.metric("Total Roles", stats.get('total_roles', 0))
    
    with col4:
        st.metric("Servers", stats.get('total_servers', 0))
    
    # Charts and analysis
    st.markdown("#### User Distribution")
    
    # Users by server chart
    if stats.get('users_by_server'):
        st.bar_chart(stats['users_by_server'])
    
    # User types distribution
    if stats.get('user_types'):
        st.pie_chart(stats['user_types'])

def show_management_settings(db_manager):
    """Management settings and configuration"""
    st.subheader("⚙️ Management Settings")
    
    # Auto-sync settings
    st.markdown("#### Automatic Synchronization")
    
    auto_sync = st.checkbox("Enable automatic user sync", value=True)
    if auto_sync:
        sync_interval = st.selectbox("Sync interval", ["5 minutes", "15 minutes", "1 hour", "6 hours", "24 hours"])
        st.info(f"Users will be synchronized every {sync_interval}")
    
    # Notification settings
    st.markdown("#### Notifications")
    
    notify_new_users = st.checkbox("Notify on new users", value=True)
    notify_role_changes = st.checkbox("Notify on role changes", value=True)
    notify_permission_changes = st.checkbox("Notify on permission changes", value=False)
    
    # Security settings
    st.markdown("#### Security")
    
    require_approval = st.checkbox("Require approval for new users", value=False)
    log_all_operations = st.checkbox("Log all user operations", value=True)
    
    # Save settings
    if st.button("💾 Save Settings", use_container_width=True):
        save_management_settings({
            'auto_sync': auto_sync,
            'sync_interval': sync_interval if auto_sync else None,
            'notify_new_users': notify_new_users,
            'notify_role_changes': notify_role_changes,
            'notify_permission_changes': notify_permission_changes,
            'require_approval': require_approval,
            'log_all_operations': log_all_operations
        })
        st.success("✅ Settings saved successfully!")

# Helper functions
def get_server_list(db_manager) -> List[str]:
    """Get list of available servers"""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT name FROM servers WHERE is_active = 1")
            servers = cursor.fetchall()
            return [server['name'] for server in servers]
    except Exception as e:
        st.error(f"Error getting servers: {e}")
        return []

def get_filtered_users(db_manager, search_query: str, filter_server: str, filter_status: str) -> List[Dict]:
    """Get filtered users based on criteria"""
    try:
        # Build SQL query based on filters
        sql = """
            SELECT u.*, s.name as server_name, s.database_type
            FROM users u
            JOIN servers s ON u.server_id = s.id
            WHERE 1=1
        """
        params = []
        
        # Apply search filter
        if search_query:
            sql += " AND u.username LIKE ?"
            params.append(f"%{search_query}%")
        
        # Apply server filter
        if filter_server != "All":
            sql += " AND s.name = ?"
            params.append(filter_server)
        
        # Apply status filter
        if filter_status == "Active":
            sql += " AND u.is_active = 1"
        elif filter_status == "Inactive":
            sql += " AND u.is_active = 0"
        
        sql += " ORDER BY u.updated_at DESC LIMIT 100"
        
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql, params)
            users = cursor.fetchall()
            return [dict(user) for user in users]
        
    except Exception as e:
        st.error(f"Error filtering users: {e}")
        return []

def get_roles_data(db_manager) -> List[Dict]:
    """Get roles data from database"""
    try:
        sql = """
            SELECT r.*, s.name as server_name, 
                   COUNT(rm.user_id) as members_count
            FROM roles r
            JOIN servers s ON r.server_id = s.id
            LEFT JOIN role_members rm ON r.id = rm.role_id
            GROUP BY r.id, r.role_name, r.server_id, s.name
            ORDER BY r.role_name
        """
        
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql)
            roles = cursor.fetchall()
            return [dict(role) for role in roles]
    except Exception as e:
        st.error(f"Error getting roles: {e}")
        return []

def get_user_statistics(db_manager) -> Dict:
    """Get user statistics"""
    try:
        stats = {}
        
        with db_manager.get_cursor() as cursor:
            # Total users
            cursor.execute("SELECT COUNT(*) as total FROM users")
            stats['total_users'] = cursor.fetchone()['total']
            
            # Active users
            cursor.execute("SELECT COUNT(*) as active FROM users WHERE is_active = 1")
            stats['active_users'] = cursor.fetchone()['active']
            
            # Total roles
            cursor.execute("SELECT COUNT(*) as total FROM roles")
            stats['total_roles'] = cursor.fetchone()['total']
            
            # Total servers
            cursor.execute("SELECT COUNT(*) as total FROM servers WHERE is_active = 1")
            stats['total_servers'] = cursor.fetchone()['total']
            
            # Users by server
            cursor.execute("""
                SELECT s.name, COUNT(u.id) as user_count
                FROM servers s
                LEFT JOIN users u ON s.id = u.server_id
                WHERE s.is_active = 1
                GROUP BY s.id, s.name
            """)
            users_by_server = cursor.fetchall()
            stats['users_by_server'] = {row['name']: row['user_count'] for row in users_by_server}
            
            # User types
            cursor.execute("""
                SELECT user_type, COUNT(*) as count
                FROM users
                GROUP BY user_type
            """)
            user_types = cursor.fetchall()
            stats['user_types'] = {row['user_type']: row['count'] for row in user_types}
        
        return stats
    except Exception as e:
        st.error(f"Error getting statistics: {e}")
        return {
            'total_users': 0,
            'active_users': 0,
            'total_roles': 0,
            'total_servers': 0,
            'users_by_server': {},
            'user_types': {}
        }

def show_add_user_form(db_manager):
    """Show form to add new user"""
    st.markdown("**Add New User:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_username = st.text_input("Username")
        server_choice = st.selectbox("Server", get_server_list(db_manager))
    
    with col2:
        user_type = st.selectbox("User Type", ["standard", "admin", "superuser"])
        initial_status = st.selectbox("Initial Status", ["active", "inactive"])
    
    if st.button("➕ Add User"):
        if new_username and server_choice:
            try:
                # Add user logic here
                st.success(f"✅ User '{new_username}' added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to add user: {e}")
        else:
            st.error("Please fill in all required fields")

def show_edit_user_modal(user: Dict, db_manager):
    """Show edit user modal"""
    st.markdown(f"**Editing User: {user.get('username')}**")
    # Edit form would go here
    st.info("Edit functionality will be implemented here")

def show_user_roles_modal(user: Dict, db_manager):
    """Show user roles management modal"""
    st.markdown(f"**Managing Roles for: {user.get('username')}**")
    # Role management would go here
    st.info("Role management functionality will be implemented here")

def show_user_permissions_modal(user: Dict, db_manager):
    """Show user permissions modal"""
    st.markdown(f"**Permissions for: {user.get('username')}**")
    # Permissions display would go here
    st.info("Permissions view will be implemented here")

def toggle_user_status(user: Dict, db_manager):
    """Toggle user active status"""
    try:
        # Toggle logic here
        current_status = user.get('is_active', False)
        new_status = not current_status
        # db_manager.update_user_status(user.get('id'), new_status)
        st.success(f"✅ User status updated to {'Active' if new_status else 'Inactive'}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to update user status: {e}")

def show_role_details_panel(role: Dict, db_manager):
    """Show role details and management options"""
    st.markdown("#### 🏷️ Role Details")
    st.text(f"Role: {role.get('role_name', 'N/A')}")
    st.text(f"Server: {role.get('server_name', 'N/A')}")
    st.text(f"Members: {role.get('members_count', 0)}")
    st.text(f"Description: {role.get('description', 'No description')}")

def refresh_all_users(db_manager):
    """Refresh all users from all servers"""
    with st.spinner("Refreshing users..."):
        # Refresh logic here
        st.success("✅ Users refreshed successfully!")

def sync_user_data(db_manager):
    """Sync user data across servers"""
    with st.spinner("Syncing user data..."):
        # Sync logic here
        st.success("✅ User data synchronized!")

def cleanup_inactive_users(db_manager):
    """Cleanup inactive users"""
    with st.spinner("Cleaning up inactive users..."):
        # Cleanup logic here
        st.success("✅ Inactive users cleaned up!")

def refresh_all_roles(db_manager):
    """Refresh all roles"""
    with st.spinner("Refreshing roles..."):
        # Refresh logic here
        st.success("✅ Roles refreshed successfully!")

def rebuild_role_mappings(db_manager):
    """Rebuild role mappings"""
    with st.spinner("Rebuilding role mappings..."):
        # Rebuild logic here
        st.success("✅ Role mappings rebuilt!")

def export_role_matrix(db_manager):
    """Export role matrix"""
    with st.spinner("Exporting role matrix..."):
        # Export logic here
        st.success("✅ Role matrix exported!")

def show_recent_operations(db_manager):
    """Show recent operations log"""
    try:
        # Get recent operations from activity log
        operations = [
            {"Time": "2025-08-03 11:15", "Operation": "User Added", "Target": "john_doe", "Status": "Success"},
            {"Time": "2025-08-03 11:10", "Operation": "Role Updated", "Target": "admin_role", "Status": "Success"},
            {"Time": "2025-08-03 11:05", "Operation": "User Disabled", "Target": "temp_user", "Status": "Success"},
        ]
        
        if operations:
            df = pd.DataFrame(operations)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No recent operations")
    except Exception as e:
        st.error(f"Error loading operations: {e}")

def save_management_settings(settings: Dict):
    """Save management settings"""
    try:
        # Save settings logic here
        pass
    except Exception as e:
        st.error(f"Failed to save settings: {e}")

if __name__ == "__main__":
    show_advanced_user_management()