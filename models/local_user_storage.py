#!/usr/bin/env python3
"""
Local User Storage Model
Manages local storage of users, permissions, and CREATE USER commands
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

class LocalUserStorage:
    """Local storage manager for users and their permissions"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = "/home/orel/my_installer/rsm/RedshiftManager/data/local_users.db"
        
        self.db_path = db_path
        self.ensure_db_directory()
        self.init_database()
    
    def ensure_db_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    def init_database(self):
        """Initialize the local user database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    normalized_username TEXT NOT NULL,
                    display_name TEXT,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_system_user BOOLEAN DEFAULT FALSE,
                    description TEXT,
                    tags TEXT,  -- JSON array of tags
                    metadata TEXT,  -- JSON metadata
                    UNIQUE(normalized_username)
                )
            ''')
            
            # Database connections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_database_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    database_name TEXT NOT NULL,
                    database_type TEXT NOT NULL,
                    connection_info TEXT,  -- JSON with host, port, etc.
                    is_active BOOLEAN DEFAULT TRUE,
                    last_sync TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # User creation commands table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_creation_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    database_name TEXT NOT NULL,
                    database_type TEXT NOT NULL,
                    create_user_sql TEXT NOT NULL,
                    original_password_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_template BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Permissions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    database_name TEXT NOT NULL,
                    permission_type TEXT NOT NULL,  -- role, table, schema, column, database
                    resource_name TEXT NOT NULL,    -- table name, schema name, etc.
                    privilege TEXT NOT NULL,       -- SELECT, INSERT, UPDATE, etc.
                    grant_option BOOLEAN DEFAULT FALSE,
                    granted_by TEXT,
                    granted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata TEXT,  -- JSON for additional info
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Permission templates table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS permission_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    database_types TEXT,  -- JSON array of supported DB types
                    permissions_json TEXT NOT NULL,  -- JSON structure of permissions
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Sync history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    database_name TEXT NOT NULL,
                    sync_type TEXT NOT NULL,  -- full_sync, incremental, export, import
                    sync_direction TEXT NOT NULL,  -- to_remote, from_remote, bidirectional
                    status TEXT NOT NULL,  -- success, error, partial
                    changes_made INTEGER DEFAULT 0,
                    error_message TEXT,
                    sync_duration_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_normalized ON users(normalized_username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_connections_user_db ON user_database_connections(user_id, database_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_permissions_user_db ON user_permissions(user_id, database_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_permissions_resource ON user_permissions(resource_name, permission_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_history_user ON sync_history(user_id, created_at)')
            
            conn.commit()
    
    @staticmethod
    def normalize_username(username: str) -> str:
        """Normalize username for consistent storage"""
        return username.lower().strip()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password for secure storage"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, display_name: str = None, email: str = None, 
                    description: str = None, tags: List[str] = None, 
                    metadata: Dict = None) -> int:
        """Create a new user in local storage"""
        normalized_username = self.normalize_username(username)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO users (username, normalized_username, display_name, email, 
                                     description, tags, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    username,
                    normalized_username,
                    display_name or username,
                    email,
                    description,
                    json.dumps(tags or []),
                    json.dumps(metadata or {})
                ))
                
                user_id = cursor.lastrowid
                
                # Log creation (optional - we can skip this for local-only users)
                try:
                    self.log_sync_event(user_id, "local_storage", "user_creation", "local", "success", 
                                      changes_made=1, sync_duration_ms=0)
                except Exception:
                    # If logging fails, continue anyway - the user creation succeeded
                    pass
                
                return user_id
                
            except sqlite3.IntegrityError:
                # User already exists
                cursor.execute('SELECT id FROM users WHERE normalized_username = ?', (normalized_username,))
                result = cursor.fetchone()
                if result:
                    return result[0]
                raise
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        normalized_username = self.normalize_username(username)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM users WHERE normalized_username = ?
            ''', (normalized_username,))
            
            row = cursor.fetchone()
            if row:
                user_dict = dict(row)
                user_dict['tags'] = json.loads(user_dict['tags'] or '[]')
                user_dict['metadata'] = json.loads(user_dict['metadata'] or '{}')
                return user_dict
            
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.*, 
                       COUNT(udc.id) as database_count,
                       COUNT(up.id) as permission_count
                FROM users u
                LEFT JOIN user_database_connections udc ON u.id = udc.user_id
                LEFT JOIN user_permissions up ON u.id = up.user_id AND up.is_active = TRUE
                GROUP BY u.id
                ORDER BY u.username
            ''')
            
            users = []
            for row in cursor.fetchall():
                user_dict = dict(row)
                user_dict['tags'] = json.loads(user_dict['tags'] or '[]')
                user_dict['metadata'] = json.loads(user_dict['metadata'] or '{}')
                users.append(user_dict)
            
            return users
    
    def save_user_creation_command(self, user_id: int, database_name: str, 
                                 database_type: str, create_sql: str, 
                                 password: str = None) -> int:
        """Save CREATE USER command for a user"""
        password_hash = self.hash_password(password) if password else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Remove existing command for this user/database combo
            cursor.execute('''
                DELETE FROM user_creation_commands 
                WHERE user_id = ? AND database_name = ?
            ''', (user_id, database_name))
            
            cursor.execute('''
                INSERT INTO user_creation_commands 
                (user_id, database_name, database_type, create_user_sql, original_password_hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, database_name, database_type, create_sql, password_hash))
            
            return cursor.lastrowid
    
    def get_user_creation_commands(self, user_id: int, database_name: str = None) -> List[Dict]:
        """Get CREATE USER commands for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if database_name:
                cursor.execute('''
                    SELECT * FROM user_creation_commands 
                    WHERE user_id = ? AND database_name = ?
                    ORDER BY created_at DESC
                ''', (user_id, database_name))
            else:
                cursor.execute('''
                    SELECT * FROM user_creation_commands 
                    WHERE user_id = ?
                    ORDER BY database_name, created_at DESC
                ''', (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def save_user_permissions(self, user_id: int, database_name: str, 
                            permissions: List[Dict]) -> int:
        """Save user permissions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Deactivate existing permissions for this user/database
            cursor.execute('''
                UPDATE user_permissions 
                SET is_active = FALSE 
                WHERE user_id = ? AND database_name = ?
            ''', (user_id, database_name))
            
            permissions_saved = 0
            
            for perm in permissions:
                cursor.execute('''
                    INSERT INTO user_permissions 
                    (user_id, database_name, permission_type, resource_name, 
                     privilege, grant_option, granted_by, granted_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    database_name,
                    perm.get('permission_type', 'unknown'),
                    perm.get('resource_name', ''),
                    perm.get('privilege', ''),
                    perm.get('grant_option', False),
                    perm.get('granted_by', ''),
                    perm.get('granted_at'),
                    json.dumps(perm.get('metadata', {}))
                ))
                permissions_saved += 1
            
            # Log sync event
            self.log_sync_event(user_id, database_name, "permissions_sync", "from_remote", 
                              "success", changes_made=permissions_saved)
            
            return permissions_saved
    
    def get_user_permissions(self, user_id: int, database_name: str = None) -> List[Dict]:
        """Get user permissions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if database_name:
                cursor.execute('''
                    SELECT * FROM user_permissions 
                    WHERE user_id = ? AND database_name = ? AND is_active = TRUE
                    ORDER BY permission_type, resource_name, privilege
                ''', (user_id, database_name))
            else:
                cursor.execute('''
                    SELECT * FROM user_permissions 
                    WHERE user_id = ? AND is_active = TRUE
                    ORDER BY database_name, permission_type, resource_name, privilege
                ''', (user_id,))
            
            permissions = []
            for row in cursor.fetchall():
                perm_dict = dict(row)
                perm_dict['metadata'] = json.loads(perm_dict['metadata'] or '{}')
                permissions.append(perm_dict)
            
            return permissions
    
    def add_database_connection(self, user_id: int, database_name: str, 
                              database_type: str, connection_info: Dict) -> int:
        """Add database connection for user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_database_connections 
                (user_id, database_name, database_type, connection_info, last_sync)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, database_name, database_type, json.dumps(connection_info)))
            
            return cursor.lastrowid
    
    def get_user_databases(self, user_id: int) -> List[Dict]:
        """Get databases associated with user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT udc.*, 
                       COUNT(up.id) as permission_count
                FROM user_database_connections udc
                LEFT JOIN user_permissions up ON udc.user_id = up.user_id 
                    AND udc.database_name = up.database_name AND up.is_active = TRUE
                WHERE udc.user_id = ?
                GROUP BY udc.id
                ORDER BY udc.database_name
            ''', (user_id,))
            
            databases = []
            for row in cursor.fetchall():
                db_dict = dict(row)
                db_dict['connection_info'] = json.loads(db_dict['connection_info'] or '{}')
                databases.append(db_dict)
            
            return databases
    
    def log_sync_event(self, user_id: int, database_name: str, sync_type: str, 
                      sync_direction: str, status: str, changes_made: int = 0, 
                      error_message: str = None, sync_duration_ms: int = 0):
        """Log synchronization event"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sync_history 
                (user_id, database_name, sync_type, sync_direction, status, 
                 changes_made, error_message, sync_duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, database_name, sync_type, sync_direction, status, 
                  changes_made, error_message, sync_duration_ms))
    
    def get_sync_history(self, user_id: int = None, database_name: str = None, 
                        limit: int = 100) -> List[Dict]:
        """Get synchronization history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT sh.*, u.username 
                FROM sync_history sh
                LEFT JOIN users u ON sh.user_id = u.id
                WHERE 1=1
            '''
            params = []
            
            if user_id:
                query += ' AND sh.user_id = ?'
                params.append(user_id)
            
            if database_name:
                query += ' AND sh.database_name = ?'
                params.append(database_name)
            
            query += ' ORDER BY sh.created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def create_permission_template(self, template_name: str, description: str, 
                                 database_types: List[str], permissions: Dict, 
                                 created_by: str = None) -> int:
        """Create a permission template"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO permission_templates 
                (template_name, description, database_types, permissions_json, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (template_name, description, json.dumps(database_types), 
                  json.dumps(permissions), created_by))
            
            return cursor.lastrowid
    
    def get_permission_templates(self, database_type: str = None) -> List[Dict]:
        """Get permission templates"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if database_type:
                cursor.execute('''
                    SELECT * FROM permission_templates 
                    WHERE is_active = TRUE 
                    AND (database_types LIKE ? OR database_types LIKE ?)
                    ORDER BY template_name
                ''', (f'%"{database_type}"%', '%"*"%'))
            else:
                cursor.execute('''
                    SELECT * FROM permission_templates 
                    WHERE is_active = TRUE 
                    ORDER BY template_name
                ''')
            
            templates = []
            for row in cursor.fetchall():
                template_dict = dict(row)
                template_dict['database_types'] = json.loads(template_dict['database_types'] or '[]')
                template_dict['permissions_json'] = json.loads(template_dict['permissions_json'] or '{}')
                templates.append(template_dict)
            
            return templates
    
    def search_users(self, query: str, limit: int = 50) -> List[Dict]:
        """Search users by username, display name, or email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            search_pattern = f'%{query.lower()}%'
            
            cursor.execute('''
                SELECT u.*, 
                       COUNT(DISTINCT udc.database_name) as database_count,
                       COUNT(up.id) as permission_count
                FROM users u
                LEFT JOIN user_database_connections udc ON u.id = udc.user_id
                LEFT JOIN user_permissions up ON u.id = up.user_id AND up.is_active = TRUE
                WHERE (LOWER(u.username) LIKE ? 
                   OR LOWER(u.display_name) LIKE ?
                   OR LOWER(u.email) LIKE ?
                   OR LOWER(u.description) LIKE ?)
                   AND u.is_active = TRUE
                GROUP BY u.id
                ORDER BY u.username
                LIMIT ?
            ''', (search_pattern, search_pattern, search_pattern, search_pattern, limit))
            
            users = []
            for row in cursor.fetchall():
                user_dict = dict(row)
                user_dict['tags'] = json.loads(user_dict['tags'] or '[]')
                user_dict['metadata'] = json.loads(user_dict['metadata'] or '{}')
                users.append(user_dict)
            
            return users
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # User statistics
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = TRUE')
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT database_name) FROM user_database_connections')
            stats['total_databases'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM user_permissions WHERE is_active = TRUE')
            stats['total_permissions'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM permission_templates WHERE is_active = TRUE')
            stats['total_templates'] = cursor.fetchone()[0]
            
            # Recent activity
            cursor.execute('''
                SELECT COUNT(*) FROM sync_history 
                WHERE created_at > datetime('now', '-24 hours')
            ''')
            stats['sync_events_24h'] = cursor.fetchone()[0]
            
            # Database types
            cursor.execute('''
                SELECT database_type, COUNT(*) as count
                FROM user_database_connections
                GROUP BY database_type
                ORDER BY count DESC
            ''')
            stats['database_types'] = dict(cursor.fetchall())
            
            return stats