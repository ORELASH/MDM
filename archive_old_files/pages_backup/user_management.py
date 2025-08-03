"""
RedshiftManager User Management Page
Comprehensive user management interface with RBAC (Role-Based Access Control).
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import hashlib

# Import our models
try:
    from models.database_models import get_database_manager, User, Role, UserSession, AuditLog, UserRoleType, AuditActionType
    from models.encryption_model import get_password_validator, get_encryption_manager
    from utils.i18n_helper import get_text, apply_rtl_css, get_streamlit_helper
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()


def user_management_page():
    """Main user management page."""
    
    # Apply RTL CSS if needed
    apply_rtl_css()
    
    # Page title
    st.title("👥 " + get_text("nav.users", "User Management"))
    st.markdown("---")
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Sidebar for actions
    with st.sidebar:
        st.header(get_text("user.actions", "User Actions"))
        
        action = st.selectbox(
            get_text("user.select_action", "Select Action"),
            [
                get_text("user.view_all", "View All Users"),
                get_text("user.add", "Add User"),
                get_text("user.edit", "Edit User"),
                get_text("user.manage_roles", "Manage User Roles"),
                get_text("user.reset_password", "Reset Password"),
                get_text("user.delete", "Delete User"),
                get_text("user.view_sessions", "View Active Sessions"),
                get_text("user.audit_logs", "View Audit Logs")
            ]
        )
    
    # Main content area
    if action == get_text("user.view_all", "View All Users"):
        show_all_users(db_manager)
    elif action == get_text("user.add", "Add User"):
        add_user_form(db_manager)
    elif action == get_text("user.edit", "Edit User"):
        edit_user_form(db_manager)
    elif action == get_text("user.manage_roles", "Manage User Roles"):
        manage_user_roles_form(db_manager)
    elif action == get_text("user.reset_password", "Reset Password"):
        reset_password_form(db_manager)
    elif action == get_text("user.delete", "Delete User"):
        delete_user_form(db_manager)
    elif action == get_text("user.view_sessions", "View Active Sessions"):
        show_active_sessions(db_manager)
    elif action == get_text("user.audit_logs", "View Audit Logs"):
        show_audit_logs(db_manager)


def show_all_users(db_manager):
    """Display all users in a table."""
    
    st.subheader("👥 " + get_text("user.all_users", "All Users"))
    
    try:
        with db_manager.session_scope() as session:
            users = session.query(User).all()
            
            if not users:
                st.info(get_text("user.no_users", "No users found. Create the first user!"))
                return
            
            # Create DataFrame for display
            user_data = []
            for user in users:
                # Get user roles
                roles = [role.name for role in user.roles]
                
                user_data.append({
                    "ID": user.id,
                    get_text("user.username", "Username"): user.username,
                    get_text("user.email", "Email"): user.email,
                    get_text("user.full_name", "Full Name"): user.full_name,
                    get_text("user.roles", "Roles"): ", ".join(roles) if roles else get_text("user.no_roles", "No roles"),
                    get_text("user.status", "Status"): "🔒" + get_text("user.locked", "Locked") if user.is_locked else ("✅" + get_text("user.active", "Active") if user.is_active else "❌" + get_text("user.inactive", "Inactive")),
                    get_text("user.last_login", "Last Login"): user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else get_text("user.never", "Never"),
                    get_text("user.login_count", "Login Count"): user.login_count,
                    get_text("user.created", "Created"): user.created_at.strftime("%Y-%m-%d")
                })
            
            df = pd.DataFrame(user_data)
            st.dataframe(df, use_container_width=True)
            
            # User statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(get_text("user.total_users", "Total Users"), len(users))
            
            with col2:
                active_users = sum(1 for u in users if u.is_active)
                st.metric(get_text("user.active_users", "Active"), active_users)
            
            with col3:
                locked_users = sum(1 for u in users if u.is_locked)
                st.metric(get_text("user.locked_users", "Locked"), locked_users)
            
            with col4:
                recent_logins = sum(1 for u in users if u.last_login and u.last_login > datetime.utcnow() - timedelta(days=7))
                st.metric(get_text("user.recent_logins", "Recent Logins (7d)"), recent_logins)
    
    except Exception as e:
        st.error(f"Error loading users: {e}")


def add_user_form(db_manager):
    """Form to add a new user."""
    
    st.subheader("➕ " + get_text("user.add", "Add New User"))
    
    # Get available roles
    try:
        with db_manager.session_scope() as session:
            roles = session.query(Role).filter_by(is_active=True).all()
    except Exception as e:
        st.error(f"Error loading roles: {e}")
        return
    
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input(
                get_text("user.username", "Username") + " *",
                help=get_text("user.username_help", "Unique username for login")
            )
            
            email = st.text_input(
                get_text("user.email", "Email") + " *",
                help=get_text("user.email_help", "User's email address")
            )
            
            first_name = st.text_input(
                get_text("user.first_name", "First Name"),
                help=get_text("user.first_name_help", "User's first name")
            )
            
            last_name = st.text_input(
                get_text("user.last_name", "Last Name"),
                help=get_text("user.last_name_help", "User's last name")
            )
        
        with col2:
            password = st.text_input(
                get_text("user.password", "Password") + " *",
                type="password",
                help=get_text("user.password_help", "Strong password required")
            )
            
            confirm_password = st.text_input(
                get_text("user.confirm_password", "Confirm Password") + " *",
                type="password"
            )
            
            is_active = st.checkbox(
                get_text("user.active", "Active"),
                value=True,
                help=get_text("user.active_help", "User can log in when active")
            )
            
            force_password_change = st.checkbox(
                get_text("user.force_password_change", "Force Password Change on First Login"),
                value=True,
                help=get_text("user.force_password_change_help", "User must change password on first login")
            )
        
        # Role selection
        st.subheader(get_text("user.assign_roles", "Assign Roles"))
        selected_roles = []
        
        if roles:
            for role in roles:
                if st.checkbox(f"{role.display_name or role.name}", key=f"role_{role.id}"):
                    selected_roles.append(role.id)
        else:
            st.warning(get_text("user.no_roles_available", "No roles available. Create roles first."))
        
        # Additional settings
        with st.expander("⚙️ " + get_text("user.additional_settings", "Additional Settings")):
            col3, col4 = st.columns(2)
            
            with col3:
                preferred_language = st.selectbox(
                    get_text("user.preferred_language", "Preferred Language"),
                    options=["en", "he"],
                    format_func=lambda x: "English" if x == "en" else "Hebrew"
                )
                
                theme = st.selectbox(
                    get_text("user.theme", "Theme"),
                    options=["light", "dark", "auto"]
                )
            
            with col4:
                timezone = st.selectbox(
                    get_text("user.timezone", "Timezone"),
                    options=["UTC", "America/New_York", "Europe/London", "Asia/Jerusalem"],
                    index=3  # Default to Jerusalem
                )
                
                two_factor_enabled = st.checkbox(
                    get_text("user.enable_2fa", "Enable Two-Factor Authentication"),
                    help=get_text("user.2fa_help", "Enhanced security with 2FA")
                )
        
        # Form submission
        col1, col2 = st.columns(2)
        
        with col1:
            validate_only = st.form_submit_button(
                "🔍 " + get_text("user.validate", "Validate Input")
            )
        
        with col2:
            submit = st.form_submit_button(
                "💾 " + get_text("form.save", "Save User")
            )
        
        # Handle form submission
        if validate_only or submit:
            validation_errors = validate_user_input(
                username, email, password, confirm_password
            )
            
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                return
            
            if validate_only:
                st.success(get_text("user.validation_passed", "✅ Validation passed! All fields are valid."))
            
            if submit:
                success = save_user(
                    db_manager, username, email, password, first_name, last_name,
                    is_active, force_password_change, selected_roles,
                    preferred_language, theme, timezone, two_factor_enabled
                )
                
                if success:
                    st.success(get_text("user.saved_successfully", "User created successfully!"))
                    st.experimental_rerun()


def edit_user_form(db_manager):
    """Form to edit an existing user."""
    
    st.subheader("✏️ " + get_text("user.edit", "Edit User"))
    
    try:
        with db_manager.session_scope() as session:
            users = session.query(User).all()
            
            if not users:
                st.info(get_text("user.no_users_to_edit", "No users available to edit."))
                return
            
            # Select user to edit
            user_options = {f"{user.username} ({user.email})": user.id for user in users}
            selected_user_key = st.selectbox(
                get_text("user.select_to_edit", "Select user to edit"),
                options=list(user_options.keys())
            )
            
            if selected_user_key:
                user_id = user_options[selected_user_key]
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    show_edit_user_form(db_manager, user, session)
    
    except Exception as e:
        st.error(f"Error loading users: {e}")


def show_edit_user_form(db_manager, user, session):
    """Show the edit form with pre-populated values."""
    
    roles = session.query(Role).filter_by(is_active=True).all()
    user_role_ids = [role.id for role in user.roles]
    
    with st.form("edit_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input(
                get_text("user.username", "Username") + " *",
                value=user.username
            )
            
            email = st.text_input(
                get_text("user.email", "Email") + " *",
                value=user.email
            )
            
            first_name = st.text_input(
                get_text("user.first_name", "First Name"),
                value=user.first_name or ""
            )
            
            last_name = st.text_input(
                get_text("user.last_name", "Last Name"),
                value=user.last_name or ""
            )
        
        with col2:
            is_active = st.checkbox(
                get_text("user.active", "Active"),
                value=user.is_active
            )
            
            is_verified = st.checkbox(
                get_text("user.verified", "Email Verified"),
                value=user.is_verified
            )
            
            force_password_change = st.checkbox(
                get_text("user.force_password_change", "Force Password Change"),
                value=user.force_password_change
            )
            
            two_factor_enabled = st.checkbox(
                get_text("user.enable_2fa", "Two-Factor Authentication"),
                value=user.two_factor_enabled
            )
        
        # Role management
        st.subheader(get_text("user.manage_roles", "Manage Roles"))
        selected_roles = []
        
        if roles:
            for role in roles:
                is_checked = role.id in user_role_ids
                if st.checkbox(f"{role.display_name or role.name}", value=is_checked, key=f"edit_role_{role.id}"):
                    selected_roles.append(role.id)
        
        # User preferences
        with st.expander("👤 " + get_text("user.preferences", "User Preferences")):
            col3, col4 = st.columns(2)
            
            with col3:
                preferred_language = st.selectbox(
                    get_text("user.preferred_language", "Preferred Language"),
                    options=["en", "he"],
                    index=0 if user.preferred_language == "en" else 1,
                    format_func=lambda x: "English" if x == "en" else "Hebrew"
                )
                
                theme = st.selectbox(
                    get_text("user.theme", "Theme"),
                    options=["light", "dark", "auto"],
                    index=["light", "dark", "auto"].index(user.theme)
                )
            
            with col4:
                timezone = st.selectbox(
                    get_text("user.timezone", "Timezone"),
                    options=["UTC", "America/New_York", "Europe/London", "Asia/Jerusalem"],
                    index=3 if user.timezone == "Asia/Jerusalem" else 0
                )
        
        # User statistics (read-only)
        with st.expander("📊 " + get_text("user.statistics", "User Statistics")):
            col5, col6 = st.columns(2)
            
            with col5:
                st.write(f"**{get_text('user.created', 'Created')}:** {user.created_at.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**{get_text('user.last_login', 'Last Login')}:** {user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else get_text('user.never', 'Never')}")
                st.write(f"**{get_text('user.login_count', 'Login Count')}:** {user.login_count}")
            
            with col6:
                st.write(f"**{get_text('user.failed_attempts', 'Failed Login Attempts')}:** {user.failed_login_attempts}")
                st.write(f"**{get_text('user.locked_until', 'Locked Until')}:** {user.locked_until.strftime('%Y-%m-%d %H:%M') if user.locked_until else get_text('user.not_locked', 'Not locked')}")
                st.write(f"**{get_text('user.password_changed', 'Password Changed')}:** {user.password_changed_at.strftime('%Y-%m-%d') if user.password_changed_at else get_text('user.unknown', 'Unknown')}")
        
        # Form submission
        col1, col2, col3 = st.columns(3)
        
        with col1:
            update = st.form_submit_button(
                "💾 " + get_text("form.update", "Update User")
            )
        
        with col2:
            unlock_user = st.form_submit_button(
                "🔓 " + get_text("user.unlock", "Unlock User")
            )
        
        with col3:
            reset_attempts = st.form_submit_button(
                "🔄 " + get_text("user.reset_attempts", "Reset Failed Attempts")
            )
        
        # Handle form submission
        if update:
            success = update_user(
                db_manager, user.id, username, email, first_name, last_name,
                is_active, is_verified, force_password_change, two_factor_enabled,
                selected_roles, preferred_language, theme, timezone
            )
            
            if success:
                st.success(get_text("user.updated_successfully", "User updated successfully!"))
                st.experimental_rerun()
        
        if unlock_user:
            success = unlock_user_account(db_manager, user.id)
            if success:
                st.success(get_text("user.unlocked_successfully", "User unlocked successfully!"))
                st.experimental_rerun()
        
        if reset_attempts:
            success = reset_failed_attempts(db_manager, user.id)
            if success:
                st.success(get_text("user.attempts_reset", "Failed attempts reset successfully!"))
                st.experimental_rerun()


def manage_user_roles_form(db_manager):
    """Form to manage user roles separately."""
    
    st.subheader("🎭 " + get_text("user.manage_roles", "Manage User Roles"))
    
    try:
        with db_manager.session_scope() as session:
            users = session.query(User).all()
            roles = session.query(Role).filter_by(is_active=True).all()
            
            if not users:
                st.info(get_text("user.no_users", "No users found."))
                return
            
            if not roles:
                st.warning(get_text("user.no_roles_available", "No roles available."))
                return
            
            # Select user
            user_options = {f"{user.username} ({user.email})": user.id for user in users}
            selected_user_key = st.selectbox(
                get_text("user.select_user", "Select User"),
                options=list(user_options.keys())
            )
            
            if selected_user_key:
                user_id = user_options[selected_user_key]
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    current_roles = [role.id for role in user.roles]
                    
                    st.write(f"**{get_text('user.current_roles', 'Current Roles')}:**")
                    if user.roles:
                        for role in user.roles:
                            st.write(f"• {role.display_name or role.name}")
                    else:
                        st.write(get_text("user.no_roles_assigned", "No roles assigned"))
                    
                    st.write("---")
                    
                    # Role selection
                    new_roles = st.multiselect(
                        get_text("user.assign_new_roles", "Assign Roles"),
                        options=[role.id for role in roles],
                        format_func=lambda x: next((role.display_name or role.name for role in roles if role.id == x), "Unknown"),
                        default=current_roles
                    )
                    
                    if st.button("💾 " + get_text("user.update_roles", "Update Roles")):
                        success = update_user_roles(db_manager, user_id, new_roles)
                        if success:
                            st.success(get_text("user.roles_updated", "User roles updated successfully!"))
                            st.experimental_rerun()
    
    except Exception as e:
        st.error(f"Error managing roles: {e}")


def reset_password_form(db_manager):
    """Form to reset user password."""
    
    st.subheader("🔑 " + get_text("user.reset_password", "Reset Password"))
    
    try:
        with db_manager.session_scope() as session:
            users = session.query(User).all()
            
            if not users:
                st.info(get_text("user.no_users", "No users found."))
                return
            
            # Select user
            user_options = {f"{user.username} ({user.email})": user.id for user in users}
            selected_user_key = st.selectbox(
                get_text("user.select_user_password", "Select User for Password Reset"),
                options=list(user_options.keys())
            )
            
            if selected_user_key:
                user_id = user_options[selected_user_key]
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    st.write(f"**{get_text('user.resetting_password_for', 'Resetting password for')}:** {user.username}")
                    
                    with st.form("reset_password_form"):
                        new_password = st.text_input(
                            get_text("user.new_password", "New Password") + " *",
                            type="password",
                            help=get_text("user.password_requirements", "Password must meet security requirements")
                        )
                        
                        confirm_password = st.text_input(
                            get_text("user.confirm_new_password", "Confirm New Password") + " *",
                            type="password"
                        )
                        
                        force_change_on_login = st.checkbox(
                            get_text("user.force_change_on_next_login", "Force change on next login"),
                            value=True
                        )
                        
                        notify_user = st.checkbox(
                            get_text("user.notify_user", "Notify user via email"),
                            value=False,
                            help=get_text("user.notify_help", "Send password reset notification")
                        )
                        
                        if st.form_submit_button("🔑 " + get_text("user.reset_password", "Reset Password")):
                            if not new_password or not confirm_password:
                                st.error(get_text("user.password_required", "Password fields are required"))
                            elif new_password != confirm_password:
                                st.error(get_text("user.passwords_dont_match", "Passwords don't match"))
                            else:
                                # Validate password
                                pv = get_password_validator()
                                is_valid, errors = pv.validate_password(new_password)
                                
                                if not is_valid:
                                    for error in errors:
                                        st.error(error)
                                else:
                                    success = reset_user_password(
                                        db_manager, user_id, new_password, force_change_on_login, notify_user
                                    )
                                    if success:
                                        st.success(get_text("user.password_reset_success", "Password reset successfully!"))
                                        st.experimental_rerun()
    
    except Exception as e:
        st.error(f"Error resetting password: {e}")


def delete_user_form(db_manager):
    """Form to delete a user."""
    
    st.subheader("🗑️ " + get_text("user.delete", "Delete User"))
    st.warning(get_text("user.delete_warning", "⚠️ Deleting a user will remove all associated data and cannot be undone!"))
    
    try:
        with db_manager.session_scope() as session:
            users = session.query(User).all()
            
            if not users:
                st.info(get_text("user.no_users_to_delete", "No users available to delete."))
                return
            
            # Select user to delete
            user_options = {f"{user.username} ({user.email})": user.id for user in users}
            selected_user_key = st.selectbox(
                get_text("user.select_to_delete", "Select user to delete"),
                options=list(user_options.keys())
            )
            
            if selected_user_key:
                user_id = user_options[selected_user_key]
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    # Show user details
                    with st.expander("👤 " + get_text("user.details", "User Details")):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**{get_text('user.username', 'Username')}:** {user.username}")
                            st.write(f"**{get_text('user.email', 'Email')}:** {user.email}")
                            st.write(f"**{get_text('user.full_name', 'Full Name')}:** {user.full_name}")
                        
                        with col2:
                            st.write(f"**{get_text('user.created', 'Created')}:** {user.created_at.strftime('%Y-%m-%d')}")
                            st.write(f"**{get_text('user.login_count', 'Login Count')}:** {user.login_count}")
                            role_names = [role.name for role in user.roles]
                            st.write(f"**{get_text('user.roles', 'Roles')}:** {', '.join(role_names) if role_names else 'None'}")
                    
                    # Confirmation
                    st.error(get_text("user.confirm_delete", "Type 'DELETE' to confirm deletion:"))
                    confirmation = st.text_input(
                        get_text("user.confirmation", "Confirmation"),
                        placeholder="DELETE"
                    )
                    
                    if st.button("🗑️ " + get_text("user.delete_permanently", "Delete Permanently"), type="primary"):
                        if confirmation == "DELETE":
                            success = delete_user(db_manager, user_id)
                            if success:
                                st.success(get_text("user.deleted_successfully", "User deleted successfully!"))
                                st.experimental_rerun()
                        else:
                            st.error(get_text("user.confirmation_required", "Please type 'DELETE' to confirm"))
    
    except Exception as e:
        st.error(f"Error loading users: {e}")


def show_active_sessions(db_manager):
    """Show active user sessions."""
    
    st.subheader("🔗 " + get_text("user.active_sessions", "Active Sessions"))
    
    try:
        with db_manager.session_scope() as session:
            # Get active sessions
            active_sessions = session.query(UserSession).filter(
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ).all()
            
            if not active_sessions:
                st.info(get_text("user.no_active_sessions", "No active sessions found."))
                return
            
            # Create DataFrame
            session_data = []
            for user_session in active_sessions:
                user = session.query(User).filter_by(id=user_session.user_id).first()
                
                session_data.append({
                    "ID": user_session.id,
                    get_text("user.username", "Username"): user.username if user else "Unknown",
                    get_text("user.ip_address", "IP Address"): user_session.ip_address or "Unknown",
                    get_text("user.login_method", "Login Method"): user_session.login_method or "Unknown",
                    get_text("user.created", "Created"): user_session.created_at.strftime("%Y-%m-%d %H:%M"),
                    get_text("user.last_activity", "Last Activity"): user_session.last_activity.strftime("%Y-%m-%d %H:%M") if user_session.last_activity else "Unknown",
                    get_text("user.expires", "Expires"): user_session.expires_at.strftime("%Y-%m-%d %H:%M"),
                    get_text("user.location", "Location"): user_session.location or "Unknown"
                })
            
            df = pd.DataFrame(session_data)
            st.dataframe(df, use_container_width=True)
            
            # Session management
            if st.button("🔄 " + get_text("user.refresh_sessions", "Refresh Sessions")):
                st.experimental_rerun()
            
            # Bulk session management
            with st.expander("⚙️ " + get_text("user.session_management", "Session Management")):
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🚪 " + get_text("user.end_all_sessions", "End All Sessions")):
                        count = end_all_sessions(db_manager)
                        st.success(f"{get_text('user.sessions_ended', 'Ended')} {count} {get_text('user.sessions', 'sessions')}")
                        st.experimental_rerun()
                
                with col2:
                    if st.button("🧹 " + get_text("user.cleanup_expired", "Clean Up Expired Sessions")):
                        count = cleanup_expired_sessions(db_manager)
                        st.success(f"{get_text('user.cleaned_up', 'Cleaned up')} {count} {get_text('user.expired_sessions', 'expired sessions')}")
                        st.experimental_rerun()
    
    except Exception as e:
        st.error(f"Error loading sessions: {e}")


def show_audit_logs(db_manager):
    """Show user audit logs."""
    
    st.subheader("📋 " + get_text("user.audit_logs", "Audit Logs"))
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days_back = st.selectbox(
            get_text("user.time_period", "Time Period"),
            options=[1, 7, 30, 90],
            index=1,
            format_func=lambda x: f"{get_text('user.last', 'Last')} {x} {get_text('user.days', 'days')}"
        )
    
    with col2:
        action_filter = st.selectbox(
            get_text("user.action_filter", "Action Filter"),
            options=["all"] + [action.value for action in AuditActionType],
            format_func=lambda x: get_text("user.all_actions", "All Actions") if x == "all" else x.title()
        )
    
    with col3:
        limit = st.selectbox(
            get_text("user.max_records", "Max Records"),
            options=[50, 100, 500, 1000],
            index=1
        )
    
    try:
        with db_manager.session_scope() as session:
            # Build query
            query = session.query(AuditLog).filter(
                AuditLog.created_at >= datetime.utcnow() - timedelta(days=days_back)
            )
            
            if action_filter != "all":
                query = query.filter(AuditLog.action == AuditActionType(action_filter))
            
            audit_logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
            
            if not audit_logs:
                st.info(get_text("user.no_audit_logs", "No audit logs found for the selected criteria."))
                return
            
            # Create DataFrame
            log_data = []
            for log in audit_logs:
                user = session.query(User).filter_by(id=log.user_id).first() if log.user_id else None
                
                log_data.append({
                    get_text("user.timestamp", "Timestamp"): log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    get_text("user.username", "Username"): user.username if user else "System",
                    get_text("user.action", "Action"): log.action.value if log.action else "Unknown",
                    get_text("user.resource", "Resource"): f"{log.resource_type}:{log.resource_id}" if log.resource_type else "N/A",
                    get_text("user.success", "Success"): "✅" if log.success else "❌",
                    get_text("user.ip_address", "IP"): log.ip_address or "Unknown",
                    get_text("user.details", "Details"): str(log.details)[:50] + "..." if log.details else ""
                })
            
            df = pd.DataFrame(log_data)
            st.dataframe(df, use_container_width=True)
            
            # Export option
            if st.button("📊 " + get_text("user.export_logs", "Export Logs")):
                csv = df.to_csv(index=False)
                st.download_button(
                    label=get_text("user.download_csv", "Download CSV"),
                    data=csv,
                    file_name=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"Error loading audit logs: {e}")


# Helper functions

def validate_user_input(username, email, password, confirm_password):
    """Validate user input."""
    errors = []
    
    if not username or len(username) < 3:
        errors.append(get_text("user.username_too_short", "Username must be at least 3 characters"))
    
    if not email or "@" not in email:
        errors.append(get_text("user.invalid_email", "Invalid email address"))
    
    if not password:
        errors.append(get_text("user.password_required", "Password is required"))
    elif password != confirm_password:
        errors.append(get_text("user.passwords_dont_match", "Passwords don't match"))
    else:
        # Validate password strength
        pv = get_password_validator()
        is_valid, password_errors = pv.validate_password(password)
        if not is_valid:
            errors.extend(password_errors)
    
    return errors


def save_user(db_manager, username, email, password, first_name, last_name,
              is_active, force_password_change, selected_roles,
              preferred_language, theme, timezone, two_factor_enabled):
    """Save a new user to the database."""
    
    try:
        with db_manager.session_scope() as session:
            # Check if username or email already exists
            existing_user = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                st.error(get_text("user.already_exists", "Username or email already exists"))
                return False
            
            # Hash password
            pv = get_password_validator()
            password_hash = pv.hash_password(password)
            
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                is_active=is_active,
                force_password_change=force_password_change,
                preferred_language=preferred_language,
                theme=theme,
                timezone=timezone,
                two_factor_enabled=two_factor_enabled,
                password_changed_at=datetime.utcnow()
            )
            
            # Assign roles
            if selected_roles:
                roles = session.query(Role).filter(Role.id.in_(selected_roles)).all()
                user.roles.extend(roles)
            
            session.add(user)
            session.commit()
            
            return True
    
    except Exception as e:
        st.error(f"Error saving user: {e}")
        return False


def update_user(db_manager, user_id, username, email, first_name, last_name,
                is_active, is_verified, force_password_change, two_factor_enabled,
                selected_roles, preferred_language, theme, timezone):
    """Update an existing user."""
    
    try:
        with db_manager.session_scope() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                st.error(get_text("user.not_found", "User not found"))
                return False
            
            # Update fields
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = is_active
            user.is_verified = is_verified
            user.force_password_change = force_password_change
            user.two_factor_enabled = two_factor_enabled
            user.preferred_language = preferred_language
            user.theme = theme
            user.timezone = timezone
            
            # Update roles
            user.roles.clear()
            if selected_roles:
                roles = session.query(Role).filter(Role.id.in_(selected_roles)).all()
                user.roles.extend(roles)
            
            session.commit()
            return True
    
    except Exception as e:
        st.error(f"Error updating user: {e}")
        return False


def update_user_roles(db_manager, user_id, role_ids):
    """Update user roles."""
    
    try:
        with db_manager.session_scope() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            # Clear existing roles
            user.roles.clear()
            
            # Add new roles
            if role_ids:
                roles = session.query(Role).filter(Role.id.in_(role_ids)).all()
                user.roles.extend(roles)
            
            session.commit()
            return True
    
    except Exception as e:
        st.error(f"Error updating user roles: {e}")
        return False


def reset_user_password(db_manager, user_id, new_password, force_change_on_login, notify_user):
    """Reset user password."""
    
    try:
        with db_manager.session_scope() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            # Hash new password
            pv = get_password_validator()
            user.password_hash = pv.hash_password(new_password)
            user.password_changed_at = datetime.utcnow()
            user.force_password_change = force_change_on_login
            
            # Reset failed attempts
            user.failed_login_attempts = 0
            user.locked_until = None
            
            session.commit()
            
            # TODO: Send notification email if notify_user is True
            
            return True
    
    except Exception as e:
        st.error(f"Error resetting password: {e}")
        return False


def unlock_user_account(db_manager, user_id):
    """Unlock a user account."""
    
    try:
        with db_manager.session_scope() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            user.locked_until = None
            user.failed_login_attempts = 0
            
            session.commit()
            return True
    
    except Exception as e:
        st.error(f"Error unlocking user: {e}")
        return False


def reset_failed_attempts(db_manager, user_id):
    """Reset failed login attempts."""
    
    try:
        with db_manager.session_scope() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            user.failed_login_attempts = 0
            
            session.commit()
            return True
    
    except Exception as e:
        st.error(f"Error resetting failed attempts: {e}")
        return False


def delete_user(db_manager, user_id):
    """Delete a user."""
    
    try:
        with db_manager.session_scope() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            session.delete(user)
            session.commit()
            return True
    
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False


def end_all_sessions(db_manager):
    """End all active sessions."""
    
    try:
        with db_manager.session_scope() as session:
            count = session.query(UserSession).filter_by(is_active=True).count()
            session.query(UserSession).filter_by(is_active=True).update({"is_active": False})
            session.commit()
            return count
    
    except Exception as e:
        st.error(f"Error ending sessions: {e}")
        return 0


def cleanup_expired_sessions(db_manager):
    """Clean up expired sessions."""
    
    try:
        with db_manager.session_scope() as session:
            count = session.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).count()
            
            session.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()
            
            session.commit()
            return count
    
    except Exception as e:
        st.error(f"Error cleaning up sessions: {e}")
        return 0


if __name__ == "__main__":
    user_management_page()