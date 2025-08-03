"""
Authentication Decorators and Middleware
Provides decorators and middleware for protecting pages and functions.
Integrates with Streamlit pages and the authentication system.
"""

import streamlit as st
from functools import wraps
from typing import Callable, Optional, List
import logging

from .auth_manager import (
    auth_manager, is_authenticated, get_current_user, UserRole
)

logger = logging.getLogger(__name__)

def require_authentication(redirect_to_login: bool = True):
    """
    Decorator that requires user authentication
    
    Args:
        redirect_to_login: Whether to redirect to login page if not authenticated
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                if redirect_to_login:
                    st.error("🔒 Authentication required. Please log in.")
                    st.markdown("[Login Page](pages/login.py)")
                    st.stop()
                else:
                    st.error("Authentication required")
                    return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(required_role: UserRole, show_error: bool = True):
    """
    Decorator that requires specific user role
    
    Args:
        required_role: Minimum required role
        show_error: Whether to show error message if access denied
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                if show_error:
                    st.error("🔒 Authentication required")
                st.stop()
                return None
            
            if not auth_manager.has_permission(required_role):
                if show_error:
                    current_user = get_current_user()
                    st.error(f"🚫 Access denied. Required role: {required_role.value.title()}, Your role: {current_user.role.value.title()}")
                st.stop()
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def admin_only(func: Callable) -> Callable:
    """Decorator that allows only admin users"""
    return require_role(UserRole.ADMIN)(func)

def manager_or_admin(func: Callable) -> Callable:
    """Decorator that allows manager and admin users"""
    return require_role(UserRole.MANAGER)(func)

def analyst_or_above(func: Callable) -> Callable:
    """Decorator that allows analyst, manager and admin users"""
    return require_role(UserRole.ANALYST)(func)

class AuthMiddleware:
    """Authentication middleware for Streamlit pages"""
    
    @staticmethod
    def check_page_access(required_role: Optional[UserRole] = None, 
                         page_name: str = "this page") -> bool:
        """
        Check if user has access to a page
        
        Args:
            required_role: Minimum required role (None for any authenticated user)
            page_name: Name of the page for error messages
            
        Returns:
            True if access granted, False otherwise
        """
        # Check authentication
        if not is_authenticated():
            st.error(f"🔒 Authentication required to access {page_name}")
            st.markdown("Please [login](pages/login.py) to continue")
            
            # Show login button
            if st.button("🚀 Go to Login", type="primary"):
                st.switch_page("pages/login.py")
            
            st.stop()
            return False
        
        # Check role if specified
        if required_role and not auth_manager.has_permission(required_role):
            current_user = get_current_user()
            st.error(f"🚫 Access denied to {page_name}")
            st.warning(f"Required role: {required_role.value.title()}")
            st.info(f"Your role: {current_user.role.value.title()}")
            st.stop()
            return False
        
        return True
    
    @staticmethod
    def show_auth_sidebar():
        """Show authentication info in sidebar"""
        if is_authenticated():
            user = get_current_user()
            
            with st.sidebar:
                st.markdown("### 👤 User Info")
                st.markdown(f"**Username:** {user.username}")
                st.markdown(f"**Role:** {user.role.value.title()}")
                
                # Session info
                session_info = auth_manager.get_session_info()
                if session_info:
                    from datetime import datetime
                    expires_at = datetime.fromisoformat(session_info.expires_at)
                    time_remaining = expires_at - datetime.now()
                    
                    if time_remaining.total_seconds() > 0:
                        hours = int(time_remaining.total_seconds() // 3600)
                        minutes = int((time_remaining.total_seconds() % 3600) // 60)
                        st.markdown(f"**Session:** {hours:02d}:{minutes:02d} remaining")
                    else:
                        st.markdown("**Session:** Expired")
                
                st.markdown("---")
                
                # Quick logout
                if st.button("🚪 Logout", use_container_width=True):
                    from .auth_manager import logout
                    if logout():
                        st.success("Logged out successfully")
                        st.rerun()
    
    @staticmethod
    def init_page_auth(page_name: str, 
                      required_role: Optional[UserRole] = None,
                      show_sidebar: bool = True) -> bool:
        """
        Initialize page with authentication check
        
        Args:
            page_name: Name of the page
            required_role: Minimum required role
            show_sidebar: Whether to show auth info in sidebar
            
        Returns:
            True if authentication successful
        """
        # Check page access
        if not AuthMiddleware.check_page_access(required_role, page_name):
            return False
        
        # Show sidebar info
        if show_sidebar:
            AuthMiddleware.show_auth_sidebar()
        
        # Log page access
        user = get_current_user()
        logger.info(f"User {user.username} accessed {page_name}")
        
        return True

def protected_page(required_role: Optional[UserRole] = None, 
                  page_name: Optional[str] = None):
    """
    Decorator for protecting entire Streamlit pages
    
    Args:
        required_role: Minimum required role
        page_name: Name of the page (auto-detected if None)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Auto-detect page name if not provided
            actual_page_name = page_name or func.__name__.replace('_', ' ').title()
            
            # Initialize page authentication
            if not AuthMiddleware.init_page_auth(actual_page_name, required_role):
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Convenience decorators for common use cases
def public_page(func: Callable) -> Callable:
    """Decorator for public pages (no authentication required)"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Still show auth info in sidebar if user is logged in
        if is_authenticated():
            AuthMiddleware.show_auth_sidebar()
        return func(*args, **kwargs)
    return wrapper

def login_required(func: Callable) -> Callable:
    """Decorator for pages that require login but no specific role"""
    return protected_page()(func)

def admin_page(func: Callable) -> Callable:
    """Decorator for admin-only pages"""
    return protected_page(UserRole.ADMIN)(func)

def manager_page(func: Callable) -> Callable:
    """Decorator for manager-level pages"""
    return protected_page(UserRole.MANAGER)(func)

def analyst_page(func: Callable) -> Callable:
    """Decorator for analyst-level pages"""
    return protected_page(UserRole.ANALYST)(func)

# Helper functions for inline checks
def ensure_authenticated() -> bool:
    """Ensure user is authenticated, show error if not"""
    return AuthMiddleware.check_page_access()

def ensure_role(required_role: UserRole) -> bool:
    """Ensure user has required role, show error if not"""
    return AuthMiddleware.check_page_access(required_role)

def ensure_admin() -> bool:
    """Ensure user is admin"""
    return ensure_role(UserRole.ADMIN)

def ensure_manager() -> bool:
    """Ensure user is manager or admin"""
    return ensure_role(UserRole.MANAGER)

def ensure_analyst() -> bool:
    """Ensure user is analyst or above"""
    return ensure_role(UserRole.ANALYST)

# Context manager for temporary role checks
class RoleContext:
    """Context manager for role-based code blocks"""
    
    def __init__(self, required_role: UserRole, show_error: bool = True):
        self.required_role = required_role
        self.show_error = show_error
        self.has_access = False
    
    def __enter__(self):
        if not is_authenticated():
            if self.show_error:
                st.error("Authentication required")
            return False
        
        if not auth_manager.has_permission(self.required_role):
            if self.show_error:
                current_user = get_current_user()
                st.error(f"Access denied. Required: {self.required_role.value.title()}, Your role: {current_user.role.value.title()}")
            return False
        
        self.has_access = True
        return True
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Usage example:
# with RoleContext(UserRole.ADMIN) as has_admin_access:
#     if has_admin_access:
#         st.write("Admin-only content")
#     else:
#         st.write("Access denied")