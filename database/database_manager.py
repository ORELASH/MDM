"""
Database Manager for MultiDBManager
Handles all SQLite database operations and migrations from JSON
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import hashlib
import threading
from contextlib import contextmanager

class DatabaseManager:
    """
    Centralized database manager for MultiDBManager
    Handles SQLite operations, migrations, and data consistency
    """
    
    def __init__(self, db_path: str = "data/multidb_manager.db"):
        self.db_path = db_path
        self.logger = logging.getLogger("database_manager")
        self._local = threading.local()
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")
        
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def _initialize_database(self):
        """Initialize database with schema"""
        try:
            # Read and execute schema
            schema_path = Path(__file__).parent / "schema.sql"
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                
                # Split schema into individual statements to handle errors gracefully
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                conn = self._get_connection()
                cursor = conn.cursor()
                
                try:
                    for statement in statements:
                        if statement.strip():
                            try:
                                # Handle PRAGMA statements separately (they don't need transactions)
                                if statement.strip().upper().startswith('PRAGMA'):
                                    cursor.execute(statement)
                                else:
                                    cursor.execute(statement)
                            except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
                                error_msg = str(e).lower()
                                # Skip if already exists (for triggers, views, etc.)
                                if "already exists" in error_msg:
                                    continue
                                # Skip duplicate data insertion
                                elif "unique constraint failed" in error_msg:
                                    continue
                                # Skip transaction warnings for PRAGMA
                                elif "no transaction is active" in error_msg:
                                    continue
                                # Skip incomplete input warnings
                                elif "incomplete input" in error_msg:
                                    continue
                                else:
                                    self.logger.warning(f"Schema statement warning: {e}")
                    
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise
                finally:
                    cursor.close()
                
                self.logger.info("Database initialized successfully")
            else:
                self.logger.error(f"Schema file not found: {schema_path}")
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    # ================================
    # SERVER OPERATIONS
    # ================================
    
    def add_server(self, server_config: Dict[str, Any]) -> int:
        """Add a new server configuration"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO servers (name, host, port, database_name, database_type, username, password, 
                                   environment, scanner_settings, connection_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                server_config['name'],
                server_config['host'],
                server_config['port'],
                server_config.get('database_name') or server_config.get('database'),
                server_config.get('database_type', 'postgresql'),
                server_config.get('username'),
                server_config.get('password'),
                server_config.get('environment', 'Development'),
                json.dumps(server_config.get('scanner_settings', {})),
                json.dumps(server_config.get('connection_metadata') or server_config.get('metadata', {}))
            ))
            
            server_id = cursor.lastrowid
            self.logger.info(f"Added server: {server_config['name']} (ID: {server_id})")
            return server_id
    
    def get_servers(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        """Get all servers with their configuration"""
        with self.get_cursor() as cursor:
            query = "SELECT * FROM server_summary"
            if not include_inactive:
                query += " WHERE status != 'Inactive'"
            
            cursor.execute(query)
            servers = []
            
            for row in cursor.fetchall():
                server = dict(row)
                
                # Get full server config
                cursor.execute("SELECT * FROM servers WHERE id = ?", (server['id'],))
                full_config = dict(cursor.fetchone())
                
                # Parse JSON fields
                if full_config['scanner_settings']:
                    full_config['scanner_settings'] = json.loads(full_config['scanner_settings'])
                if full_config['connection_metadata']:
                    full_config['connection_metadata'] = json.loads(full_config['connection_metadata'])
                
                # Merge summary with full config
                server.update(full_config)
                servers.append(server)
            
            return servers
    
    def get_all_servers(self) -> List[Dict[str, Any]]:
        """Alias for get_servers() for backward compatibility"""
        return self.get_servers()
    
    def get_latest_scan_results(self, server_id: int) -> Dict[str, Any]:
        """Get latest scan results for a server"""
        with self.get_cursor() as cursor:
            # Get latest scan
            cursor.execute("""
                SELECT * FROM scan_history 
                WHERE server_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (server_id,))
            
            scan = cursor.fetchone()
            if not scan:
                return {"users": [], "roles": [], "tables": []}
            
            scan_dict = dict(scan)
            
            # Parse scan results if stored as JSON
            if scan_dict.get('scan_results'):
                try:
                    import json
                    results = json.loads(scan_dict['scan_results'])
                    return results
                except:
                    pass
            
            # If no JSON results, get from individual tables
            # Get users for this server
            cursor.execute("SELECT * FROM users WHERE server_id = ?", (server_id,))
            users = [dict(row) for row in cursor.fetchall()]
            
            # Get roles for this server
            cursor.execute("SELECT * FROM roles WHERE server_id = ?", (server_id,))
            roles = [dict(row) for row in cursor.fetchall()]
            
            # Get tables for this server
            cursor.execute("SELECT * FROM tables WHERE server_id = ?", (server_id,))
            tables = [dict(row) for row in cursor.fetchall()]
            
            return {
                "users": users,
                "roles": roles, 
                "tables": tables,
                "scan_id": scan_dict.get('id'),
                "scan_date": scan_dict.get('created_at')
            }
    
    def update_server(self, server_id: int, server_config: Dict[str, Any]) -> bool:
        """Update server configuration"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE servers 
                    SET name = ?, host = ?, port = ?, database_name = ?, database_type = ?, 
                        username = ?, password = ?, environment = ?, 
                        scanner_settings = ?, connection_metadata = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    server_config['name'],
                    server_config['host'],
                    server_config['port'],
                    server_config.get('database_name') or server_config.get('database'),
                    server_config.get('database_type', 'postgresql'),
                    server_config.get('username'),
                    server_config.get('password'),
                    server_config.get('environment', 'Development'),
                    json.dumps(server_config.get('scanner_settings', {})),
                    json.dumps(server_config.get('connection_metadata') or server_config.get('metadata', {})),
                    server_id
                ))
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Updated server ID {server_id}: {server_config['name']}")
                    return True
                else:
                    self.logger.warning(f"No server found with ID {server_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to update server {server_id}: {e}")
            return False

    def update_server_status(self, server_id: int, status: str, last_test_at: Optional[datetime] = None):
        """Update server connection status"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE servers 
                SET status = ?, last_test_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, last_test_at or datetime.now(), server_id))
    
    def delete_server(self, server_id: int):
        """Delete server and all related data"""
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
            self.logger.info(f"Deleted server ID: {server_id}")
    
    # ================================
    # USER OPERATIONS
    # ================================
    
    def save_users(self, server_id: int, users_data: List[Dict[str, Any]]):
        """Save discovered users for a server"""
        with self.get_cursor() as cursor:
            # Clear existing users for this server
            cursor.execute("DELETE FROM users WHERE server_id = ?", (server_id,))
            
            # Insert new users
            for user in users_data:
                normalized_username = self._normalize_username(user['name'])
                
                cursor.execute("""
                    INSERT INTO users (server_id, username, normalized_username, user_type, 
                                     is_active, last_login, metadata, permissions_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    server_id,
                    user['name'],
                    normalized_username,
                    user.get('type', 'unknown'),
                    user.get('active', True),
                    user.get('last_login'),
                    json.dumps(user.get('metadata', {})),
                    json.dumps(user.get('permissions', []))
                ))
            
            self.logger.info(f"Saved {len(users_data)} users for server ID: {server_id}")
    
    def get_global_users(self) -> Dict[str, Any]:
        """Get unified global users across all servers"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.normalized_username, u.user_type, u.is_active, 
                       u.last_login, u.created_at, u.discovered_at, u.metadata, u.permissions_data,
                       s.name as server_name, s.database_type, s.environment,
                       COUNT(DISTINCT s2.id) as appears_on_servers
                FROM users u
                JOIN servers s ON u.server_id = s.id
                LEFT JOIN users u2 ON u.normalized_username = u2.normalized_username AND u2.id != u.id
                LEFT JOIN servers s2 ON u2.server_id = s2.id
                GROUP BY u.id, u.username, u.normalized_username, u.user_type, u.is_active, 
                         u.last_login, u.created_at, u.discovered_at, u.metadata, u.permissions_data,
                         s.name, s.database_type, s.environment
                ORDER BY u.normalized_username
            """)
            
            global_users = {}
            for row in cursor.fetchall():
                user_data = dict(row)
                normalized_name = user_data['normalized_username']
                
                if normalized_name not in global_users:
                    global_users[normalized_name] = {
                        'original_name': user_data['username'],
                        'normalized_name': normalized_name,
                        'databases': {},
                        'total_permissions': 0,
                        'is_active_somewhere': user_data['is_active'],
                        'user_types': {user_data['user_type']},
                        'first_seen': user_data.get('discovered_at') or user_data.get('created_at'),
                        'last_activity': user_data['last_login'],
                        'appears_on_servers': user_data.get('appears_on_servers', 1)
                    }
                
                # Add server-specific data
                global_users[normalized_name]['databases'][user_data['server_name']] = {
                    'server_info': {
                        'Name': user_data['server_name'],
                        'database_type': user_data['database_type'],
                        'environment': user_data['environment']
                    },
                    'user_data': {
                        'name': user_data['username'],
                        'type': user_data['user_type'],
                        'active': user_data['is_active'],
                        'last_login': user_data['last_login']
                    }
                }
            
            return global_users
    
    def get_users_by_server(self, server_id: int) -> List[Dict[str, Any]]:
        """Get all users for a specific server"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT u.*, s.name as server_name
                FROM users u
                JOIN servers s ON u.server_id = s.id
                WHERE u.server_id = ?
                ORDER BY u.username
            """, (server_id,))
            
            users = []
            for row in cursor.fetchall():
                user = dict(row)
                if user['metadata']:
                    user['metadata'] = json.loads(user['metadata'])
                if user['permissions_data']:
                    user['permissions_data'] = json.loads(user['permissions_data'])
                users.append(user)
            
            return users
    
    def detect_manual_users(self, server_id: int, current_users: List[str], baseline_users: List[str]) -> List[str]:
        """Detect manually created users and log them"""
        manual_users = list(set(current_users) - set(baseline_users))
        
        if manual_users:
            with self.get_cursor() as cursor:
                for username in manual_users:
                    # Log the detection
                    cursor.execute("""
                        INSERT INTO manual_user_detections (server_id, username, risk_level)
                        VALUES (?, ?, ?)
                    """, (server_id, username, 'medium'))
                    
                    # Log security event
                    cursor.execute("""
                        INSERT INTO security_events (server_id, event_type, severity, username, description)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        server_id,
                        'manual_user_detected',
                        'medium',
                        username,
                        f'Manual user creation detected: {username}'
                    ))
            
            self.logger.warning(f"Detected {len(manual_users)} manual users on server {server_id}: {manual_users}")
        
        return manual_users
    
    # ================================
    # SCAN OPERATIONS
    # ================================
    
    def start_scan(self, server_id: int, scan_type: str) -> int:
        """Start a new scan operation"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO scan_history (server_id, scan_type, status)
                VALUES (?, ?, 'running')
            """, (server_id, scan_type))
            
            scan_id = cursor.lastrowid
            self.logger.info(f"Started {scan_type} scan for server {server_id} (Scan ID: {scan_id})")
            return scan_id
    
    def complete_scan(self, scan_id: int, results: Dict[str, Any], duration_ms: int):
        """Complete a scan operation with results"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE scan_history 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP, 
                    duration_ms = ?, results = ?, 
                    users_found = ?, roles_found = ?, tables_found = ?
                WHERE id = ?
            """, (
                duration_ms,
                json.dumps(results),
                len(results.get('users', [])),
                len(results.get('roles', [])),
                len(results.get('tables', [])),
                scan_id
            ))
    
    def fail_scan(self, scan_id: int, error_message: str):
        """Mark scan as failed"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE scan_history 
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE id = ?
            """, (error_message, scan_id))
    
    def get_scan_history(self, server_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get scan history"""
        with self.get_cursor() as cursor:
            query = """
                SELECT sh.*, s.name as server_name
                FROM scan_history sh
                JOIN servers s ON sh.server_id = s.id
            """
            params = []
            
            if server_id:
                query += " WHERE sh.server_id = ?"
                params.append(server_id)
            
            query += " ORDER BY sh.started_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            history = []
            for row in cursor.fetchall():
                scan = dict(row)
                if scan['results']:
                    scan['results'] = json.loads(scan['results'])
                history.append(scan)
            
            return history
    
    # ================================
    # SECURITY OPERATIONS
    # ================================
    
    def get_security_events(self, resolved: Optional[bool] = None, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get security events"""
        with self.get_cursor() as cursor:
            query = "SELECT * FROM security_dashboard"
            conditions = []
            params = []
            
            if resolved is not None:
                conditions.append("resolved = ?")
                params.append(resolved)
            
            if severity:
                conditions.append("severity = ?")
                params.append(severity)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def resolve_security_event(self, event_id: int):
        """Mark security event as resolved"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE security_events 
                SET resolved = TRUE, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (event_id,))
    
    # ================================
    # UTILITY METHODS
    # ================================
    
    def _normalize_username(self, username: str) -> str:
        """Normalize username for global user management"""
        return username.lower().strip()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        with self.get_cursor() as cursor:
            stats = {}
            
            # Server statistics
            cursor.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN status LIKE '🟢%' THEN 1 END) as connected FROM servers")
            server_stats = dict(cursor.fetchone())
            stats['servers'] = server_stats
            
            # User statistics
            cursor.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN is_active THEN 1 END) as active FROM users")
            user_stats = dict(cursor.fetchone())
            stats['users'] = user_stats
            
            # Global user statistics
            cursor.execute("SELECT COUNT(DISTINCT normalized_username) as unique_users FROM users")
            global_user_stats = dict(cursor.fetchone())
            stats['global_users'] = global_user_stats
            
            # Recent activity
            cursor.execute("SELECT COUNT(*) as recent_events FROM user_activity WHERE timestamp > datetime('now', '-24 hours')")
            activity_stats = dict(cursor.fetchone())
            stats['activity'] = activity_stats
            
            # Security statistics
            cursor.execute("SELECT COUNT(*) as unresolved_events FROM security_events WHERE resolved = FALSE")
            security_stats = dict(cursor.fetchone())
            stats['security'] = security_stats
            
            return stats
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create database backup"""
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"data/backups/redshift_manager_backup_{timestamp}.db"
        
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Create backup using SQLite backup API
        source = self._get_connection()
        backup_conn = sqlite3.connect(backup_path)
        
        source.backup(backup_conn)
        backup_conn.close()
        
        self.logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()


# ================================
# MIGRATION UTILITIES
# ================================

class JSONToSQLiteMigrator:
    """Migrate existing JSON data to SQLite"""
    
    def __init__(self, db_manager: DatabaseManager, json_data_dir: str = "data"):
        self.db = db_manager
        self.json_dir = json_data_dir
        self.logger = logging.getLogger("migrator")
    
    def migrate_all(self):
        """Migrate all JSON data to SQLite"""
        self.logger.info("Starting migration from JSON to SQLite")
        
        try:
            self.migrate_servers()
            self.migrate_session_data()
            self.logger.info("Migration completed successfully")
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            raise
    
    def migrate_servers(self):
        """Migrate servers.json to database"""
        servers_file = os.path.join(self.json_dir, "servers.json")
        
        if not os.path.exists(servers_file):
            self.logger.warning("servers.json not found, skipping server migration")
            return
        
        with open(servers_file, 'r') as f:
            servers = json.load(f)
        
        for server in servers:
            try:
                # Map JSON fields to database schema
                server_config = {
                    'name': server['Name'],
                    'host': server['Host'],
                    'port': server['Port'],
                    'database': server['Database'],
                    'username': server.get('Username'),
                    'password': server.get('Password'),
                    'environment': server.get('Environment', 'Development'),
                    'scanner_settings': server.get('scanner_settings', {}),
                    'metadata': {
                        'last_test': server.get('Last Test'),
                        'last_scan': server.get('last_scan')
                    }
                }
                
                # Determine database type from port
                if server['Port'] == 5432:
                    server_config['database_type'] = 'postgresql'
                elif server['Port'] == 3306:
                    server_config['database_type'] = 'mysql'
                elif server['Port'] == 6379:
                    server_config['database_type'] = 'redis'
                elif server['Port'] == 5439:
                    server_config['database_type'] = 'redshift'
                else:
                    server_config['database_type'] = 'postgresql'  # default
                
                server_id = self.db.add_server(server_config)
                
                # Update status
                status = server.get('Status', 'Unknown')
                self.db.update_server_status(server_id, status)
                
                self.logger.info(f"Migrated server: {server['Name']}")
                
            except Exception as e:
                self.logger.error(f"Failed to migrate server {server.get('Name', 'Unknown')}: {e}")
    
    def migrate_session_data(self):
        """Migrate session files to database"""
        sessions_dir = os.path.join(self.json_dir, "sessions")
        
        if not os.path.exists(sessions_dir):
            self.logger.warning("sessions directory not found, skipping session migration")
            return
        
        # Get server mapping
        servers = self.db.get_servers()
        server_map = {s['name']: s['id'] for s in servers}
        
        for server_name in os.listdir(sessions_dir):
            server_session_dir = os.path.join(sessions_dir, server_name)
            if not os.path.isdir(server_session_dir):
                continue
            
            # Find server ID
            server_id = None
            for db_name, db_id in server_map.items():
                if server_name.lower().replace('_', '-') == db_name.lower().replace('_', '-'):
                    server_id = db_id
                    break
            
            if not server_id:
                self.logger.warning(f"No matching server found for session directory: {server_name}")
                continue
            
            # Migrate latest session
            latest_session_file = os.path.join(server_session_dir, "session_latest.json")
            if os.path.exists(latest_session_file):
                try:
                    with open(latest_session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    scan_results = session_data.get('scan_results', {})
                    
                    # Save users
                    if 'users' in scan_results:
                        self.db.save_users(server_id, scan_results['users'])
                    
                    # Create scan history entry
                    scan_id = self.db.start_scan(server_id, 'full')
                    self.db.complete_scan(scan_id, scan_results, 0)  # Duration unknown
                    
                    self.logger.info(f"Migrated session data for server: {server_name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to migrate session for {server_name}: {e}")


# Global database manager instance
_db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager