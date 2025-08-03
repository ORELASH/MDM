#!/usr/bin/env python3
"""
LDAP Connector
Simple LDAP integration for retrieving user information (usernames, status, groups)
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from pathlib import Path

try:
    import ldap3
    from ldap3 import Server, Connection, ALL, SUBTREE
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

class LDAPConnector:
    """Simple LDAP connector for user information retrieval"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or "/home/orel/my_installer/rsm/RedshiftManager/config/ldap_config.json"
        self.logger = logging.getLogger(__name__)
        
        # Initialize config directory
        Path(os.path.dirname(self.config_file)).mkdir(parents=True, exist_ok=True)
        
        # LDAP configuration
        self.config = self.load_config()
        self.connection = None
        
    def load_config(self) -> Dict:
        """Load LDAP configuration"""
        default_config = {
            "enabled": False,
            "server": {
                "host": "ldap://your-domain-controller.com",
                "port": 389,
                "use_ssl": False,
                "use_tls": False
            },
            "auth": {
                "bind_dn": "CN=service-account,OU=Users,DC=company,DC=com",
                "password": "",
                "auth_method": "SIMPLE"  # SIMPLE, NTLM
            },
            "search": {
                "base_dn": "OU=Users,DC=company,DC=com",
                "user_filter": "(objectClass=user)",
                "group_base_dn": "OU=Groups,DC=company,DC=com",
                "group_filter": "(objectClass=group)"
            },
            "attributes": {
                "username": "sAMAccountName",
                "display_name": "displayName", 
                "email": "mail",
                "groups": "memberOf",
                "account_disabled": "userAccountControl",
                "last_logon": "lastLogon"
            },
            "sync": {
                "auto_sync": False,
                "sync_interval_hours": 24,
                "last_sync": None
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in config[key]:
                                    config[key][subkey] = subvalue
                    return config
            else:
                # Create default config
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                return default_config
                
        except Exception as e:
            self.logger.error(f"Error loading LDAP config: {e}")
            return default_config
    
    def save_config(self):
        """Save LDAP configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving LDAP config: {e}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test LDAP connection"""
        if not LDAP_AVAILABLE:
            return False, "ldap3 library not available"
        
        if not self.config.get('enabled', False):
            return False, "LDAP not enabled in configuration"
        
        try:
            server_config = self.config.get('server', {})
            auth_config = self.config.get('auth', {})
            
            # Create server
            server = Server(
                host=server_config.get('host'),
                port=server_config.get('port', 389),
                use_ssl=server_config.get('use_ssl', False),
                get_info=ALL
            )
            
            # Create connection
            conn = Connection(
                server,
                user=auth_config.get('bind_dn'),
                password=auth_config.get('password'),
                authentication=auth_config.get('auth_method', 'SIMPLE')
            )
            
            # Test bind
            if conn.bind():
                conn.unbind()
                return True, "Connection successful"
            else:
                return False, f"Bind failed: {conn.result}"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def connect(self) -> bool:
        """Establish LDAP connection"""
        if not LDAP_AVAILABLE:
            self.logger.error("ldap3 library not available")
            return False
        
        if not self.config.get('enabled', False):
            self.logger.warning("LDAP not enabled")
            return False
        
        try:
            server_config = self.config.get('server', {})
            auth_config = self.config.get('auth', {})
            
            # Create server
            server = Server(
                host=server_config.get('host'),
                port=server_config.get('port', 389),
                use_ssl=server_config.get('use_ssl', False),
                get_info=ALL
            )
            
            # Create connection
            self.connection = Connection(
                server,
                user=auth_config.get('bind_dn'),
                password=auth_config.get('password'),
                authentication=auth_config.get('auth_method', 'SIMPLE')
            )
            
            # Bind
            if self.connection.bind():
                self.logger.info("LDAP connection established")
                return True
            else:
                self.logger.error(f"LDAP bind failed: {self.connection.result}")
                return False
                
        except Exception as e:
            self.logger.error(f"LDAP connection error: {e}")
            return False
    
    def disconnect(self):
        """Close LDAP connection"""  
        if self.connection:
            self.connection.unbind()
            self.connection = None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users from LDAP"""
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            search_config = self.config.get('search', {})
            attr_config = self.config.get('attributes', {})
            
            # Search for users
            self.connection.search(
                search_base=search_config.get('base_dn'),
                search_filter=search_config.get('user_filter', '(objectClass=user)'),
                search_scope=SUBTREE,
                attributes=[
                    attr_config.get('username', 'sAMAccountName'),
                    attr_config.get('display_name', 'displayName'),
                    attr_config.get('email', 'mail'),
                    attr_config.get('groups', 'memberOf'),
                    attr_config.get('account_disabled', 'userAccountControl'),
                    attr_config.get('last_logon', 'lastLogon')
                ]
            )
            
            users = []
            for entry in self.connection.entries:
                user_data = self._parse_user_entry(entry)
                if user_data:
                    users.append(user_data)
            
            self.logger.info(f"Retrieved {len(users)} users from LDAP")
            return users
            
        except Exception as e:
            self.logger.error(f"Error retrieving LDAP users: {e}")
            return []
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get specific user by username"""
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            search_config = self.config.get('search', {})
            attr_config = self.config.get('attributes', {})
            
            # Search for specific user
            username_attr = attr_config.get('username', 'sAMAccountName')
            search_filter = f"(&{search_config.get('user_filter', '(objectClass=user)')}({username_attr}={username}))"
            
            self.connection.search(
                search_base=search_config.get('base_dn'),
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[
                    attr_config.get('username', 'sAMAccountName'),
                    attr_config.get('display_name', 'displayName'),
                    attr_config.get('email', 'mail'),
                    attr_config.get('groups', 'memberOf'),
                    attr_config.get('account_disabled', 'userAccountControl'),
                    attr_config.get('last_logon', 'lastLogon')
                ]
            )
            
            if self.connection.entries:
                return self._parse_user_entry(self.connection.entries[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving user {username} from LDAP: {e}")
            return None
    
    def get_user_groups(self, username: str) -> List[str]:
        """Get groups for a specific user"""
        user_data = self.get_user_by_username(username)
        if user_data:
            return user_data.get('groups', [])
        return []
    
    def _parse_user_entry(self, entry) -> Optional[Dict]:
        """Parse LDAP user entry into standardized format"""
        try:
            attr_config = self.config.get('attributes', {})
            
            # Get username
            username_attr = attr_config.get('username', 'sAMAccountName')
            username = str(getattr(entry, username_attr, ''))
            
            if not username:
                return None
            
            # Get display name
            display_name_attr = attr_config.get('display_name', 'displayName')
            display_name = str(getattr(entry, display_name_attr, '')) or username
            
            # Get email
            email_attr = attr_config.get('email', 'mail')
            email = str(getattr(entry, email_attr, ''))
            
            # Get groups
            groups_attr = attr_config.get('groups', 'memberOf')
            groups_raw = getattr(entry, groups_attr, [])
            groups = []
            
            if groups_raw:
                for group_dn in groups_raw:
                    # Extract group name from DN (e.g., CN=Group Name,OU=Groups,DC=company,DC=com)
                    group_name = self._extract_cn_from_dn(str(group_dn))
                    if group_name:
                        groups.append(group_name)
            
            # Check if account is disabled
            account_control_attr = attr_config.get('account_disabled', 'userAccountControl')
            account_control = getattr(entry, account_control_attr, 0)
            
            # In AD, userAccountControl bit 1 (0x2) indicates disabled account
            is_locked = False
            if account_control:
                try:
                    control_value = int(str(account_control))
                    is_locked = bool(control_value & 0x2)
                except (ValueError, TypeError):
                    pass
            
            # Get last logon
            last_logon_attr = attr_config.get('last_logon', 'lastLogon')
            last_logon_raw = getattr(entry, last_logon_attr, None)  
            last_logon = None
            
            if last_logon_raw:
                try:
                    # Convert Windows FILETIME to datetime if needed
                    last_logon = str(last_logon_raw)
                except:
                    pass
            
            user_data = {
                'username': username,
                'display_name': display_name,
                'email': email,
                'groups': groups,
                'is_locked': is_locked,
                'is_active': not is_locked,
                'last_logon': last_logon,
                'source': 'ldap',
                'retrieved_at': datetime.now().isoformat()
            }
            
            return user_data
            
        except Exception as e:
            self.logger.error(f"Error parsing LDAP user entry: {e}")
            return None
    
    def _extract_cn_from_dn(self, dn: str) -> Optional[str]:
        """Extract CN (Common Name) from Distinguished Name"""
        try:
            # Look for CN= at the beginning of the DN
            if dn.upper().startswith('CN='):
                # Extract everything between CN= and the first comma
                end_index = dn.find(',')
                if end_index != -1:
                    return dn[3:end_index]
                else:
                    return dn[3:]  # No comma found, take everything after CN=
            return None
        except:
            return None
    
    def sync_users_to_local_storage(self) -> Tuple[int, str]:
        """Sync LDAP users to local storage with role mapping"""
        try:
            from models.local_user_storage import LocalUserStorage
            from core.group_role_mapping import get_group_role_mapper
            
            local_storage = LocalUserStorage()
            mapper = get_group_role_mapper()
            ldap_users = self.get_all_users()
            
            if not ldap_users:
                return 0, "No users retrieved from LDAP"
            
            synced_count = 0
            
            for ldap_user in ldap_users:
                try:
                    # Check if user exists in local storage
                    existing_user = local_storage.get_user(ldap_user['username'])
                    
                    # Get mapped roles for user's groups
                    user_groups = ldap_user.get('groups', [])
                    mapped_roles = {}
                    
                    # Get roles for each database type
                    for db_type in ['global', 'postgresql', 'mysql', 'redshift']:
                        roles = mapper.get_roles_for_user(user_groups, db_type)
                        if roles:
                            mapped_roles[db_type] = roles
                    
                    if existing_user:
                        # Update existing user with LDAP data
                        existing_user['display_name'] = ldap_user['display_name']
                        existing_user['email'] = ldap_user['email']
                        existing_user['is_active'] = ldap_user['is_active']
                        
                        # Update metadata
                        metadata = existing_user.get('metadata', {})
                        metadata.update({
                            'ldap_groups': ldap_user['groups'],
                            'ldap_last_sync': ldap_user['retrieved_at'],
                            'ldap_is_locked': ldap_user['is_locked'],
                            'ldap_last_logon': ldap_user['last_logon'],
                            'mapped_roles': mapped_roles
                        })
                        existing_user['metadata'] = metadata
                        
                    else:
                        # Create new user from LDAP data
                        description_parts = [f"User synced from LDAP"]
                        if user_groups:
                            description_parts.append(f"Groups: {', '.join(user_groups[:3])}")
                        if mapped_roles:
                            all_roles = []
                            for roles in mapped_roles.values():
                                all_roles.extend(roles)
                            if all_roles:
                                description_parts.append(f"Roles: {', '.join(set(all_roles)[:3])}")
                        
                        user_id = local_storage.create_user(
                            username=ldap_user['username'],
                            display_name=ldap_user['display_name'],
                            email=ldap_user['email'],
                            description=' - '.join(description_parts),
                            tags=['ldap', 'external', 'auto-mapped'],
                            metadata={
                                'source': 'ldap',
                                'ldap_groups': ldap_user['groups'],
                                'ldap_last_sync': ldap_user['retrieved_at'],
                                'ldap_is_locked': ldap_user['is_locked'],
                                'ldap_last_logon': ldap_user['last_logon'],
                                'mapped_roles': mapped_roles
                            }
                        )
                        
                        if user_id:
                            synced_count += 1
                
                except Exception as e:
                    self.logger.error(f"Error syncing user {ldap_user.get('username', 'unknown')}: {e}")
            
            # Update last sync time
            self.config['sync']['last_sync'] = datetime.now().isoformat()
            self.save_config()
            
            return synced_count, f"Successfully synced {synced_count} users from LDAP with role mapping"
            
        except Exception as e:
            self.logger.error(f"Error syncing LDAP users: {e}")
            return 0, f"Sync failed: {str(e)}"
    
    def get_sync_status(self) -> Dict:
        """Get LDAP sync status"""
        sync_config = self.config.get('sync', {})
        
        status = {
            'enabled': self.config.get('enabled', False),
            'auto_sync': sync_config.get('auto_sync', False),
            'sync_interval_hours': sync_config.get('sync_interval_hours', 24),
            'last_sync': sync_config.get('last_sync'),
            'connection_available': LDAP_AVAILABLE,
            'server_configured': bool(self.config.get('server', {}).get('host'))
        }
        
        # Test connection if enabled
        if status['enabled'] and status['connection_available']:
            connection_ok, connection_msg = self.test_connection()
            status['connection_status'] = 'connected' if connection_ok else 'failed'
            status['connection_message'] = connection_msg
        else:
            status['connection_status'] = 'disabled'
            status['connection_message'] = 'LDAP not enabled or library not available'
        
        return status

# Global LDAP connector instance
_ldap_connector = None

def get_ldap_connector() -> LDAPConnector:
    """Get the global LDAP connector instance"""
    global _ldap_connector
    if _ldap_connector is None:
        _ldap_connector = LDAPConnector()
    return _ldap_connector