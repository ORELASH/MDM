"""
Login Page for RedshiftManager
Provides authentication UI with JWT-based login/logout functionality.
Supports user management and session handling.
"""

import streamlit as st
from typing import Dict, Any, Optional
import logging
from datetime import datetime

# Import authentication components
try:
    from utils.auth_manager import (
        auth_manager, login, logout, is_authenticated, get_current_user,
        AuthStatus, UserRole
    )
    from utils.i18n_helper import get_text, apply_rtl_css
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()

logger = logging.getLogger(__name__)

def show_login_form():
    """Display login form"""
    st.markdown("### 🔐 " + get_text("auth.login_title", "RedshiftManager Login"))
    st.markdown("---")
    
    # Login form
    with st.form("login_form", clear_on_submit=False):
        st.markdown("#### " + get_text("auth.enter_credentials", "Enter your credentials"))
        
        username = st.text_input(
            get_text("auth.username", "Username"),
            placeholder="Enter your username",
            key="login_username"
        )
        
        password = st.text_input(
            get_text("auth.password", "Password"),
            type="password",
            placeholder="Enter your password",
            key="login_password"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            login_submitted = st.form_submit_button(
                "🚀 " + get_text("auth.login", "Login"),
                use_container_width=True,
                type="primary"
            )
        
        if login_submitted:
            if username and password:
                with st.spinner(get_text("auth.authenticating", "Authenticating...")):
                    status, token = login(username, password)
                    
                    if status == AuthStatus.SUCCESS:
                        st.success(get_text("auth.login_success", "Login successful!"))
                        st.balloons()
                        
                        # Store token in session state
                        st.session_state.jwt_token = token
                        
                        # Log successful login
                        logger.info(f"User {username} logged in successfully")
                        
                        # Redirect to dashboard
                        st.rerun()
                        
                    elif status == AuthStatus.USER_NOT_FOUND:
                        st.error(get_text("auth.user_not_found", "User not found"))
                        
                    elif status == AuthStatus.INVALID_CREDENTIALS:
                        st.error(get_text("auth.invalid_credentials", "Invalid username or password"))
                        
                    elif status == AuthStatus.ACCOUNT_LOCKED:
                        st.error(get_text("auth.account_locked", "Account is temporarily locked"))
                        
                    else:
                        st.error(get_text("auth.login_failed", "Login failed"))
            else:
                st.warning(get_text("auth.fill_all_fields", "Please fill in all fields"))

def show_user_info():
    """Display current user information"""
    user = get_current_user()
    
    if user:
        st.sidebar.markdown("### 👤 " + get_text("auth.user_info", "User Information"))
        st.sidebar.markdown(f"**{get_text('auth.username', 'Username')}:** {user.username}")
        st.sidebar.markdown(f"**{get_text('auth.email', 'Email')}:** {user.email}")
        st.sidebar.markdown(f"**{get_text('auth.role', 'Role')}:** {user.role.value.title()}")
        
        if user.last_login:
            last_login = datetime.fromisoformat(user.last_login)
            st.sidebar.markdown(f"**{get_text('auth.last_login', 'Last Login')}:** {last_login.strftime('%Y-%m-%d %H:%M')}")
        
        st.sidebar.markdown("---")
        
        # Session info
        session_info = auth_manager.get_session_info()
        if session_info:
            st.sidebar.markdown("### 🔒 " + get_text("auth.session_info", "Session Info"))
            created_at = datetime.fromisoformat(session_info.created_at)
            expires_at = datetime.fromisoformat(session_info.expires_at)
            
            st.sidebar.markdown(f"**{get_text('auth.session_started', 'Started')}:** {created_at.strftime('%H:%M')}")
            st.sidebar.markdown(f"**{get_text('auth.session_expires', 'Expires')}:** {expires_at.strftime('%H:%M')}")
            
            # Session time remaining
            time_remaining = expires_at - datetime.now()
            if time_remaining.total_seconds() > 0:
                hours = int(time_remaining.total_seconds() // 3600)
                minutes = int((time_remaining.total_seconds() % 3600) // 60)
                st.sidebar.markdown(f"**{get_text('auth.time_remaining', 'Time Remaining')}:** {hours:02d}:{minutes:02d}")
            
        st.sidebar.markdown("---")
        
        # Logout button
        if st.sidebar.button("🚪 " + get_text("auth.logout", "Logout"), use_container_width=True):
            if logout():
                st.success(get_text("auth.logout_success", "Logged out successfully"))
                st.rerun()
            else:
                st.error(get_text("auth.logout_failed", "Logout failed"))

def show_registration_form():
    """Display user registration form (admin only)"""
    current_user = get_current_user()
    
    if not current_user or current_user.role != UserRole.ADMIN:
        st.warning(get_text("auth.admin_only", "Administrator access required"))
        return
    
    st.markdown("### ➕ " + get_text("auth.create_user", "Create New User"))
    st.markdown("---")
    
    with st.form("registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input(
                get_text("auth.new_username", "Username"),
                placeholder="Enter username",
                key="reg_username"
            )
            
            new_email = st.text_input(
                get_text("auth.new_email", "Email"),
                placeholder="Enter email address",
                key="reg_email"
            )
        
        with col2:
            new_password = st.text_input(
                get_text("auth.new_password", "Password"),
                type="password",
                placeholder="Enter password",
                key="reg_password"
            )
            
            new_role = st.selectbox(
                get_text("auth.new_role", "Role"),
                options=[role.value for role in UserRole],
                key="reg_role"
            )
        
        if st.form_submit_button(get_text("auth.create_user_btn", "Create User"), type="primary"):
            if new_username and new_email and new_password and new_role:
                try:
                    role_enum = UserRole(new_role)
                    
                    if auth_manager.create_user(new_username, new_email, new_password, role_enum):
                        st.success(f"User '{new_username}' created successfully!")
                        logger.info(f"Admin {current_user.username} created user {new_username}")
                    else:
                        st.error("Failed to create user. Username might already exist.")
                        
                except Exception as e:
                    st.error(f"Error creating user: {e}")
                    logger.error(f"Error creating user: {e}")
            else:
                st.warning("Please fill in all fields")

def show_user_management():
    """Display user management interface (admin only)"""
    current_user = get_current_user()
    
    if not current_user or current_user.role != UserRole.ADMIN:
        return
    
    st.markdown("### 👥 " + get_text("auth.user_management", "User Management"))
    st.markdown("---")
    
    # Show current users
    if auth_manager.users:
        users_data = []
        for username, user in auth_manager.users.items():
            users_data.append({
                'Username': user.username,
                'Email': user.email,
                'Role': user.role.value.title(),
                'Active': "✅" if user.is_active else "❌",
                'Last Login': user.last_login[:16] if user.last_login else "Never",
                'Failed Attempts': user.failed_attempts
            })
        
        st.dataframe(users_data, use_container_width=True)
        
        # Active sessions
        if auth_manager.active_sessions:
            st.markdown("#### 🔒 " + get_text("auth.active_sessions", "Active Sessions"))
            sessions_data = []
            
            for session_id, session in auth_manager.active_sessions.items():
                sessions_data.append({
                    'Username': session.username,
                    'Role': session.role.value.title(),
                    'Started': datetime.fromisoformat(session.created_at).strftime('%H:%M:%S'),
                    'Last Activity': datetime.fromisoformat(session.last_activity).strftime('%H:%M:%S'),
                    'Expires': datetime.fromisoformat(session.expires_at).strftime('%H:%M:%S')
                })
            
            st.dataframe(sessions_data, use_container_width=True)
            
            # Cleanup expired sessions button
            if st.button("🧹 " + get_text("auth.cleanup_sessions", "Cleanup Expired Sessions")):
                cleaned = auth_manager.cleanup_expired_sessions()
                if cleaned > 0:
                    st.success(f"Cleaned up {cleaned} expired sessions")
                else:
                    st.info("No expired sessions to clean up")
    else:
        st.info("No users found")

def check_authentication():
    """Check if user is authenticated and handle redirection"""
    if not is_authenticated():
        return False
    
    # Show user info in sidebar
    show_user_info()
    return True

def login_page():
    """Main login page function"""
    # Apply RTL CSS if needed
    apply_rtl_css()
    
    # Page configuration
    st.set_page_config(
        page_title="RedshiftManager - Login",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Check if already authenticated
    if is_authenticated():
        user = get_current_user()
        st.success(f"Welcome back, {user.username}!")
        
        # Navigation options for authenticated users
        tab1, tab2, tab3 = st.tabs([
            get_text("auth.dashboard", "Dashboard"),
            get_text("auth.profile", "Profile"), 
            get_text("auth.admin", "Admin")
        ])
        
        with tab1:
            st.markdown("### 🏠 " + get_text("auth.welcome", "Welcome to RedshiftManager"))
            st.markdown(get_text("auth.dashboard_desc", "Navigate using the sidebar to access different features."))
            
            # Quick actions
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 " + get_text("nav.dashboard", "Dashboard"), use_container_width=True):
                    st.switch_page("main.py")
            
            with col2:
                if st.button("🔧 " + get_text("nav.settings", "Settings"), use_container_width=True):
                    st.switch_page("pages/settings.py")
            
            with col3:
                if st.button("👥 " + get_text("nav.users", "Users"), use_container_width=True):
                    st.switch_page("pages/user_management.py")
        
        with tab2:
            show_user_info()
            
            # User preferences
            st.markdown("### ⚙️ " + get_text("auth.preferences", "Preferences"))
            
            # Theme selection
            theme = st.selectbox(
                get_text("auth.theme", "Theme"),
                ["Light", "Dark", "Auto"],
                key="user_theme"
            )
            
            # Language selection
            language = st.selectbox(
                get_text("auth.language", "Language"),
                ["English", "עברית"],
                key="user_language"
            )
            
            if st.button(get_text("auth.save_preferences", "Save Preferences")):
                # Save user preferences
                if user:
                    user.preferences.update({
                        'theme': theme.lower(),
                        'language': 'he' if language == 'עברית' else 'en'
                    })
                    auth_manager._save_users()
                    st.success(get_text("auth.preferences_saved", "Preferences saved!"))
        
        with tab3:
            if user and user.role == UserRole.ADMIN:
                show_registration_form()
                st.markdown("---")
                show_user_management()
            else:
                st.warning(get_text("auth.admin_access_required", "Administrator access required"))
    
    else:
        # Show login form
        show_login_form()
        
        # Info section
        st.markdown("---")
        st.markdown("### ℹ️ " + get_text("auth.info_title", "System Information"))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                get_text("auth.total_users", "Total Users"),
                len(auth_manager.users)
            )
        
        with col2:
            st.metric(
                get_text("auth.active_sessions", "Active Sessions"),
                len(auth_manager.active_sessions)
            )
        
        with col3:
            # Show system uptime or version
            st.metric(
                get_text("auth.version", "Version"),
                "1.0.0"
            )

# For direct page access
if __name__ == "__main__":
    login_page()