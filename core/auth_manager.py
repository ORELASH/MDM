#!/usr/bin/env python3
"""
Authentication Manager for MultiDBManager
Handles both LDAP and local authentication with fallback
"""

import logging
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json

from database.database_manager import get_database_manager

try:
    from core.ldap_integration import get_ldap_manager, LDAP_AVAILABLE
    LDAP_INTEGRATION_AVAILABLE = True
except ImportError:
    LDAP_INTEGRATION_AVAILABLE = False
    LDAP_AVAILABLE = False

class AuthManager:
    """
    Unified authentication manager supporting both LDAP and local authentication
    """
    
    def __init__(self):
        self.logger = logging.getLogger("auth_manager")
        self.db = get_database_manager()
        
        # Configuration
        self.config = {
            'ldap_enabled': LDAP_AVAILABLE and LDAP_INTEGRATION_AVAILABLE,
            'local_fallback': True,
            'session_timeout_hours': 8,
            'max_failed_attempts': 5,
            'lockout_duration_minutes': 30,
            'require_strong_passwords': True,
            'min_password_length': 8
        }
        
        # Initialize local user tables if needed
        self._initialize_local_auth_tables()
    
    def _initialize_local_auth_tables(self):
        """Initialize local authentication tables"""
        try:
            with self.db.get_cursor() as cursor:
                # Local users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS local_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(255) NOT NULL UNIQUE,
                        password_hash VARCHAR(512) NOT NULL,
                        salt VARCHAR(256) NOT NULL,
                        email VARCHAR(255),
                        full_name VARCHAR(255),
                        role VARCHAR(100) DEFAULT 'user',
                        is_active BOOLEAN DEFAULT 1,
                        failed_attempts INTEGER DEFAULT 0,
                        locked_until TIMESTAMP NULL,
                        last_login TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # User sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id VARCHAR(256) NOT NULL UNIQUE,
                        username VARCHAR(255) NOT NULL,
                        auth_method VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Auth attempts log
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(255) NOT NULL,
                        auth_method VARCHAR(50) NOT NULL,
                        success BOOLEAN NOT NULL,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        error_message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_local_users_username ON local_users(username)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_username ON user_sessions(username)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_attempts_username ON auth_attempts(username)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_attempts_timestamp ON auth_attempts(timestamp)")
                
                # Create default admin user if no users exist
                cursor.execute("SELECT COUNT(*) FROM local_users")
                user_count = cursor.fetchone()[0]
                
                if user_count == 0:
                    self._create_default_admin()
                
        except Exception as e:
            self.logger.error(f"Error initializing local auth tables: {e}")
    
    def _create_default_admin(self):
        """Create default admin user"""
        try:
            default_password = "admin123"  # In production, this should be randomly generated
            salt = secrets.token_hex(32)
            password_hash = self._hash_password(default_password, salt)
            
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO local_users (username, password_hash, salt, email, full_name, role)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    'admin',
                    password_hash,
                    salt,
                    'admin@multidb.local',
                    'Default Administrator',
                    'admin'
                ))
            
            self.logger.info("Default admin user created (username: admin, password: admin123)")
            
        except Exception as e:
            self.logger.error(f"Error creating default admin user: {e}")
    
    def authenticate(self, username: str, password: str, ip_address: str = None, user_agent: str = None) -> Tuple[bool, Optional[Dict], str]:
        """
        Authenticate user using LDAP first, then local fallback
        Returns: (success, user_info, method)
        """
        # Check if user is locked out
        if self._is_user_locked(username):
            self._log_auth_attempt(username, 'unknown', False, ip_address, user_agent, 'User account locked')
            return False, None, 'locked'
        
        user_info = None
        auth_method = 'unknown'
        success = False
        error_message = ''
        
        # Try LDAP authentication first if available
        if self.config['ldap_enabled']:
            try:
                ldap_manager = get_ldap_manager()
                success, user_info = ldap_manager.authenticate_user(username, password)
                auth_method = 'ldap'
                
                if success and user_info:
                    # Convert LDAP user info to standard format
                    user_info = self._normalize_ldap_user_info(user_info)
                    self.logger.info(f"LDAP authentication successful for {username}")
                else:
                    error_message = 'LDAP authentication failed'
                    
            except Exception as e:
                self.logger.warning(f"LDAP authentication error for {username}: {e}")
                error_message = f'LDAP error: {e}'
        
        # Try local authentication if LDAP failed or is not available
        if not success and self.config['local_fallback']:
            try:
                success, user_info = self._authenticate_local_user(username, password)
                auth_method = 'local'
                
                if success:
                    self.logger.info(f"Local authentication successful for {username}")
                else:
                    error_message = 'Invalid local credentials'
                    
            except Exception as e:
                self.logger.error(f"Local authentication error for {username}: {e}")
                error_message = f'Local auth error: {e}'
        
        # Handle failed authentication
        if not success:
            self._handle_failed_auth(username)
            self._log_auth_attempt(username, auth_method, False, ip_address, user_agent, error_message)
            return False, None, auth_method
        
        # Handle successful authentication
        self._reset_failed_attempts(username)
        self._update_last_login(username, auth_method)
        self._log_auth_attempt(username, auth_method, True, ip_address, user_agent)
        
        return True, user_info, auth_method
    
    def create_session(self, username: str, auth_method: str, ip_address: str = None, user_agent: str = None) -> str:
        """Create a new user session"""
        try:
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=self.config['session_timeout_hours'])
            
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_sessions 
                    (session_id, user_identifier, created_at, last_activity, expires_at, session_data, ip_address, user_agent)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?, ?)
                """, (session_id, username, expires_at, json.dumps({'auth_method': auth_method}), ip_address, user_agent))
            
            self.logger.info(f"Session created for {username} ({auth_method})")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Error creating session for {username}: {e}")
            return None
    
    def validate_session(self, session_id: str) -> Tuple[bool, Optional[Dict]]:
        """Validate a user session"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT user_identifier, session_data, expires_at, last_activity
                    FROM user_sessions 
                    WHERE session_id = ?
                """, (session_id,))
                
                session = cursor.fetchone()
                
                if not session:
                    return False, None
                
                # Check if session has expired
                expires_at = datetime.fromisoformat(session['expires_at'])
                if datetime.now() > expires_at:
                    self._invalidate_session(session_id)
                    return False, None
                
                # Update last activity
                cursor.execute("""
                    UPDATE user_sessions 
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (session_id,))
                
                # Parse session data and return normalized format
                session_data = json.loads(session['session_data']) if session['session_data'] else {}
                result = {
                    'username': session['user_identifier'],
                    'auth_method': session_data.get('auth_method', 'unknown'),
                    'expires_at': session['expires_at'],
                    'last_activity': session['last_activity']
                }
                
                return True, result
                
        except Exception as e:
            self.logger.error(f"Error validating session {session_id}: {e}")
            return False, None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a user session"""
        return self._invalidate_session(session_id)
    
    def _invalidate_session(self, session_id: str) -> bool:
        """Internal method to invalidate session"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE session_id = ?
                """, (session_id,))
            return True
        except Exception as e:
            self.logger.error(f"Error invalidating session {session_id}: {e}")
            return False
    
    def create_local_user(self, username: str, password: str, email: str = None, full_name: str = None, role: str = 'user') -> bool:
        """Create a new local user"""
        try:
            # Validate password strength
            if self.config['require_strong_passwords']:
                if not self._is_password_strong(password):
                    raise ValueError("Password does not meet strength requirements")
            
            # Generate salt and hash password
            salt = secrets.token_hex(32)
            password_hash = self._hash_password(password, salt)
            
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO local_users (username, password_hash, salt, email, full_name, role)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, password_hash, salt, email, full_name, role))
            
            self.logger.info(f"Local user created: {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating local user {username}: {e}")
            return False
    
    def _authenticate_local_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Authenticate against local user database"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT password_hash, salt, email, full_name, role, is_active
                    FROM local_users 
                    WHERE username = ?
                """, (username,))
                
                user = cursor.fetchone()
                
                if not user:
                    return False, None
                
                if not user['is_active']:
                    return False, None
                
                # Verify password
                password_hash = self._hash_password(password, user['salt'])
                
                if password_hash == user['password_hash']:
                    user_info = {
                        'username': username,
                        'email': user['email'],
                        'full_name': user['full_name'],
                        'role': user['role'],
                        'auth_method': 'local'
                    }
                    return True, user_info
                else:
                    return False, None
                    
        except Exception as e:
            self.logger.error(f"Error authenticating local user {username}: {e}")
            return False, None
    
    def _normalize_ldap_user_info(self, ldap_user_info: Dict) -> Dict:
        """Normalize LDAP user info to standard format"""
        return {
            'username': ldap_user_info.get('username', ''),
            'email': ldap_user_info.get('mail', ''),
            'full_name': ldap_user_info.get('displayName', ldap_user_info.get('cn', '')),
            'role': self._map_ldap_groups_to_role(ldap_user_info.get('groups', [])),
            'auth_method': 'ldap',
            'ldap_dn': ldap_user_info.get('dn', ''),
            'groups': ldap_user_info.get('groups', [])
        }
    
    def _map_ldap_groups_to_role(self, groups: List[str]) -> str:
        """Map LDAP groups to application roles"""
        # This can be configured based on organization needs
        group_role_mapping = {
            'db_admins': 'admin',
            'administrators': 'admin',
            'developers': 'developer',
            'analysts': 'analyst'
        }
        
        for group in groups:
            if group.lower() in group_role_mapping:
                return group_role_mapping[group.lower()]
        
        return 'user'  # Default role
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt"""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _is_password_strong(self, password: str) -> bool:
        """Check if password meets strength requirements"""
        if len(password) < self.config['min_password_length']:
            return False
        
        # Add more strength checks as needed
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        return has_upper and has_lower and has_digit
    
    def _is_user_locked(self, username: str) -> bool:
        """Check if user account is locked"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT locked_until FROM local_users 
                    WHERE username = ?
                """, (username,))
                
                result = cursor.fetchone()
                
                if result and result['locked_until']:
                    locked_until = datetime.fromisoformat(result['locked_until'])
                    return datetime.now() < locked_until
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking lock status for {username}: {e}")
            return False
    
    def _handle_failed_auth(self, username: str):
        """Handle failed authentication attempt"""
        try:
            with self.db.get_cursor() as cursor:
                # Increment failed attempts
                cursor.execute("""
                    UPDATE local_users 
                    SET failed_attempts = failed_attempts + 1
                    WHERE username = ?
                """, (username,))
                
                # Check if user should be locked
                cursor.execute("""
                    SELECT failed_attempts FROM local_users 
                    WHERE username = ?
                """, (username,))
                
                result = cursor.fetchone()
                
                if result and result['failed_attempts'] >= self.config['max_failed_attempts']:
                    # Lock user account
                    locked_until = datetime.now() + timedelta(minutes=self.config['lockout_duration_minutes'])
                    cursor.execute("""
                        UPDATE local_users 
                        SET locked_until = ?
                        WHERE username = ?
                    """, (locked_until, username))
                    
                    self.logger.warning(f"User {username} locked due to too many failed attempts")
                
        except Exception as e:
            self.logger.error(f"Error handling failed auth for {username}: {e}")
    
    def _reset_failed_attempts(self, username: str):
        """Reset failed authentication attempts"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE local_users 
                    SET failed_attempts = 0, locked_until = NULL
                    WHERE username = ?
                """, (username,))
        except Exception as e:
            self.logger.error(f"Error resetting failed attempts for {username}: {e}")
    
    def _update_last_login(self, username: str, auth_method: str):
        """Update last login timestamp"""
        try:
            if auth_method == 'local':
                with self.db.get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE local_users 
                        SET last_login = CURRENT_TIMESTAMP
                        WHERE username = ?
                    """, (username,))
        except Exception as e:
            self.logger.error(f"Error updating last login for {username}: {e}")
    
    def _log_auth_attempt(self, username: str, auth_method: str, success: bool, ip_address: str = None, user_agent: str = None, error_message: str = None):
        """Log authentication attempt"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO auth_attempts 
                    (username, auth_method, success, ip_address, user_agent, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, auth_method, success, ip_address, user_agent, error_message))
        except Exception as e:
            self.logger.error(f"Error logging auth attempt: {e}")
    
    def get_auth_statistics(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        try:
            stats = {}
            
            with self.db.get_cursor() as cursor:
                # Total auth attempts today
                cursor.execute("""
                    SELECT COUNT(*) as total, 
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                    FROM auth_attempts 
                    WHERE DATE(timestamp) = DATE('now')
                """)
                daily_stats = cursor.fetchone()
                stats['daily_attempts'] = dict(daily_stats) if daily_stats else {'total': 0, 'successful': 0}
                
                # Active sessions
                cursor.execute("""
                    SELECT COUNT(*) as active_sessions
                    FROM user_sessions 
                    WHERE expires_at > datetime('now')
                """)
                stats['active_sessions'] = cursor.fetchone()['active_sessions']
                
                # Local users count
                cursor.execute("SELECT COUNT(*) as local_users FROM local_users WHERE is_active = 1")
                stats['local_users'] = cursor.fetchone()['local_users']
                
                # LDAP users count
                if LDAP_INTEGRATION_AVAILABLE:
                    cursor.execute("SELECT COUNT(*) as ldap_users FROM ldap_users WHERE is_active = 1")
                    stats['ldap_users'] = cursor.fetchone()['ldap_users']
                else:
                    stats['ldap_users'] = 0
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting auth statistics: {e}")
            return {}


# Global instance
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Get authentication manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager