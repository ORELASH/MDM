#!/usr/bin/env python3
"""
LDAP Integration for MultiDBManager
Handles LDAP authentication and user synchronization
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

try:
    from ldap3 import Server, Connection, ALL, SUBTREE
    from ldap3.core.exceptions import LDAPException, LDAPBindError
    # Check if LDAPInvalidCredentialsError exists, if not use LDAPBindError
    try:
        from ldap3.core.exceptions import LDAPInvalidCredentialsError
    except ImportError:
        LDAPInvalidCredentialsError = LDAPBindError
    LDAP_AVAILABLE = True
    print("✅ LDAP3 library imported successfully")
except ImportError as e:
    print(f"❌ LDAP Import Error: {e}")
    LDAP_AVAILABLE = False
except Exception as e:
    print(f"❌ LDAP Exception: {e}")
    LDAP_AVAILABLE = False

from database.database_manager import get_database_manager

class LDAPManager:
    """
    LDAP Manager for user authentication and synchronization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger("ldap_manager")
        self.db = get_database_manager()
        
        # Default configuration for testing with ForumSys public LDAP
        self.config = config or {
            'server': 'ldap.forumsys.com',
            'port': 389,
            'use_ssl': False,
            'base_dn': 'dc=example,dc=com',
            'bind_dn': 'cn=read-only-admin,dc=example,dc=com',
            'bind_password': 'password',
            'user_filter': '(uid={username})',
            'group_filter': '(member={user_dn})',
            'user_search_base': 'dc=example,dc=com',
            'group_search_base': 'dc=example,dc=com',
            'timeout': 10,
            'auto_sync': True,
            'sync_interval_hours': 24
        }
        
        if not LDAP_AVAILABLE:
            self.logger.error("LDAP3 library not available. Install with: pip install ldap3")
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test LDAP connection
        Returns: (success, message)
        """
        if not LDAP_AVAILABLE:
            return False, "LDAP3 library not installed"
        
        try:
            server = Server(
                self.config['server'],
                port=self.config['port'],
                use_ssl=self.config['use_ssl'],
                get_info=ALL
            )
            
            conn = Connection(
                server,
                user=self.config['bind_dn'],
                password=self.config['bind_password'],
                auto_bind=True
            )
            
            # Test search
            conn.search(
                search_base=self.config['base_dn'],
                search_filter='(objectClass=*)',
                search_scope=SUBTREE,
                size_limit=1
            )
            
            conn.unbind()
            return True, "LDAP connection successful"
            
        except LDAPBindError as e:
            return False, f"LDAP bind error: {e}"
        except LDAPException as e:
            return False, f"LDAP error: {e}"
        except Exception as e:
            return False, f"Connection error: {e}"
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user against LDAP
        Returns: (success, user_info)
        """
        if not LDAP_AVAILABLE:
            return False, None
        
        try:
            # First, find the user
            user_info = self.get_user_info(username)
            if not user_info:
                self.logger.warning(f"User {username} not found in LDAP")
                return False, None
            
            # Try to bind with user credentials
            server = Server(
                self.config['server'],
                port=self.config['port'],
                use_ssl=self.config['use_ssl']
            )
            
            conn = Connection(
                server,
                user=user_info['dn'],
                password=password,
                auto_bind=True
            )
            
            conn.unbind()
            
            # Log successful authentication
            self._log_auth_event(username, True, "LDAP authentication successful")
            
            return True, user_info
            
        except LDAPInvalidCredentialsError:
            self._log_auth_event(username, False, "Invalid credentials")
            return False, None
        except LDAPException as e:
            self._log_auth_event(username, False, f"LDAP error: {e}")
            return False, None
        except Exception as e:
            self._log_auth_event(username, False, f"Authentication error: {e}")
            return False, None
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """
        Get user information from LDAP
        """
        if not LDAP_AVAILABLE:
            return None
        
        try:
            server = Server(
                self.config['server'],
                port=self.config['port'],
                use_ssl=self.config['use_ssl']
            )
            
            conn = Connection(
                server,
                user=self.config['bind_dn'],
                password=self.config['bind_password'],
                auto_bind=True
            )
            
            # Search for user
            search_filter = self.config['user_filter'].format(username=username)
            
            conn.search(
                search_base=self.config['user_search_base'],
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['*']
            )
            
            if len(conn.entries) == 0:
                conn.unbind()
                return None
            
            entry = conn.entries[0]
            user_info = {
                'dn': str(entry.entry_dn),
                'username': username,
                'cn': str(entry.cn) if hasattr(entry, 'cn') else username,
                'mail': str(entry.mail) if hasattr(entry, 'mail') else '',
                'displayName': str(entry.displayName) if hasattr(entry, 'displayName') else '',
                'givenName': str(entry.givenName) if hasattr(entry, 'givenName') else '',
                'sn': str(entry.sn) if hasattr(entry, 'sn') else '',
                'groups': self.get_user_groups(str(entry.entry_dn))
            }
            
            conn.unbind()
            return user_info
            
        except Exception as e:
            self.logger.error(f"Error getting user info for {username}: {e}")
            return None
    
    def get_user_groups(self, user_dn: str) -> List[str]:
        """
        Get groups for a user
        """
        if not LDAP_AVAILABLE:
            return []
        
        try:
            server = Server(
                self.config['server'],
                port=self.config['port'],
                use_ssl=self.config['use_ssl']
            )
            
            conn = Connection(
                server,
                user=self.config['bind_dn'],
                password=self.config['bind_password'],
                auto_bind=True
            )
            
            # Search for groups containing this user
            search_filter = self.config['group_filter'].format(user_dn=user_dn)
            
            conn.search(
                search_base=self.config['group_search_base'],
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['cn']
            )
            
            groups = []
            for entry in conn.entries:
                if hasattr(entry, 'cn'):
                    groups.append(str(entry.cn))
            
            conn.unbind()
            return groups
            
        except Exception as e:
            self.logger.error(f"Error getting groups for user {user_dn}: {e}")
            return []
    
    def sync_users(self) -> Dict[str, Any]:
        """
        Synchronize LDAP users to local database
        """
        if not LDAP_AVAILABLE:
            return {'success': False, 'error': 'LDAP not available'}
        
        try:
            # Get all users from LDAP
            ldap_users = self.get_all_users()
            
            # Sync to database
            synced_count = 0
            errors = []
            
            for user in ldap_users:
                try:
                    self._sync_user_to_db(user)
                    synced_count += 1
                except Exception as e:
                    errors.append(f"Failed to sync user {user.get('username', 'unknown')}: {e}")
            
            # Log sync results
            self._log_sync_event(synced_count, len(errors))
            
            return {
                'success': True,
                'synced_users': synced_count,
                'total_users': len(ldap_users),
                'errors': errors
            }
            
        except Exception as e:
            self.logger.error(f"LDAP sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_all_users(self) -> List[Dict]:
        """
        Get all users from LDAP
        """
        if not LDAP_AVAILABLE:
            return []
        
        try:
            server = Server(
                self.config['server'],
                port=self.config['port'],
                use_ssl=self.config['use_ssl']
            )
            
            conn = Connection(
                server,
                user=self.config['bind_dn'],
                password=self.config['bind_password'],
                auto_bind=True
            )
            
            # Search for all users
            conn.search(
                search_base=self.config['user_search_base'],
                search_filter='(objectClass=inetOrgPerson)',
                search_scope=SUBTREE,
                attributes=['*']
            )
            
            users = []
            for entry in conn.entries:
                user_info = {
                    'dn': str(entry.entry_dn),
                    'username': str(entry.uid) if hasattr(entry, 'uid') else str(entry.cn),
                    'cn': str(entry.cn) if hasattr(entry, 'cn') else '',
                    'mail': str(entry.mail) if hasattr(entry, 'mail') else '',
                    'displayName': str(entry.displayName) if hasattr(entry, 'displayName') else '',
                    'givenName': str(entry.givenName) if hasattr(entry, 'givenName') else '',
                    'sn': str(entry.sn) if hasattr(entry, 'sn') else '',
                    'groups': self.get_user_groups(str(entry.entry_dn))
                }
                users.append(user_info)
            
            conn.unbind()
            return users
            
        except Exception as e:
            self.logger.error(f"Error getting all users: {e}")
            return []
    
    def _sync_user_to_db(self, user_info: Dict):
        """
        Sync a single user to the database
        """
        try:
            # Create or update user in local database
            with self.db.get_cursor() as cursor:
                # Check if user exists
                cursor.execute("""
                    SELECT id FROM ldap_users WHERE username = ?
                """, (user_info['username'],))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing user
                    cursor.execute("""
                        UPDATE ldap_users 
                        SET dn = ?, email = ?, display_name = ?, 
                            given_name = ?, surname = ?, groups_data = ?,
                            last_sync = CURRENT_TIMESTAMP
                        WHERE username = ?
                    """, (
                        user_info['dn'],
                        user_info['mail'],
                        user_info['displayName'],
                        user_info['givenName'],
                        user_info['sn'],
                        json.dumps(user_info['groups']),
                        user_info['username']
                    ))
                else:
                    # Insert new user
                    cursor.execute("""
                        INSERT INTO ldap_users 
                        (username, dn, email, display_name, given_name, surname, groups_data, last_sync)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        user_info['username'],
                        user_info['dn'],
                        user_info['mail'],
                        user_info['displayName'],
                        user_info['givenName'],
                        user_info['sn'],
                        json.dumps(user_info['groups'])
                    ))
                
        except Exception as e:
            self.logger.error(f"Error syncing user {user_info['username']} to database: {e}")
            raise
    
    def _log_auth_event(self, username: str, success: bool, message: str):
        """
        Log authentication event
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ldap_auth_log (username, success, message, timestamp)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (username, success, message))
        except Exception as e:
            self.logger.error(f"Error logging auth event: {e}")
    
    def _log_sync_event(self, synced_count: int, error_count: int):
        """
        Log synchronization event
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ldap_sync_log (synced_users, errors, timestamp)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (synced_count, error_count))
        except Exception as e:
            self.logger.error(f"Error logging sync event: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current LDAP configuration (without sensitive data)
        """
        safe_config = self.config.copy()
        safe_config['bind_password'] = '***'
        return safe_config
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        Update LDAP configuration
        """
        self.config.update(new_config)
        self.logger.info("LDAP configuration updated")


# Global instance
_ldap_manager = None

def get_ldap_manager(config: Optional[Dict[str, Any]] = None) -> LDAPManager:
    """
    Get LDAP manager instance
    """
    global _ldap_manager
    if _ldap_manager is None:
        _ldap_manager = LDAPManager(config)
    return _ldap_manager


# Test configurations for different LDAP servers
TEST_CONFIGS = {
    'forumsys': {
        'server': 'ldap.forumsys.com',
        'port': 389,
        'use_ssl': False,
        'base_dn': 'dc=example,dc=com',
        'bind_dn': 'cn=read-only-admin,dc=example,dc=com',
        'bind_password': 'password',
        'user_filter': '(uid={username})',
        'group_filter': '(member={user_dn})',
        'user_search_base': 'dc=example,dc=com',
        'group_search_base': 'dc=example,dc=com',
        'timeout': 10
    },
    'local_docker': {
        'server': 'localhost',
        'port': 389,
        'use_ssl': False,
        'base_dn': 'dc=multidb,dc=local',
        'bind_dn': 'cn=admin,dc=multidb,dc=local',
        'bind_password': 'admin123',
        'user_filter': '(uid={username})',
        'group_filter': '(member={user_dn})',
        'user_search_base': 'ou=people,dc=multidb,dc=local',
        'group_search_base': 'ou=groups,dc=multidb,dc=local',
        'timeout': 10
    },
    'local_system': {
        'server': 'localhost',
        'port': 389,
        'use_ssl': False,
        'base_dn': 'dc=multidb,dc=local',
        'bind_dn': 'cn=admin,dc=multidb,dc=local',
        'bind_password': 'admin123',
        'user_filter': '(uid={username})',
        'group_filter': '(member={user_dn})',
        'user_search_base': 'ou=people,dc=multidb,dc=local',
        'group_search_base': 'ou=groups,dc=multidb,dc=local',
        'timeout': 10
    }
}