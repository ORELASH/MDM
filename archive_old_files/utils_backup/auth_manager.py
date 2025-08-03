"""
Advanced Authentication Manager for RedshiftManager
JWT-based authentication with session management and RBAC integration.
Supports multiple authentication methods and secure session handling.
"""

import jwt
import hashlib
import secrets
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import json
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"

class AuthStatus(Enum):
    """Authentication status"""
    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    USER_NOT_FOUND = "user_not_found"
    ACCOUNT_LOCKED = "account_locked"
    SESSION_EXPIRED = "session_expired"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"

@dataclass
class User:
    """User data class"""
    username: str
    email: str
    role: UserRole
    hashed_password: str
    salt: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: Optional[str] = None
    failed_attempts: int = 0
    locked_until: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

@dataclass 
class Session:
    """Session data class"""
    session_id: str
    username: str
    role: UserRole
    created_at: str
    expires_at: str
    last_activity: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AuthenticationManager:
    """Advanced JWT-based authentication manager"""
    
    def __init__(self, secret_key: Optional[str] = None, users_file: str = "data/users.json"):
        self.secret_key = secret_key or self._generate_secret_key()
        self.users_file = Path(users_file)
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Session management
        self.active_sessions: Dict[str, Session] = {}
        self.session_timeout = timedelta(hours=8)
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        
        # Load existing users
        self.users: Dict[str, User] = self._load_users()
        
        # Create default admin user if no users exist
        if not self.users:
            self._create_default_admin()
        
        logger.info("Authentication manager initialized")
    
    def _generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA-256
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hashed.hex(), salt
    
    def _verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against hash"""
        test_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(test_hash, hashed_password)
    
    def _load_users(self) -> Dict[str, User]:
        """Load users from file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                    users = {}
                    for username, data in users_data.items():
                        users[username] = User(
                            username=data['username'],
                            email=data['email'],
                            role=UserRole(data['role']),
                            hashed_password=data['hashed_password'],
                            salt=data['salt'],
                            created_at=data.get('created_at', datetime.now().isoformat()),
                            last_login=data.get('last_login'),
                            failed_attempts=data.get('failed_attempts', 0),
                            locked_until=data.get('locked_until'),
                            preferences=data.get('preferences', {}),
                            is_active=data.get('is_active', True)
                        )
                    return users
            return {}
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}
    
    def _save_users(self) -> bool:
        """Save users to file"""
        try:
            users_data = {}
            for username, user in self.users.items():
                users_data[username] = {
                    'username': user.username,
                    'email': user.email,
                    'role': user.role.value,
                    'hashed_password': user.hashed_password,
                    'salt': user.salt,
                    'created_at': user.created_at,
                    'last_login': user.last_login,
                    'failed_attempts': user.failed_attempts,
                    'locked_until': user.locked_until,
                    'preferences': user.preferences,
                    'is_active': user.is_active
                }
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            return False
    
    def _create_default_admin(self) -> None:
        """Create default admin user"""
        admin_password = "admin123"  # In production, use env var
        hashed_password, salt = self._hash_password(admin_password)
        
        admin_user = User(
            username="admin",
            email="admin@redshiftmanager.com",
            role=UserRole.ADMIN,
            hashed_password=hashed_password,
            salt=salt
        )
        
        self.users["admin"] = admin_user
        self._save_users()
        logger.info("Default admin user created")
    
    def create_user(self, username: str, email: str, password: str, role: UserRole) -> bool:
        """Create a new user"""
        try:
            if username in self.users:
                logger.warning(f"User {username} already exists")
                return False
            
            hashed_password, salt = self._hash_password(password)
            
            new_user = User(
                username=username,
                email=email,
                role=role,
                hashed_password=hashed_password,
                salt=salt
            )
            
            self.users[username] = new_user
            success = self._save_users()
            
            if success:
                logger.info(f"User {username} created successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return False
    
    def authenticate(self, username: str, password: str) -> Tuple[AuthStatus, Optional[str]]:
        """Authenticate user and return JWT token"""
        try:
            # Check if user exists
            if username not in self.users:
                logger.warning(f"Authentication attempt for non-existent user: {username}")
                return AuthStatus.USER_NOT_FOUND, None
            
            user = self.users[username]
            
            # Check if account is locked
            if user.locked_until:
                lock_time = datetime.fromisoformat(user.locked_until)
                if datetime.now() < lock_time:
                    logger.warning(f"Authentication attempt for locked user: {username}")
                    return AuthStatus.ACCOUNT_LOCKED, None
                else:
                    # Unlock account
                    user.locked_until = None
                    user.failed_attempts = 0
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Authentication attempt for inactive user: {username}")
                return AuthStatus.USER_NOT_FOUND, None
            
            # Verify password
            if self._verify_password(password, user.hashed_password, user.salt):
                # Reset failed attempts
                user.failed_attempts = 0
                user.last_login = datetime.now().isoformat()
                self._save_users()
                
                # Create JWT token
                token = self._create_jwt_token(user)
                
                # Create session
                session_id = secrets.token_urlsafe(32)
                session = Session(
                    session_id=session_id,
                    username=username,
                    role=user.role,
                    created_at=datetime.now().isoformat(),
                    expires_at=(datetime.now() + self.session_timeout).isoformat(),
                    last_activity=datetime.now().isoformat()
                )
                
                self.active_sessions[session_id] = session
                
                # Store session in Streamlit session state
                if 'streamlit' in str(type(st)):
                    st.session_state.session_id = session_id
                    st.session_state.username = username
                    st.session_state.user_role = user.role.value
                    st.session_state.authenticated = True
                
                logger.info(f"User {username} authenticated successfully")
                return AuthStatus.SUCCESS, token
            
            else:
                # Handle failed attempt
                user.failed_attempts += 1
                
                if user.failed_attempts >= self.max_failed_attempts:
                    user.locked_until = (datetime.now() + self.lockout_duration).isoformat()
                    logger.warning(f"User {username} locked due to too many failed attempts")
                
                self._save_users()
                logger.warning(f"Failed authentication attempt for user: {username}")
                return AuthStatus.INVALID_CREDENTIALS, None
                
        except Exception as e:
            logger.error(f"Error during authentication for {username}: {e}")
            return AuthStatus.INVALID_CREDENTIALS, None
    
    def _create_jwt_token(self, user: User) -> str:
        """Create JWT token for user"""
        payload = {
            'username': user.username,
            'role': user.role.value,
            'email': user.email,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + self.session_timeout
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return True, payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return False, None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return False, None
    
    def logout(self, session_id: Optional[str] = None) -> bool:
        """Logout user and invalidate session"""
        try:
            if session_id is None:
                session_id = st.session_state.get('session_id')
            
            if session_id and session_id in self.active_sessions:
                username = self.active_sessions[session_id].username
                del self.active_sessions[session_id]
                logger.info(f"User {username} logged out")
            
            # Clear Streamlit session state
            if 'streamlit' in str(type(st)):
                for key in ['session_id', 'username', 'user_role', 'authenticated']:
                    if key in st.session_state:
                        del st.session_state[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    def is_authenticated(self, session_id: Optional[str] = None) -> bool:
        """Check if user is authenticated"""
        try:
            if session_id is None:
                session_id = st.session_state.get('session_id')
            
            if not session_id or session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            
            # Check if session is expired
            if datetime.now() > datetime.fromisoformat(session.expires_at):
                del self.active_sessions[session_id]
                return False
            
            # Update last activity
            session.last_activity = datetime.now().isoformat()
            return True
            
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False
    
    def get_current_user(self, session_id: Optional[str] = None) -> Optional[User]:
        """Get current authenticated user"""
        try:
            if session_id is None:
                session_id = st.session_state.get('session_id')
            
            if not session_id or session_id not in self.active_sessions:
                return None
            
            session = self.active_sessions[session_id]
            return self.users.get(session.username)
            
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return None
    
    def has_permission(self, required_role: UserRole, session_id: Optional[str] = None) -> bool:
        """Check if user has required permission"""
        try:
            user = self.get_current_user(session_id)
            if not user:
                return False
            
            # Role hierarchy: ADMIN > MANAGER > ANALYST > VIEWER
            role_hierarchy = {
                UserRole.VIEWER: 1,
                UserRole.ANALYST: 2, 
                UserRole.MANAGER: 3,
                UserRole.ADMIN: 4
            }
            
            user_level = role_hierarchy.get(user.role, 0)
            required_level = role_hierarchy.get(required_role, 0)
            
            return user_level >= required_level
            
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            return False
    
    def get_session_info(self, session_id: Optional[str] = None) -> Optional[Session]:
        """Get session information"""
        if session_id is None:
            session_id = st.session_state.get('session_id')
        
        return self.active_sessions.get(session_id)
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if now > datetime.fromisoformat(session.expires_at):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)

# Global authentication manager
auth_manager = AuthenticationManager()

# Helper functions
def login(username: str, password: str) -> Tuple[AuthStatus, Optional[str]]:
    """Login helper function"""
    return auth_manager.authenticate(username, password)

def logout() -> bool:
    """Logout helper function"""
    return auth_manager.logout()

def is_authenticated() -> bool:
    """Check authentication status"""
    return auth_manager.is_authenticated()

def get_current_user() -> Optional[User]:
    """Get current user"""
    return auth_manager.get_current_user()

def require_auth(required_role: UserRole = UserRole.VIEWER):
    """Decorator to require authentication"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                st.error("Authentication required")
                st.stop()
            
            if not auth_manager.has_permission(required_role):
                st.error("Insufficient permissions")
                st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator