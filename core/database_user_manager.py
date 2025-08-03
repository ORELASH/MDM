"""
Database-powered Global User Manager
Replaces the JSON-based GlobalUserManager with SQLite database operations
"""

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from database.database_manager import get_database_manager

class DatabaseUserManager:
    """
    Database-powered user management for RedshiftManager
    Handles user operations across multiple database servers using SQLite
    """
    
    def __init__(self):
        self.db = get_database_manager()
        self.logger = logging.getLogger("database_user_manager")
    
    def get_unified_users(self) -> Dict[str, Any]:
        """
        Get unified users across all servers
        Returns the same format as the original GlobalUserManager for compatibility
        """
        try:
            return self.db.get_global_users()
        except Exception as e:
            self.logger.error(f"Error getting unified users: {e}")
            return {}
    
    def add_server_users(self, server_name: str, users_data: List[Dict[str, Any]]) -> bool:
        """
        Add users from a server scan
        """
        try:
            # Get server ID
            servers = self.db.get_servers()
            server_id = None
            for server in servers:
                if server['name'] == server_name:
                    server_id = server['id']
                    break
            
            if not server_id:
                self.logger.error(f"Server {server_name} not found in database")
                return False
            
            # Save users to database
            self.db.save_users(server_id, users_data)
            self.logger.info(f"Added {len(users_data)} users for server {server_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding users for server {server_name}: {e}")
            return False
    
    def remove_server_users(self, server_name: str) -> bool:
        """
        Remove all users for a specific server
        """
        try:
            # Get server ID
            servers = self.db.get_servers()
            server_id = None
            for server in servers:
                if server['name'] == server_name:
                    server_id = server['id']
                    break
            
            if not server_id:
                self.logger.error(f"Server {server_name} not found in database")
                return False
            
            # Clear users for this server
            with self.db.get_cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE server_id = ?", (server_id,))
            
            self.logger.info(f"Removed all users for server {server_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing users for server {server_name}: {e}")
            return False
    
    def get_server_users(self, server_name: str) -> List[Dict[str, Any]]:
        """
        Get users for a specific server
        """
        try:
            # Get server ID
            servers = self.db.get_servers()
            server_id = None
            for server in servers:
                if server['name'] == server_name:
                    server_id = server['id']
                    break
            
            if not server_id:
                self.logger.error(f"Server {server_name} not found in database")
                return []
            
            return self.db.get_users_by_server(server_id)
            
        except Exception as e:
            self.logger.error(f"Error getting users for server {server_name}: {e}")
            return []
    
    def normalize_username(self, username: str) -> str:
        """
        Normalize username for global user management
        """
        return self.db._normalize_username(username)
    
    def disable_user(self, server_name: str, username: str, reason: str = "Manual disable") -> bool:
        """
        Disable user across all occurrences
        """
        try:
            unified_users = self.get_unified_users()
            normalized_username = self.normalize_username(username)
            
            if normalized_username not in unified_users:
                self.logger.warning(f"User {username} not found in global users")
                return False
            
            user_data = unified_users[normalized_username]
            
            # Disable user on all servers where they exist
            success_count = 0
            for db_name, db_info in user_data['databases'].items():
                try:
                    # Get server info
                    server_info = db_info['server_info']
                    
                    # Execute disable command on the actual database
                    disable_result = self._disable_user_in_database(server_info, username)
                    
                    if disable_result:
                        # Update our database record
                        with self.db.get_cursor() as cursor:
                            cursor.execute("""
                                UPDATE users 
                                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                                WHERE server_id = (SELECT id FROM servers WHERE name = ?) 
                                AND username = ?
                            """, (db_name, username))
                        
                        # Log the action
                        with self.db.get_cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO user_activity (server_id, username, action, details)
                                VALUES (
                                    (SELECT id FROM servers WHERE name = ?),
                                    ?, 'disabled', 
                                    json_object('reason', ?, 'timestamp', datetime('now'))
                                )
                            """, (db_name, username, reason))
                        
                        success_count += 1
                        self.logger.info(f"Disabled user {username} on server {db_name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to disable user {username} on server {db_name}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Error disabling user {username}: {e}")
            return False
    
    def _disable_user_in_database(self, server_info: Dict[str, Any], username: str) -> bool:
        """
        Disable user in the actual database
        """
        try:
            # Import database execution function
            from ui.open_dashboard import execute_sql_command
            
            db_type = server_info.get('database_type', 'postgresql')
            
            if db_type in ["postgresql", "redshift"]:
                sql = f'ALTER ROLE "{username}" WITH NOLOGIN;'
            elif db_type == "mysql":
                sql = f"ALTER USER '{username}'@'%' ACCOUNT LOCK;"
            else:
                self.logger.warning(f"User disable not supported for database type: {db_type}")
                return False
            
            result, output = execute_sql_command(server_info, sql, fetch_results=False)
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing disable command for user {username}: {e}")
            return False
    
    def enable_user(self, server_name: str, username: str, reason: str = "Manual enable") -> bool:
        """
        Enable user across all occurrences
        """
        try:
            unified_users = self.get_unified_users()
            normalized_username = self.normalize_username(username)
            
            if normalized_username not in unified_users:
                self.logger.warning(f"User {username} not found in global users")
                return False
            
            user_data = unified_users[normalized_username]
            
            # Enable user on all servers where they exist
            success_count = 0
            for db_name, db_info in user_data['databases'].items():
                try:
                    # Get server info
                    server_info = db_info['server_info']
                    
                    # Execute enable command on the actual database
                    enable_result = self._enable_user_in_database(server_info, username)
                    
                    if enable_result:
                        # Update our database record
                        with self.db.get_cursor() as cursor:
                            cursor.execute("""
                                UPDATE users 
                                SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                                WHERE server_id = (SELECT id FROM servers WHERE name = ?) 
                                AND username = ?
                            """, (db_name, username))
                        
                        # Log the action
                        with self.db.get_cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO user_activity (server_id, username, action, details)
                                VALUES (
                                    (SELECT id FROM servers WHERE name = ?),
                                    ?, 'enabled', 
                                    json_object('reason', ?, 'timestamp', datetime('now'))
                                )
                            """, (db_name, username, reason))
                        
                        success_count += 1
                        self.logger.info(f"Enabled user {username} on server {db_name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to enable user {username} on server {db_name}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Error enabling user {username}: {e}")
            return False
    
    def _enable_user_in_database(self, server_info: Dict[str, Any], username: str) -> bool:
        """
        Enable user in the actual database
        """
        try:
            # Import database execution function
            from ui.open_dashboard import execute_sql_command
            
            db_type = server_info.get('database_type', 'postgresql')
            
            if db_type in ["postgresql", "redshift"]:
                sql = f'ALTER ROLE "{username}" WITH LOGIN;'
            elif db_type == "mysql":
                sql = f"ALTER USER '{username}'@'%' ACCOUNT UNLOCK;"
            else:
                self.logger.warning(f"User enable not supported for database type: {db_type}")
                return False
            
            result, output = execute_sql_command(server_info, sql, fetch_results=False)
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing enable command for user {username}: {e}")
            return False
    
    def get_user_activity_history(self, username: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get user activity history
        """
        try:
            with self.db.get_cursor() as cursor:
                if username:
                    cursor.execute("""
                        SELECT * FROM recent_activity 
                        WHERE username = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (username, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM recent_activity 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting user activity history: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get user management statistics
        """
        try:
            return self.db.get_statistics()
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {
                'servers': {'total': 0, 'connected': 0},
                'users': {'total': 0, 'active': 0},
                'global_users': {'unique_users': 0},
                'activity': {'recent_events': 0},
                'security': {'unresolved_events': 0}
            }
    
    def detect_manual_users(self, server_name: str, current_users: List[str], baseline_users: List[str]) -> List[str]:
        """
        Detect manually created users and log security events
        """
        try:
            # Get server ID
            servers = self.db.get_servers()
            server_id = None
            for server in servers:
                if server['name'] == server_name:
                    server_id = server['id']
                    break
            
            if not server_id:
                self.logger.error(f"Server {server_name} not found in database")
                return []
            
            return self.db.detect_manual_users(server_id, current_users, baseline_users)
            
        except Exception as e:
            self.logger.error(f"Error detecting manual users for server {server_name}: {e}")
            return []
    
    def get_security_events(self, resolved: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Get security events
        """
        try:
            return self.db.get_security_events(resolved=resolved)
        except Exception as e:
            self.logger.error(f"Error getting security events: {e}")
            return []
    
    def resolve_security_event(self, event_id: int) -> bool:
        """
        Mark security event as resolved
        """
        try:
            self.db.resolve_security_event(event_id)
            return True
        except Exception as e:
            self.logger.error(f"Error resolving security event {event_id}: {e}")
            return False


# Compatibility function for existing code
def get_global_user_manager() -> DatabaseUserManager:
    """
    Get global user manager instance
    Replaces the old GlobalUserManager for backward compatibility
    """
    return DatabaseUserManager()