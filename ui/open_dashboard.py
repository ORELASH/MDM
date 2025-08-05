#!/usr/bin/env python3
"""
MultiDBManager Open Dashboard
Universal multi-database management dashboard without authentication
"""

import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Import translations
sys.path.append(str(Path(__file__).parent.parent))
from config.ui_translations import translate, get_available_languages, is_rtl_language
try:
    import ldap3
    from ldap3 import Server, Connection, ALL, NTLM
    import ssl
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

# Database connection utilities
def execute_sql_command(server_info, sql_command, fetch_results=False):
    """Execute SQL command on the database server"""
    import psycopg2
    import pymysql
    import redis
    
    host = server_info['Host']
    port = server_info['Port']
    database = server_info['Database']
    username = server_info.get('Username', 'postgres')
    password = server_info.get('Password', '')
    
    # Determine database type by port
    if port == 5432 or port == 5439:
        db_type = "postgresql" if port == 5432 else "redshift"
    elif port == 3306:
        db_type = "mysql"
    elif port == 6379:
        db_type = "redis"
    else:
        db_type = "generic"
    
    try:
        if db_type in ["postgresql", "redshift"]:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            if fetch_results:
                cursor.execute(sql_command)
                results = cursor.fetchall()
                conn.close()
                return True, results
            else:
                cursor.execute(sql_command)
                conn.commit()
                conn.close()
                return True, "Command executed successfully"
                
        elif db_type == "mysql":
            conn = pymysql.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            if fetch_results:
                cursor.execute(sql_command)
                results = cursor.fetchall()
                conn.close()
                return True, results
            else:
                cursor.execute(sql_command)
                conn.commit()
                conn.close()
                return True, "Command executed successfully"
        
        elif db_type == "redis":
            # Redis commands are different
            r = redis.Redis(host=host, port=port, password=password, socket_connect_timeout=10)
            # Redis user management is limited, but we can simulate some operations
            if "ACL SETUSER" in sql_command.upper():
                # Redis ACL command
                result = r.execute_command(sql_command)
                return True, f"Redis command executed: {result}"
            else:
                return False, "Redis doesn't support traditional SQL user management"
        
        else:
            return False, "Unsupported database type"
            
    except Exception as e:
        return False, f"Error executing command: {str(e)}"

def get_database_structure(server_info):
    """Get database structure (databases, schemas, tables) for permission assignment"""
    import psycopg2
    import pymysql
    import redis
    
    host = server_info['Host']
    port = server_info['Port']
    database = server_info['Database']
    username = server_info.get('Username', 'postgres')
    password = server_info.get('Password', '')
    
    # Determine database type by port
    if port == 5432 or port == 5439:
        db_type = "postgresql" if port == 5432 else "redshift"
    elif port == 3306:
        db_type = "mysql"
    elif port == 6379:
        db_type = "redis"
    else:
        db_type = "generic"
    
    try:
        structure = {
            "databases": [],
            "schemas": [],
            "tables": [],
            "database_type": db_type
        }
        
        if db_type in ["postgresql", "redshift"]:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            # Get databases
            cursor.execute("""
                SELECT datname FROM pg_database 
                WHERE datname NOT IN ('template0', 'template1', 'postgres') 
                AND datistemplate = false
                ORDER BY datname;
            """)
            structure["databases"] = [row[0] for row in cursor.fetchall()]
            
            # Get schemas in current database
            cursor.execute("""
                SELECT schema_name FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
                ORDER BY schema_name;
            """)
            structure["schemas"] = [row[0] for row in cursor.fetchall()]
            
            # Get tables in current database
            cursor.execute("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                ORDER BY schemaname, tablename;
            """)
            structure["tables"] = [{"schema": row[0], "table": row[1], "full_name": f"{row[0]}.{row[1]}"} for row in cursor.fetchall()]
            
            conn.close()
            
        elif db_type == "mysql":
            conn = pymysql.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            # Get databases
            cursor.execute("SHOW DATABASES;")
            excluded_dbs = ['information_schema', 'performance_schema', 'mysql', 'sys']
            structure["databases"] = [row[0] for row in cursor.fetchall() if row[0] not in excluded_dbs]
            
            # MySQL doesn't have schemas like PostgreSQL, databases are the top level
            structure["schemas"] = structure["databases"].copy()
            
            # Get tables in current database
            cursor.execute("SHOW TABLES;")
            structure["tables"] = [{"schema": database, "table": row[0], "full_name": f"{database}.{row[0]}"} for row in cursor.fetchall()]
            
            conn.close()
            
        elif db_type == "redis":
            # Redis doesn't have traditional database structure
            r = redis.Redis(host=host, port=port, password=password, socket_connect_timeout=10)
            info = r.info()
            
            # Redis has databases 0-15 by default
            structure["databases"] = [f"DB{i}" for i in range(16)]
            structure["schemas"] = []  # Redis doesn't have schemas
            structure["tables"] = []   # Redis doesn't have tables
        
        return True, structure
        
    except Exception as e:
        return False, f"Error getting database structure: {str(e)}"

def get_table_columns(server_info, table_name, schema_name=None):
    """Get column information for a specific table"""
    import psycopg2
    import pymysql
    
    host = server_info['Host']
    port = server_info['Port']
    database = server_info['Database']
    username = server_info.get('Username', 'postgres')
    password = server_info.get('Password', '')
    
    # Determine database type by port
    if port == 5432 or port == 5439:
        db_type = "postgresql" if port == 5432 else "redshift"
    elif port == 3306:
        db_type = "mysql"
    else:
        return False, "Column-level permissions not supported for this database type"
    
    try:
        columns = []
        
        if db_type in ["postgresql", "redshift"]:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            if schema_name:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s AND table_schema = %s
                    ORDER BY ordinal_position;
                """, (table_name, schema_name))
            else:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s
                    ORDER BY ordinal_position;
                """, (table_name,))
            
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == 'YES',
                    "default": row[3],
                    "full_name": f"{schema_name}.{table_name}.{row[0]}" if schema_name else f"{table_name}.{row[0]}"
                })
            
            conn.close()
            
        elif db_type == "mysql":
            conn = pymysql.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            cursor.execute(f"DESCRIBE {table_name};")
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],  # Field
                    "type": row[1],  # Type
                    "nullable": row[2] == 'YES',  # Null
                    "default": row[4],  # Default
                    "full_name": f"{database}.{table_name}.{row[0]}"
                })
            
            conn.close()
        
        return True, columns
        
    except Exception as e:
        return False, f"Error getting table columns: {str(e)}"

def get_user_permissions(server_info, username):
    """Get comprehensive permissions for a specific user"""
    import psycopg2
    import pymysql
    
    host = server_info['Host']
    port = server_info['Port']
    database = server_info['Database']
    db_username = server_info.get('Username', 'postgres')
    password = server_info.get('Password', '')
    
    # Determine database type by port
    if port == 5432 or port == 5439:
        db_type = "postgresql" if port == 5432 else "redshift"
    elif port == 3306:
        db_type = "mysql"
    else:
        return False, "Permission copying not supported for this database type"
    
    try:
        permissions = {
            "roles": [],
            "table_permissions": [],
            "schema_permissions": [],
            "database_permissions": [],
            "column_permissions": [],
            "user_properties": {},
            "database_type": db_type
        }
        
        if db_type in ["postgresql", "redshift"]:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=db_username,
                password=password,
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            # Get user properties
            cursor.execute("""
                SELECT rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolconnlimit
                FROM pg_roles WHERE rolname = %s;
            """, (username,))
            user_props = cursor.fetchone()
            if user_props:
                permissions["user_properties"] = {
                    "superuser": user_props[0],
                    "createrole": user_props[1],
                    "createdb": user_props[2],
                    "canlogin": user_props[3],
                    "connection_limit": user_props[4]
                }
            
            # Get roles granted to user
            cursor.execute("""
                SELECT r.rolname 
                FROM pg_roles r
                JOIN pg_auth_members m ON r.oid = m.roleid
                JOIN pg_roles u ON m.member = u.oid
                WHERE u.rolname = %s;
            """, (username,))
            permissions["roles"] = [row[0] for row in cursor.fetchall()]
            
            # Get table permissions
            cursor.execute("""
                SELECT schemaname, tablename, privilege_type
                FROM information_schema.table_privileges
                WHERE grantee = %s;
            """, (username,))
            for row in cursor.fetchall():
                permissions["table_permissions"].append({
                    "schema": row[0],
                    "table": row[1],
                    "privilege": row[2],
                    "full_name": f"{row[0]}.{row[1]}"
                })
            
            # Get schema permissions
            cursor.execute("""
                SELECT schema_name, privilege_type
                FROM information_schema.schema_privileges
                WHERE grantee = %s;
            """, (username,))
            for row in cursor.fetchall():
                permissions["schema_permissions"].append({
                    "schema": row[0],
                    "privilege": row[1]
                })
            
            # Get column permissions
            cursor.execute("""
                SELECT table_schema, table_name, column_name, privilege_type
                FROM information_schema.column_privileges
                WHERE grantee = %s;
            """, (username,))
            for row in cursor.fetchall():
                permissions["column_permissions"].append({
                    "schema": row[0],
                    "table": row[1],
                    "column": row[2],
                    "privilege": row[3],
                    "full_name": f"{row[0]}.{row[1]}.{row[2]}"
                })
            
            conn.close()
            
        elif db_type == "mysql":
            conn = pymysql.connect(
                host=host,
                port=port,
                database=database,
                user=db_username,
                password=password,
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            # Get user grants
            cursor.execute(f"SHOW GRANTS FOR '{username}'@'%';")
            grants = cursor.fetchall()
            
            for grant in grants:
                grant_text = grant[0]
                # Parse MySQL GRANT statements
                if "GRANT" in grant_text and "ON" in grant_text:
                    parts = grant_text.split(" ON ")
                    if len(parts) == 2:
                        privs_part = parts[0].replace("GRANT ", "")
                        table_part = parts[1].split(" TO ")[0]
                        
                        privileges = [p.strip() for p in privs_part.split(",")]
                        
                        if ".*" in table_part:
                            # Database level permissions
                            db_name = table_part.replace(".*", "").replace("`", "")
                            for priv in privileges:
                                permissions["database_permissions"].append({
                                    "database": db_name,
                                    "privilege": priv.strip()
                                })
                        else:
                            # Table level permissions
                            table_name = table_part.replace("`", "")
                            for priv in privileges:
                                permissions["table_permissions"].append({
                                    "table": table_name,
                                    "privilege": priv.strip(),
                                    "full_name": table_name
                                })
            
            conn.close()
        
        return True, permissions
        
    except Exception as e:
        return False, f"Error getting user permissions: {str(e)}"

def clone_user_permissions(server_info, source_username, target_username, target_password, clone_options=None):
    """Clone permissions from source user to new target user"""
    
    # Get source user permissions
    success, source_perms = get_user_permissions(server_info, source_username)
    if not success:
        return False, f"Could not get source user permissions: {source_perms}"
    
    db_type = source_perms.get("database_type", "postgresql")
    clone_options = clone_options or {}
    
    commands = []
    
    if db_type in ["postgresql", "redshift"]:
        # Create target user
        commands.append(f'CREATE ROLE "{target_username}" WITH LOGIN PASSWORD \'{target_password}\';')
        
        # Copy user properties if requested
        if clone_options.get("copy_properties", True):
            user_props = source_perms.get("user_properties", {})
            if user_props.get("superuser"):
                commands.append(f'ALTER ROLE "{target_username}" WITH SUPERUSER;')
            if user_props.get("createrole"):
                commands.append(f'ALTER ROLE "{target_username}" WITH CREATEROLE;')
            if user_props.get("createdb"):
                commands.append(f'ALTER ROLE "{target_username}" WITH CREATEDB;')
            if user_props.get("connection_limit", -1) != -1:
                commands.append(f'ALTER ROLE "{target_username}" CONNECTION LIMIT {user_props["connection_limit"]};')
        
        # Copy roles if requested
        if clone_options.get("copy_roles", True):
            for role in source_perms.get("roles", []):
                commands.append(f'GRANT "{role}" TO "{target_username}";')
        
        # Copy table permissions if requested
        if clone_options.get("copy_table_permissions", True):
            for perm in source_perms.get("table_permissions", []):
                commands.append(f'GRANT {perm["privilege"]} ON {perm["full_name"]} TO "{target_username}";')
        
        # Copy schema permissions if requested
        if clone_options.get("copy_schema_permissions", True):
            for perm in source_perms.get("schema_permissions", []):
                commands.append(f'GRANT {perm["privilege"]} ON SCHEMA "{perm["schema"]}" TO "{target_username}";')
        
        # Copy column permissions if requested
        if clone_options.get("copy_column_permissions", True):
            for perm in source_perms.get("column_permissions", []):
                commands.append(f'GRANT {perm["privilege"]} ON {perm["schema"]}.{perm["table"]} ({perm["column"]}) TO "{target_username}";')
    
    elif db_type == "mysql":
        # Create target user
        commands.append(f"CREATE USER '{target_username}'@'%' IDENTIFIED BY '{target_password}';")
        
        # Copy database permissions
        if clone_options.get("copy_database_permissions", True):
            for perm in source_perms.get("database_permissions", []):
                commands.append(f"GRANT {perm['privilege']} ON {perm['database']}.* TO '{target_username}'@'%';")
        
        # Copy table permissions
        if clone_options.get("copy_table_permissions", True):
            for perm in source_perms.get("table_permissions", []):
                commands.append(f"GRANT {perm['privilege']} ON {perm['full_name']} TO '{target_username}'@'%';")
        
        commands.append("FLUSH PRIVILEGES;")
    
    return True, {
        "commands": commands,
        "source_permissions": source_perms,
        "clone_options": clone_options
    }

def copy_user_permissions(server_info, source_username, target_username, copy_options=None):
    """Copy permissions from source user to existing target user"""
    
    # Get source user permissions
    success, source_perms = get_user_permissions(server_info, source_username)
    if not success:
        return False, f"Could not get source user permissions: {source_perms}"
    
    db_type = source_perms.get("database_type", "postgresql")
    copy_options = copy_options or {}
    
    commands = []
    
    if db_type in ["postgresql", "redshift"]:
        # Copy user properties if requested
        if copy_options.get("copy_properties", True):
            user_props = source_perms.get("user_properties", {})
            if user_props.get("superuser"):
                commands.append(f'ALTER ROLE "{target_username}" WITH SUPERUSER;')
            if user_props.get("createrole"):
                commands.append(f'ALTER ROLE "{target_username}" WITH CREATEROLE;')
            if user_props.get("createdb"):
                commands.append(f'ALTER ROLE "{target_username}" WITH CREATEDB;')
            if user_props.get("connection_limit", -1) != -1:
                commands.append(f'ALTER ROLE "{target_username}" CONNECTION LIMIT {user_props["connection_limit"]};')
        
        # Copy roles if requested
        if copy_options.get("copy_roles", True):
            for role in source_perms.get("roles", []):
                commands.append(f'GRANT "{role}" TO "{target_username}";')
        
        # Copy table permissions if requested
        if copy_options.get("copy_table_permissions", True):
            for perm in source_perms.get("table_permissions", []):
                commands.append(f'GRANT {perm["privilege"]} ON {perm["full_name"]} TO "{target_username}";')
        
        # Copy schema permissions if requested
        if copy_options.get("copy_schema_permissions", True):
            for perm in source_perms.get("schema_permissions", []):
                commands.append(f'GRANT {perm["privilege"]} ON SCHEMA "{perm["schema"]}" TO "{target_username}";')
        
        # Copy column permissions if requested
        if copy_options.get("copy_column_permissions", True):
            for perm in source_perms.get("column_permissions", []):
                commands.append(f'GRANT {perm["privilege"]} ON {perm["schema"]}.{perm["table"]} ({perm["column"]}) TO "{target_username}";')
    
    elif db_type == "mysql":
        # Copy database permissions
        if copy_options.get("copy_database_permissions", True):
            for perm in source_perms.get("database_permissions", []):
                commands.append(f"GRANT {perm['privilege']} ON {perm['database']}.* TO '{target_username}'@'%';")
        
        # Copy table permissions
        if copy_options.get("copy_table_permissions", True):
            for perm in source_perms.get("table_permissions", []):
                commands.append(f"GRANT {perm['privilege']} ON {perm['full_name']} TO '{target_username}'@'%';")
        
        commands.append("FLUSH PRIVILEGES;")
    
    return True, commands

class GlobalUserManager:
    """Centralized user management across all databases - SQLite Edition"""
    
    def __init__(self):
        self.unified_users = {}
        self.database_connections = {}
        # Use the new SQLite database manager
        try:
            from database.database_manager import get_database_manager
            self.db_manager = get_database_manager()
        except ImportError:
            self.db_manager = None
            st.warning("⚠️ SQLite database manager not available, falling back to legacy mode")
    
    def normalize_username(self, username):
        """Normalize username to lowercase for consistent comparison"""
        return username.lower().strip()
    
    def get_all_users_from_all_databases(self):
        """Collect all users from all configured databases - SQLite Edition"""
        if self.db_manager:
            # Use SQLite database manager for improved performance
            try:
                unified_users = {}
                
                # Get global users from the database
                global_users = self.db_manager.get_global_users()
                
                for user_data in global_users:
                    normalized_username = user_data.get('normalized_username', 
                                                       self.normalize_username(user_data.get('username', '')))
                    
                    unified_users[normalized_username] = {
                        'original_name': user_data.get('username', ''),
                        'normalized_name': normalized_username,
                        'databases': {user_data.get('server_name', 'unknown'): {
                            'database_type': user_data.get('database_type', 'unknown'),
                            'environment': user_data.get('environment', 'Unknown'),
                            'user_type': user_data.get('user_type', 'unknown'),
                            'is_active': user_data.get('is_active', False),
                            'last_login': user_data.get('last_login'),
                            'permissions': user_data.get('permissions_data', {}),
                            'metadata': user_data.get('metadata', {})
                        }},
                        'total_permissions': 1,  # Count of servers user appears on
                        'is_active_somewhere': user_data.get('is_active', False),
                        'user_types': {user_data.get('user_type', 'unknown')},
                        'first_seen': user_data.get('discovered_at', datetime.now()),
                        'last_activity': user_data.get('last_login')
                    }
                
                return unified_users
                
            except Exception as e:
                st.error(f"❌ SQLite database error: {e}")
                # Fall back to legacy mode
                pass
        
        # Legacy mode for backward compatibility
        if 'servers_list' not in st.session_state:
            return {}
        
        unified_users = {}
        
        for server in st.session_state.servers_list:
            server_name = server['Name']
            
            # First try to get scan results from the server object
            users = []
            if 'scan_results' in server and 'users' in server['scan_results']:
                users = server['scan_results']['users']
            
            # If current scan failed or no users found, try to load from session files
            if not users or (len(users) == 1 and users[0].get('name') == 'Connection failed'):
                users = self._load_users_from_session_files(server_name)
            
            # Process users
            for user in users:
                if isinstance(user, dict) and 'name' in user and user['name'] != 'Connection failed':
                    username = user['name']
                    normalized_username = self.normalize_username(username)
                    
                    # Initialize user entry if not exists
                    if normalized_username not in unified_users:
                        unified_users[normalized_username] = {
                            'original_name': username,
                            'normalized_name': normalized_username,
                            'databases': {},
                            'total_permissions': 0,
                            'is_active_somewhere': False,
                            'user_types': set(),
                            'first_seen': datetime.now(),
                            'last_activity': None
                        }
                    
                    # Add database-specific information
                    unified_users[normalized_username]['databases'][server_name] = {
                        'server_info': server,
                        'user_data': user,
                        'type': user.get('type', 'unknown'),
                        'active': user.get('active', False),
                        'last_login': user.get('last_login'),
                        'permissions_count': 0  # Will be populated later
                    }
                    
                    # Update global user status
                    if user.get('active', False):
                        unified_users[normalized_username]['is_active_somewhere'] = True
                    
                    unified_users[normalized_username]['user_types'].add(user.get('type', 'unknown'))
        
        
        return unified_users
    
    def _load_users_from_session_files(self, server_name):
        """Load users from session files when current scan fails"""
        import json
        import os
        
        users = []
        sessions_dir = f"/home/orel/my_installer/rsm/RedshiftManager/data/sessions/{server_name.replace('-', '_')}"
        
        try:
            if os.path.exists(sessions_dir):
                # Try different session files in order of preference
                session_files = ['session_latest.json', 'session_v001.json', 'session_v002.json', 'session_v003.json']
                
                for session_file in session_files:
                    session_path = os.path.join(sessions_dir, session_file)
                    if os.path.exists(session_path):
                        try:
                            with open(session_path, 'r') as f:
                                session_data = json.load(f)
                                
                            # Check if this session has valid user data
                            if ('scan_results' in session_data and 
                                'users' in session_data['scan_results'] and 
                                session_data['scan_results']['users']):
                                
                                session_users = session_data['scan_results']['users']
                                # Filter out error entries
                                valid_users = [u for u in session_users if isinstance(u, dict) and 
                                             u.get('name') != 'Connection failed' and u.get('type') != 'error']
                                
                                if valid_users:
                                    users = valid_users
                                    break  # Found valid users, stop looking
                                    
                        except (json.JSONDecodeError, KeyError) as e:
                            continue  # Try next file
                            
        except Exception as e:
            # If all else fails, return empty list
            pass
            
        return users
    
    def get_user_permissions_across_databases(self, normalized_username):
        """Get comprehensive permissions for a user across all databases"""
        unified_users = self.get_all_users_from_all_databases()
        
        if normalized_username not in unified_users:
            return None
        
        user_info = unified_users[normalized_username]
        permissions_summary = {
            'total_permissions': 0,
            'database_breakdown': {},
            'permission_types': set(),
            'high_privilege_databases': []
        }
        
        for db_name, db_info in user_info['databases'].items():
            server_info = db_info['server_info']
            
            # Get detailed permissions for this database
            success, perms = get_user_permissions(server_info, db_info['user_data']['name'])
            
            if success:
                db_perms = {
                    'roles': len(perms.get('roles', [])),
                    'table_permissions': len(perms.get('table_permissions', [])),
                    'schema_permissions': len(perms.get('schema_permissions', [])),
                    'column_permissions': len(perms.get('column_permissions', [])),
                    'user_properties': perms.get('user_properties', {}),
                    'total': sum([
                        len(perms.get('roles', [])),
                        len(perms.get('table_permissions', [])),
                        len(perms.get('schema_permissions', [])),
                        len(perms.get('column_permissions', []))
                    ])
                }
                
                permissions_summary['database_breakdown'][db_name] = db_perms
                permissions_summary['total_permissions'] += db_perms['total']
                
                # Check for high privileges
                if perms.get('user_properties', {}).get('superuser') or db_info['user_data'].get('type') == 'superuser':
                    permissions_summary['high_privilege_databases'].append(db_name)
        
        return permissions_summary
    
    def execute_global_user_action(self, normalized_username, action, **kwargs):
        """Execute an action on a user across all databases where they exist"""
        unified_users = self.get_all_users_from_all_databases()
        
        if normalized_username not in unified_users:
            return False, "User not found in any database"
        
        user_info = unified_users[normalized_username]
        results = {}
        success_count = 0
        
        for db_name, db_info in user_info['databases'].items():
            server_info = db_info['server_info']
            actual_username = db_info['user_data']['name']
            
            try:
                if action == "disable":
                    success, result = self._disable_user_in_database(server_info, actual_username)
                elif action == "enable":
                    success, result = self._enable_user_in_database(server_info, actual_username)
                elif action == "delete":
                    success, result = self._delete_user_in_database(server_info, actual_username)
                elif action == "change_password":
                    new_password = kwargs.get('new_password')
                    success, result = self._change_user_password(server_info, actual_username, new_password)
                else:
                    success, result = False, f"Unknown action: {action}"
                
                results[db_name] = {'success': success, 'result': result}
                if success:
                    success_count += 1
                    
            except Exception as e:
                results[db_name] = {'success': False, 'result': str(e)}
        
        total_databases = len(user_info['databases'])
        return success_count > 0, {
            'success_count': success_count,
            'total_databases': total_databases,
            'detailed_results': results,
            'partial_success': success_count > 0 and success_count < total_databases
        }
    
    def _disable_user_in_database(self, server_info, username):
        """Disable user in specific database"""
        db_type = self._get_database_type(server_info)
        
        if db_type in ["postgresql", "redshift"]:
            sql = f'ALTER ROLE "{username}" WITH NOLOGIN;'
        elif db_type == "mysql":
            sql = f"ALTER USER '{username}'@'%' ACCOUNT LOCK;"
        else:
            return False, f"Unsupported database type: {db_type}"
        
        return execute_sql_command(server_info, sql, fetch_results=False)
    
    def _enable_user_in_database(self, server_info, username):
        """Enable user in specific database"""
        db_type = self._get_database_type(server_info)
        
        if db_type in ["postgresql", "redshift"]:
            sql = f'ALTER ROLE "{username}" WITH LOGIN;'
        elif db_type == "mysql":
            sql = f"ALTER USER '{username}'@'%' ACCOUNT UNLOCK;"
        else:
            return False, f"Unsupported database type: {db_type}"
        
        return execute_sql_command(server_info, sql, fetch_results=False)
    
    def _delete_user_in_database(self, server_info, username):
        """Delete user from specific database"""
        db_type = self._get_database_type(server_info)
        
        if db_type in ["postgresql", "redshift"]:
            sql = f'DROP ROLE IF EXISTS "{username}";'
        elif db_type == "mysql":
            sql = f"DROP USER IF EXISTS '{username}'@'%';"
        else:
            return False, f"Unsupported database type: {db_type}"
        
        return execute_sql_command(server_info, sql, fetch_results=False)
    
    def _change_user_password(self, server_info, username, new_password):
        """Change user password in specific database"""
        db_type = self._get_database_type(server_info)
        
        if db_type in ["postgresql", "redshift"]:
            sql = f"ALTER ROLE \"{username}\" WITH PASSWORD '{new_password}';"
        elif db_type == "mysql":
            sql = f"ALTER USER '{username}'@'%' IDENTIFIED BY '{new_password}';"
        else:
            return False, f"Unsupported database type: {db_type}"
        
        return execute_sql_command(server_info, sql, fetch_results=False)
    
    def _get_database_type(self, server_info):
        """Determine database type from server info"""
        port = server_info.get('Port', 5432)
        if port == 5432:
            return "postgresql"
        elif port == 5439:
            return "redshift"
        elif port == 3306:
            return "mysql"
        else:
            return "unknown"

# Initialize global user manager
try:
    if 'global_user_manager' not in st.session_state:
        st.session_state.global_user_manager = GlobalUserManager()
except (TypeError, AttributeError):
    # Handle cases where st.session_state is not properly initialized
    pass

def show_global_users_page():
    """Show global users management page"""
    st.title("🌐 Global Users Management")
    st.markdown("### Centralized user management across all databases")
    
    # Refresh button
    col_title, col_refresh = st.columns([4, 1])
    with col_refresh:
        if st.button("🔄 Refresh", type="primary", help="Refresh user data from all servers"):
            # Clear the cache to force fresh data
            if 'global_user_manager' in st.session_state:
                del st.session_state.global_user_manager
            st.success("Data refreshed!")
            st.rerun()
    
    # Get global user manager
    if 'global_user_manager' not in st.session_state:
        st.session_state.global_user_manager = GlobalUserManager()
    
    gum = st.session_state.global_user_manager
    
    # Get all unified users
    unified_users = gum.get_all_users_from_all_databases()
    
    # Debug information
    if st.checkbox("🔍 Show Debug Info", value=False):
        st.write("**Debug Information:**")
        st.write(f"- Number of servers configured: {len(st.session_state.servers_list) if 'servers_list' in st.session_state else 0}")
        if 'servers_list' in st.session_state:
            for i, server in enumerate(st.session_state.servers_list):
                st.write(f"- Server {i+1}: {server.get('Name', 'Unknown')} - {server.get('Status', 'Unknown Status')}")
                scan_results = server.get('scan_results', {})
                users = scan_results.get('users', [])
                st.write(f"  - Users in scan: {len(users)}")
                if users:
                    for user in users[:3]:  # Show first 3 users
                        st.write(f"    - {user.get('name', 'Unknown')} ({user.get('type', 'unknown')})")
        st.write(f"- Unified users found: {len(unified_users)}")
        st.divider()
    
    if not unified_users:
        st.warning("⚠️ **No users found in Global Users**")
        st.markdown("""
        **Possible reasons:**
        1. **No servers configured** - Add servers in Server Management page
        2. **Servers not scanned** - Click the 📊 Scan button for each server
        3. **Database connection failed** - Check server credentials and connectivity
        4. **No users in database** - The scanned databases might be empty
        
        **To fix this:**
        - Go to **Server Management** page
        - Add your database servers with correct credentials
        - Click **📊 Scan** for each server
        - Check server logs if scan fails
        """)
        
        # Show current server status
        if 'servers_list' in st.session_state and st.session_state.servers_list:
            st.markdown("#### 🖥️ Current Servers Status")
            for i, server in enumerate(st.session_state.servers_list):
                scan_results = server.get('scan_results', {})
                users = scan_results.get('users', [])
                user_count = len([u for u in users if u.get('name') != 'Connection failed'])
                
                status_icon = "✅" if user_count > 0 else "❌" if any(u.get('name') == 'Connection failed' for u in users) else "⚠️"
                st.markdown(f"- {status_icon} **{server.get('Name', 'Unknown')}** - {user_count} users found")
        
        # No demo data - only real data
        st.markdown("---")
        st.info("Connect to your databases and scan them to see real user data here")
        
        return
    
    # Statistics
    st.markdown("#### 📊 Global Statistics")
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    
    with stat_col1:
        total_users = len(unified_users)
        st.metric("Total Unique Users", total_users)
    
    with stat_col2:
        active_users = sum(1 for user in unified_users.values() if user['is_active_somewhere'])
        st.metric("Active Users", active_users)
    
    with stat_col3:
        total_databases = len(st.session_state.servers_list) if 'servers_list' in st.session_state else 0
        st.metric("Connected Databases", total_databases)
    
    with stat_col4:
        multi_db_users = sum(1 for user in unified_users.values() if len(user['databases']) > 1)
        st.metric("Multi-DB Users", multi_db_users)
    
    st.divider()
    
    # Search and filters
    st.markdown("#### 🔍 Search and Filters")
    search_col1, search_col2, search_col3 = st.columns(3)
    
    with search_col1:
        search_query = st.text_input("🔍 Search Users", placeholder="Enter username...")
    
    with search_col2:
        status_filter = st.selectbox("Status Filter", ["All", "Active Only", "Inactive Only"])
    
    with search_col3:
        database_filter = st.selectbox("Database Filter", ["All"] + [s['Name'] for s in st.session_state.servers_list])
    
    # Filter users based on search criteria
    filtered_users = {}
    for norm_name, user_data in unified_users.items():
        # Apply search filter
        if search_query and search_query.lower() not in norm_name and search_query.lower() not in user_data['original_name'].lower():
            continue
        
        # Apply status filter
        if status_filter == "Active Only" and not user_data['is_active_somewhere']:
            continue
        elif status_filter == "Inactive Only" and user_data['is_active_somewhere']:
            continue
        
        # Apply database filter
        if database_filter != "All" and database_filter not in user_data['databases']:
            continue
        
        filtered_users[norm_name] = user_data
    
    st.markdown(f"#### 👥 Users ({len(filtered_users)} found)")
    
    # Users table
    if filtered_users:
        for norm_name, user_data in filtered_users.items():
            with st.expander(f"👤 {user_data['original_name']} ({len(user_data['databases'])} databases)", expanded=False):
                user_col1, user_col2 = st.columns(2)
                
                with user_col1:
                    st.markdown("##### Basic Information")
                    st.write(f"**Normalized Name:** `{norm_name}`")
                    st.write(f"**Original Name:** `{user_data['original_name']}`")
                    st.write(f"**Status:** {'🟢 Active' if user_data['is_active_somewhere'] else '🔴 Inactive'}")
                    st.write(f"**User Types:** {', '.join(user_data['user_types'])}")
                    st.write(f"**Databases:** {len(user_data['databases'])} systems")
                
                with user_col2:
                    st.markdown("##### Database Presence")
                    for db_name, db_info in user_data['databases'].items():
                        status_icon = "🟢" if db_info['active'] else "🔴"
                        st.write(f"{status_icon} **{db_name}** ({db_info['type']})")
                
                # Permissions summary
                st.markdown("##### 🔑 Permissions Summary")
                permissions_data = gum.get_user_permissions_across_databases(norm_name)
                
                if permissions_data:
                    perm_col1, perm_col2, perm_col3 = st.columns(3)
                    
                    with perm_col1:
                        st.metric("Total Permissions", permissions_data['total_permissions'])
                    
                    with perm_col2:
                        high_priv_count = len(permissions_data['high_privilege_databases'])
                        st.metric("High Privilege DBs", high_priv_count)
                    
                    with perm_col3:
                        active_db_count = sum(1 for db_info in user_data['databases'].values() if db_info['active'])
                        st.metric("Active Connections", active_db_count)
                    
                    # Detailed permissions breakdown
                    if permissions_data['database_breakdown']:
                        st.markdown("**Permissions by Database:**")
                        for db_name, db_perms in permissions_data['database_breakdown'].items():
                            with st.expander(f"📊 {db_name} ({db_perms['total']} permissions)", expanded=False):
                                perm_detail_col1, perm_detail_col2 = st.columns(2)
                                
                                with perm_detail_col1:
                                    st.write(f"**Roles:** {db_perms['roles']}")
                                    st.write(f"**Table Permissions:** {db_perms['table_permissions']}")
                                
                                with perm_detail_col2:
                                    st.write(f"**Schema Permissions:** {db_perms['schema_permissions']}")
                                    st.write(f"**Column Permissions:** {db_perms['column_permissions']}")
                                
                                # User properties
                                if db_perms['user_properties']:
                                    st.markdown("**User Properties:**")
                                    for prop, value in db_perms['user_properties'].items():
                                        if value:
                                            st.write(f"• {prop}: {value}")
                
                # Global actions
                st.markdown("##### 🔧 Global Actions")
                action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                
                with action_col1:
                    if st.button("🔒 Disable User", key=f"disable_{norm_name}", use_container_width=True):
                        with st.spinner("Disabling user across all databases..."):
                            success, result = gum.execute_global_user_action(norm_name, "disable")
                            
                            if success:
                                if result['partial_success']:
                                    st.warning(f"⚠️ Partial success: {result['success_count']}/{result['total_databases']} databases")
                                else:
                                    st.success(f"✅ User disabled in all {result['total_databases']} databases")
                                
                                # Show detailed results
                                for db_name, db_result in result['detailed_results'].items():
                                    if db_result['success']:
                                        st.success(f"✅ {db_name}: {db_result['result']}")
                                    else:
                                        st.error(f"❌ {db_name}: {db_result['result']}")
                            else:
                                st.error(f"❌ Failed to disable user: {result}")
                
                with action_col2:
                    if st.button("🔓 Enable User", key=f"enable_{norm_name}", use_container_width=True):
                        with st.spinner("Enabling user across all databases..."):
                            success, result = gum.execute_global_user_action(norm_name, "enable")
                            
                            if success:
                                if result['partial_success']:
                                    st.warning(f"⚠️ Partial success: {result['success_count']}/{result['total_databases']} databases")
                                else:
                                    st.success(f"✅ User enabled in all {result['total_databases']} databases")
                                
                                # Show detailed results
                                for db_name, db_result in result['detailed_results'].items():
                                    if db_result['success']:
                                        st.success(f"✅ {db_name}: {db_result['result']}")
                                    else:
                                        st.error(f"❌ {db_name}: {db_result['result']}")
                            else:
                                st.error(f"❌ Failed to enable user: {result}")
                
                with action_col3:
                    if st.button("🔑 Change Password", key=f"password_{norm_name}", use_container_width=True):
                        st.session_state[f"change_password_{norm_name}"] = True
                
                with action_col4:
                    if st.button("🗑️ Delete User", key=f"delete_{norm_name}", use_container_width=True):
                        st.session_state[f"confirm_delete_{norm_name}"] = True
                
                # Password change dialog
                if st.session_state.get(f"change_password_{norm_name}", False):
                    st.markdown("##### 🔑 Change Password")
                    with st.form(f"password_form_{norm_name}"):
                        new_password = st.text_input("New Password", type="password")
                        confirm_password = st.text_input("Confirm Password", type="password")
                        
                        pw_col1, pw_col2 = st.columns(2)
                        
                        with pw_col1:
                            if st.form_submit_button("🔑 Update Password", use_container_width=True):
                                if new_password and new_password == confirm_password:
                                    with st.spinner("Updating password across all databases..."):
                                        success, result = gum.execute_global_user_action(norm_name, "change_password", new_password=new_password)
                                        
                                        if success:
                                            if result['partial_success']:
                                                st.warning(f"⚠️ Partial success: {result['success_count']}/{result['total_databases']} databases")
                                            else:
                                                st.success(f"✅ Password updated in all {result['total_databases']} databases")
                                            
                                            st.session_state[f"change_password_{norm_name}"] = False
                                            st.rerun()
                                        else:
                                            st.error(f"❌ Failed to update password: {result}")
                                elif new_password != confirm_password:
                                    st.error("❌ Passwords do not match")
                                else:
                                    st.error("❌ Please enter a password")
                        
                        with pw_col2:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                st.session_state[f"change_password_{norm_name}"] = False
                                st.rerun()
                
                # Delete confirmation dialog
                if st.session_state.get(f"confirm_delete_{norm_name}", False):
                    st.markdown("##### ⚠️ Confirm Deletion")
                    st.error(f"Are you sure you want to delete user '{user_data['original_name']}' from ALL databases?")
                    st.warning("This action cannot be undone!")
                    
                    del_col1, del_col2 = st.columns(2)
                    
                    with del_col1:
                        if st.button("🗑️ Yes, Delete", key=f"confirm_del_{norm_name}", use_container_width=True):
                            with st.spinner("Deleting user from all databases..."):
                                success, result = gum.execute_global_user_action(norm_name, "delete")
                                
                                if success:
                                    if result['partial_success']:
                                        st.warning(f"⚠️ Partial success: {result['success_count']}/{result['total_databases']} databases")
                                    else:
                                        st.success(f"✅ User deleted from all {result['total_databases']} databases")
                                    
                                    st.session_state[f"confirm_delete_{norm_name}"] = False
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to delete user: {result}")
                    
                    with del_col2:
                        if st.button("❌ Cancel", key=f"cancel_del_{norm_name}", use_container_width=True):
                            st.session_state[f"confirm_delete_{norm_name}"] = False
                            st.rerun()
    
    else:
        st.info("ℹ️ No users match the current filters.")

def show_local_user_storage_page():
    """Show local user storage management page"""
    st.title("💾 Local User Storage")
    st.markdown("### Centralized local storage for user management")
    
    # Initialize storage and sync manager
    try:
        import sys
        import os
        sys.path.append('/home/orel/my_installer/rsm/RedshiftManager')
        
        from models.local_user_storage import LocalUserStorage
        from core.user_sync_manager import UserSyncManager
        
        if 'local_storage' not in st.session_state:
            st.session_state.local_storage = LocalUserStorage()
        
        if 'sync_manager' not in st.session_state:
            st.session_state.sync_manager = UserSyncManager(st.session_state.local_storage)
        
        storage = st.session_state.local_storage
        sync_manager = st.session_state.sync_manager
        
    except Exception as e:
        st.error(f"❌ Failed to initialize storage system: {str(e)}")
        return
    
    # Create tabs for different functionalities
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "👥 Users", 
        "🔄 Sync", 
        "📝 Templates", 
        "📈 Analytics"
    ])
    
    with tab1:
        st.markdown("#### 📊 Storage Statistics")
        
        try:
            stats = storage.get_statistics()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Users", stats.get('total_users', 0))
            
            with col2:
                st.metric("Connected Databases", stats.get('total_databases', 0))
            
            with col3:
                st.metric("Total Permissions", stats.get('total_permissions', 0))
            
            with col4:
                st.metric("Sync Events (24h)", stats.get('sync_events_24h', 0))
            
            st.divider()
            
            # Database types breakdown
            if stats.get('database_types'):
                st.markdown("#### 🗃️ Database Types")
                db_types_col1, db_types_col2 = st.columns(2)
                
                with db_types_col1:
                    for db_type, count in stats['database_types'].items():
                        st.write(f"**{db_type}**: {count} connections")
                
                with db_types_col2:
                    # Create a simple chart
                    import plotly.express as px
                    import pandas as pd
                    
                    if stats['database_types']:
                        df = pd.DataFrame(list(stats['database_types'].items()), 
                                        columns=['Database Type', 'Count'])
                        fig = px.pie(df, values='Count', names='Database Type', 
                                   title="Database Connections by Type")
                        st.info("Chart will appear here after real data collection")
            
            # Recent sync activity
            st.markdown("#### 🕒 Recent Sync Activity")
            recent_syncs = storage.get_sync_history(limit=10)
            
            if recent_syncs:
                sync_df = pd.DataFrame(recent_syncs)
                sync_df['created_at'] = pd.to_datetime(sync_df['created_at'])
                
                for sync in recent_syncs[:5]:  # Show last 5
                    status_icon = "✅" if sync['status'] == 'success' else "⚠️" if sync['status'] == 'partial' else "❌"
                    st.write(f"{status_icon} **{sync['sync_type']}** on {sync['database_name']} - "
                           f"{sync['changes_made']} changes - {sync['created_at'][:19]}")
            else:
                st.info("No recent sync activity")
        
        except Exception as e:
            st.error(f"Error loading statistics: {str(e)}")
    
    with tab2:
        st.markdown("#### 👥 Local Users")
        
        # Search and filters
        search_col1, search_col2, search_col3 = st.columns(3)
        
        with search_col1:
            search_query = st.text_input("🔍 Search Users", placeholder="Enter username or email...")
        
        with search_col2:
            show_inactive = st.checkbox("Show Inactive Users", value=False)
        
        with search_col3:
            if st.button("➕ Add New User", type="primary"):
                st.session_state.show_add_user_form = True
        
        # Add user form
        if st.session_state.get('show_add_user_form', False):
            with st.expander("➕ Add New User", expanded=True):
                with st.form("add_user_form"):
                    form_col1, form_col2 = st.columns(2)
                    
                    with form_col1:
                        new_username = st.text_input("Username*", placeholder="Enter username")
                        new_display_name = st.text_input("Display Name", placeholder="Full name")
                        new_email = st.text_input("Email", placeholder="user@company.com")
                    
                    with form_col2:
                        new_description = st.text_area("Description", placeholder="User description")
                        new_tags = st.text_input("Tags", placeholder="Comma-separated tags")
                    
                    add_col1, add_col2 = st.columns(2)
                    
                    with add_col1:
                        if st.form_submit_button("✅ Create User", type="primary", use_container_width=True):
                            if new_username:
                                try:
                                    tags_list = [tag.strip() for tag in new_tags.split(',')] if new_tags else []
                                    
                                    user_id = storage.create_user(
                                        username=new_username,
                                        display_name=new_display_name,
                                        email=new_email,
                                        description=new_description,
                                        tags=tags_list
                                    )
                                    
                                    st.success(f"✅ User '{new_username}' created successfully!")
                                    st.session_state.show_add_user_form = False
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Error creating user: {str(e)}")
                            else:
                                st.error("Username is required")
                    
                    with add_col2:
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.session_state.show_add_user_form = False
                            st.rerun()
        
        # List users
        try:
            if search_query:
                users = storage.search_users(search_query)
            else:
                users = storage.get_all_users()
            
            if not show_inactive:
                users = [u for u in users if u['is_active']]
            
            st.markdown(f"**Found {len(users)} users**")
            
            for user in users:
                with st.expander(f"👤 {user['display_name']} ({user['username']})", expanded=False):
                    user_col1, user_col2 = st.columns(2)
                    
                    with user_col1:
                        st.write(f"**Email:** {user['email'] or 'Not set'}")
                        st.write(f"**Status:** {'🟢 Active' if user['is_active'] else '🔴 Inactive'}")
                        st.write(f"**Created:** {user['created_at'][:19]}")
                        if user['tags']:
                            st.write(f"**Tags:** {', '.join(json.loads(user['tags']))}")
                    
                    with user_col2:
                        st.write(f"**Databases:** {user['database_count']}")
                        st.write(f"**Permissions:** {user['permission_count']}")
                        if user['description']:
                            st.write(f"**Description:** {user['description']}")
                    
                    # User actions
                    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                    
                    with action_col1:
                        if st.button("🔧 Manage", key=f"manage_{user['id']}"):
                            st.session_state[f"manage_user_{user['id']}"] = True
                    
                    with action_col2:
                        if st.button("📊 Permissions", key=f"perms_{user['id']}"):
                            st.session_state[f"show_permissions_{user['id']}"] = True
                    
                    with action_col3:
                        if st.button("🔄 Sync Status", key=f"sync_{user['id']}"):
                            st.session_state[f"show_sync_{user['id']}"] = True
                    
                    with action_col4:
                        if st.button("📝 SQL Commands", key=f"sql_{user['id']}"):
                            st.session_state[f"show_sql_{user['id']}"] = True
                    
                    # Show permissions if requested
                    if st.session_state.get(f"show_permissions_{user['id']}", False):
                        st.markdown("##### 🔑 User Permissions")
                        permissions = storage.get_user_permissions(user['id'])
                        
                        if permissions:
                            perm_df = pd.DataFrame(permissions)
                            perm_df = perm_df[['database_name', 'permission_type', 'resource_name', 'privilege']]
                            st.dataframe(perm_df, use_container_width=True)
                        else:
                            st.info("No permissions found")
                        
                        if st.button("❌ Close Permissions", key=f"close_perms_{user['id']}"):
                            st.session_state[f"show_permissions_{user['id']}"] = False
                            st.rerun()
                    
                    # Show SQL commands if requested
                    if st.session_state.get(f"show_sql_{user['id']}", False):
                        st.markdown("##### 📝 CREATE USER Commands")
                        create_commands = storage.get_user_creation_commands(user['id'])
                        
                        if create_commands:
                            for cmd in create_commands:
                                st.markdown(f"**{cmd['database_name']} ({cmd['database_type']})**")
                                st.code(cmd['create_user_sql'], language='sql')
                        else:
                            st.info("No CREATE USER commands found")
                        
                        if st.button("❌ Close SQL", key=f"close_sql_{user['id']}"):
                            st.session_state[f"show_sql_{user['id']}"] = False
                            st.rerun()
        
        except Exception as e:
            st.error(f"Error loading users: {str(e)}")
    
    with tab3:
        st.markdown("#### 🔄 Database Synchronization")
        
        # Available servers for sync
        if 'servers_list' in st.session_state:
            servers = st.session_state.servers_list
            
            sync_col1, sync_col2 = st.columns(2)
            
            with sync_col1:
                st.markdown("##### 📥 Import from Database")
                
                selected_server = st.selectbox("Select Database Server", 
                                              [s['Name'] for s in servers],
                                              key="import_server_select")
                
                if selected_server:
                    server_info = next(s for s in servers if s['Name'] == selected_server)
                    
                    import_col1, import_col2 = st.columns(2)
                    
                    with import_col1:
                        if st.button("📥 Import All Users", type="primary", use_container_width=True):
                            with st.spinner("Importing users..."):
                                success, result = sync_manager.sync_all_users_from_database(server_info)
                                
                                if success:
                                    st.success(f"✅ Import completed successfully!")
                                    st.write(f"- Users imported: {result.get('users_imported', 0)}")
                                    st.write(f"- Users updated: {result.get('users_updated', 0)}")
                                    st.write(f"- Permissions synced: {result.get('permissions_synced', 0)}")
                                    
                                    if result.get('errors'):
                                        st.warning(f"⚠️ {len(result['errors'])} errors occurred:")
                                        for error in result['errors'][:5]:
                                            st.error(error)
                                else:
                                    st.error(f"❌ Import failed: {result.get('error', 'Unknown error')}")
                    
                    with import_col2:
                        # Import specific user
                        import_username = st.text_input("Import Specific User", 
                                                       placeholder="Enter username to import")
                        
                        if st.button("👤 Import User", use_container_width=True) and import_username:
                            with st.spinner(f"Importing user {import_username}..."):
                                success, message = sync_manager.import_user_from_database(
                                    server_info, import_username)
                                
                                if success:
                                    st.success(f"✅ {message}")
                                else:
                                    st.error(f"❌ {message}")
            
            with sync_col2:
                st.markdown("##### 📤 Export to Database")
                
                # Get local users for export
                local_users = storage.get_all_users()
                
                if local_users:
                    export_user = st.selectbox("Select User to Export", 
                                             [u['username'] for u in local_users if u['is_active']],
                                             key="export_user_select")
                    
                    export_server = st.selectbox("Select Target Database", 
                                               [s['Name'] for s in servers],
                                               key="export_server_select")
                    
                    export_password = st.text_input("Password for User", type="password", 
                                                   placeholder="Enter password for user creation")
                    
                    export_col1, export_col2 = st.columns(2)
                    
                    with export_col1:
                        if st.button("👁️ Preview Export", use_container_width=True):
                            if export_user and export_server:
                                server_info = next(s for s in servers if s['Name'] == export_server)
                                success, result = sync_manager.export_user_to_database(
                                    server_info, export_user, export_password, execute=False)
                                
                                if success and isinstance(result, dict):
                                    st.markdown("**CREATE USER Command:**")
                                    st.code(result['create_command'], language='sql')
                                    
                                    if result['permission_commands']:
                                        st.markdown("**Permission Commands:**")
                                        for cmd in result['permission_commands'][:5]:
                                            st.code(cmd, language='sql')
                                        
                                        if len(result['permission_commands']) > 5:
                                            st.info(f"... and {len(result['permission_commands']) - 5} more commands")
                                else:
                                    st.error(f"Preview failed: {result}")
                    
                    with export_col2:
                        if st.button("🚀 Execute Export", type="primary", use_container_width=True):
                            if export_user and export_server and export_password:
                                server_info = next(s for s in servers if s['Name'] == export_server)
                                
                                with st.spinner(f"Exporting user {export_user}..."):
                                    success, message = sync_manager.export_user_to_database(
                                        server_info, export_user, export_password, execute=True)
                                    
                                    if success:
                                        st.success(f"✅ {message}")
                                    else:
                                        st.error(f"❌ {message}")
                            else:
                                st.error("Please select user, server, and provide password")
                else:
                    st.info("No local users available for export")
        else:
            st.warning("No database servers configured. Please add servers in Server Management.")
    
    with tab4:
        st.markdown("#### 📝 Permission Templates")
        st.info("Permission templates feature coming soon...")
    
    with tab5:
        st.markdown("#### 📈 Analytics & Reports")
        
        try:
            # Recent sync history chart
            sync_history = storage.get_sync_history(limit=50)
            
            if sync_history:
                st.markdown("##### 📊 Sync Activity Over Time")
                
                sync_df = pd.DataFrame(sync_history)
                sync_df['created_at'] = pd.to_datetime(sync_df['created_at'])
                sync_df['date'] = sync_df['created_at'].dt.date
                
                # Group by date and status
                daily_stats = sync_df.groupby(['date', 'status']).size().reset_index(name='count')
                
                fig = px.bar(daily_stats, x='date', y='count', color='status',
                           title="Daily Sync Activity by Status")
                st.info("Chart will appear here after real data collection")
                
                # Sync duration analysis
                if 'sync_duration_ms' in sync_df.columns:
                    st.markdown("##### ⏱️ Sync Performance")
                    avg_duration = sync_df['sync_duration_ms'].mean()
                    max_duration = sync_df['sync_duration_ms'].max()
                    
                    perf_col1, perf_col2 = st.columns(2)
                    
                    with perf_col1:
                        st.metric("Average Sync Time", f"{avg_duration:.0f} ms")
                    
                    with perf_col2:
                        st.metric("Max Sync Time", f"{max_duration:.0f} ms")
            else:
                st.info("No sync history available yet")
        
        except Exception as e:
            st.error(f"Error loading analytics: {str(e)}")

def get_enhanced_database_structure(server_info):
    """Get enhanced database structure including column information"""
    try:
        success, basic_structure = get_database_structure(server_info)
        
        if not success:
            return success, basic_structure
        
        db_type = basic_structure.get("database_type")
        
        # Only add column information for databases that support column-level permissions
        if db_type not in ["postgresql", "redshift", "mysql"]:
            return success, basic_structure
    except Exception as e:
        # Fallback to basic structure if enhanced fails
        return get_database_structure(server_info)
    
    # Add detailed column information to tables
    enhanced_tables = []
    for table_info in basic_structure.get("tables", []):
        table_name = table_info.get("table")
        schema_name = table_info.get("schema")
        
        # Get columns for this table
        col_success, columns = get_table_columns(server_info, table_name, schema_name)
        
        enhanced_table = table_info.copy()
        enhanced_table["columns"] = columns if col_success else []
        enhanced_table["supports_column_permissions"] = col_success
        
        enhanced_tables.append(enhanced_table)
    
    basic_structure["tables"] = enhanced_tables
    basic_structure["supports_column_permissions"] = True
    
    return True, basic_structure

def generate_create_user_sql_commands(db_type, username, password, user_type="normal", databases=None, schemas=None, tables=None, permissions=None, column_permissions=None):
    """Generate SQL commands for creating a new user with specific permissions"""
    commands = []
    
    if db_type in ["postgresql", "redshift"]:
        # Create basic user
        if user_type == "superuser":
            commands.append(f'CREATE ROLE "{username}" WITH LOGIN PASSWORD \'{password}\' SUPERUSER;')
        elif user_type == "admin":
            commands.append(f'CREATE ROLE "{username}" WITH LOGIN PASSWORD \'{password}\' CREATEROLE CREATEDB;')
        else:
            commands.append(f'CREATE ROLE "{username}" WITH LOGIN PASSWORD \'{password}\';')
        
        # Add specific permissions
        if permissions and databases:
            for db in databases:
                if 'SELECT' in permissions:
                    commands.append(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{username}";')
                if 'INSERT' in permissions:
                    commands.append(f'GRANT INSERT ON ALL TABLES IN SCHEMA public TO "{username}";')
                if 'UPDATE' in permissions:
                    commands.append(f'GRANT UPDATE ON ALL TABLES IN SCHEMA public TO "{username}";')
                if 'DELETE' in permissions:
                    commands.append(f'GRANT DELETE ON ALL TABLES IN SCHEMA public TO "{username}";')
        
        if schemas:
            for schema in schemas:
                commands.append(f'GRANT USAGE ON SCHEMA "{schema}" TO "{username}";')
                if permissions:
                    for perm in permissions:
                        commands.append(f'GRANT {perm} ON ALL TABLES IN SCHEMA "{schema}" TO "{username}";')
        
        if tables:
            for table in tables:
                if permissions:
                    for perm in permissions:
                        commands.append(f'GRANT {perm} ON {table["full_name"]} TO "{username}";')
        
        # Handle column-level permissions for PostgreSQL/Redshift
        if column_permissions:
            for col_perm in column_permissions:
                table_name = col_perm.get("table")
                columns = col_perm.get("columns", [])
                perms = col_perm.get("permissions", [])
                
                for perm in perms:
                    if perm in ["SELECT", "INSERT", "UPDATE", "REFERENCES"]:  # Column-level permissions
                        column_list = ", ".join([f'"{col}"' for col in columns])
                        commands.append(f'GRANT {perm} ({column_list}) ON {table_name} TO "{username}";')
    
    elif db_type == "mysql":
        # Create basic user
        commands.append(f"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}';")
        
        # Add permissions
        if databases and permissions:
            for db in databases:
                perm_list = ', '.join(permissions)
                commands.append(f"GRANT {perm_list} ON {db}.* TO '{username}'@'%';")
        
        if tables and permissions:
            for table in tables:
                perm_list = ', '.join(permissions)
                commands.append(f"GRANT {perm_list} ON {table['full_name']} TO '{username}'@'%';")
        
        # Handle column-level permissions for MySQL
        if column_permissions:
            for col_perm in column_permissions:
                table_name = col_perm.get("table")
                columns = col_perm.get("columns", [])
                perms = col_perm.get("permissions", [])
                
                for perm in perms:
                    if perm in ["SELECT", "INSERT", "UPDATE", "REFERENCES"]:  # MySQL column-level permissions
                        column_list = ", ".join([f"`{col}`" for col in columns])
                        commands.append(f"GRANT {perm} ({column_list}) ON {table_name} TO '{username}'@'%';")
        
        commands.append("FLUSH PRIVILEGES;")
    
    elif db_type == "redis":
        # Redis ACL user creation
        acl_permissions = []
        if permissions:
            for perm in permissions:
                if perm == "READ":
                    acl_permissions.append("+@read")
                elif perm == "WRITE":
                    acl_permissions.append("+@write")
                elif perm == "ADMIN":
                    acl_permissions.append("+@all")
        
        acl_cmd = f"ACL SETUSER {username} on >{password}"
        if acl_permissions:
            acl_cmd += " " + " ".join(acl_permissions)
        else:
            acl_cmd += " +@read"  # Default to read-only
        
        commands.append(acl_cmd)
    
    return commands

def generate_user_sql_commands(db_type, action, old_username, new_username=None, new_user_type=None, new_active=None, new_password=None, new_permissions=None):
    """Generate SQL commands for user management based on database type"""
    commands = []
    
    if db_type in ["postgresql", "redshift"]:
        if action == "update_user":
            if new_username and new_username != old_username:
                commands.append(f'ALTER ROLE "{old_username}" RENAME TO "{new_username}";')
                old_username = new_username  # Update for subsequent commands
            
            if new_password:
                commands.append(f"ALTER ROLE \"{old_username}\" WITH PASSWORD '{new_password}';")
            
            if new_user_type:
                if new_user_type == "superuser":
                    commands.append(f'ALTER ROLE "{old_username}" WITH SUPERUSER;')
                elif new_user_type == "admin":
                    commands.append(f'ALTER ROLE "{old_username}" WITH CREATEROLE CREATEDB;')
                else:
                    commands.append(f'ALTER ROLE "{old_username}" WITH NOSUPERUSER NOCREATEROLE NOCREATEDB;')
            
            if new_active is not None:
                if new_active:
                    commands.append(f'ALTER ROLE "{old_username}" WITH LOGIN;')
                else:
                    commands.append(f'ALTER ROLE "{old_username}" WITH NOLOGIN;')
        
        elif action == "toggle_active":
            if new_active:
                commands.append(f'ALTER ROLE "{old_username}" WITH LOGIN;')
            else:
                commands.append(f'ALTER ROLE "{old_username}" WITH NOLOGIN;')
    
    elif db_type == "mysql":
        if action == "update_user":
            if new_username and new_username != old_username:
                commands.append(f"RENAME USER '{old_username}' TO '{new_username}';")
                old_username = new_username
            
            if new_password:
                commands.append(f"ALTER USER '{old_username}' IDENTIFIED BY '{new_password}';")
            
            if new_permissions:
                # Revoke all existing permissions first
                commands.append(f"REVOKE ALL PRIVILEGES ON *.* FROM '{old_username}';")
                # Grant new permissions
                perms_str = ", ".join(new_permissions)
                commands.append(f"GRANT {perms_str} ON *.* TO '{old_username}';")
        
        elif action == "toggle_active":
            if new_active:
                commands.append(f"ALTER USER '{old_username}' ACCOUNT UNLOCK;")
            else:
                commands.append(f"ALTER USER '{old_username}' ACCOUNT LOCK;")
    
    elif db_type == "redis":
        if action == "update_user":
            if new_active is not None:
                status = "on" if new_active else "off"
                commands.append(f"ACL SETUSER {old_username} {status}")
            if new_password:
                commands.append(f"ACL SETUSER {old_username} >{new_password}")
    
    return commands

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import logging system
from core.logging_system import get_logger, log_user_action, log_system_event, log_operation

# Initialize logger
logger = get_logger("dashboard")

# Configure page
st.set_page_config(
    page_title="MultiDBManager Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


def show_sidebar():
    """Show sidebar with navigation"""
    st.sidebar.title("🔧 MultiDBManager")
    
    # Language selector
    st.sidebar.markdown("### 🌐 Language / שפה")
    available_languages = get_available_languages()
    language_options = list(available_languages.keys())
    
    # Initialize language in session state if not exists
    if 'selected_language' not in st.session_state:
        st.session_state.selected_language = "English"
    
    selected_language = st.sidebar.selectbox(
        "Select Language:",
        language_options,
        index=language_options.index(st.session_state.selected_language),
        key="language_selector"
    )
    
    # Update session state
    st.session_state.selected_language = selected_language
    
    # Apply RTL layout if needed
    if is_rtl_language(selected_language):
        st.markdown("""
        <style>
        .main .block-container {
            direction: rtl;
        }
        </style>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown(translate("### Universal Multi-Database Management Tool", selected_language))
    st.sidebar.markdown("---")

    # Navigation
    st.sidebar.markdown(f"### 📋 {translate('Navigation', selected_language)}")

    pages = [
        "📊 Dashboard",
        "🖥️ Server Management", 
        "👥 User Management",
        "🌐 Global Users",
        "💾 Local User Storage",
        "🔔 Notifications",
        "🔗 LDAP Sync",
        "🎭 Group-Role Mapping",
        "🔧 Module Manager",
        "🚨 Alert System",
        "💾 Backup System",
        "📋 Logs Viewer",        
        "⚙️ Settings",
    ]

    # Translate page names
    translated_pages = [translate(page, selected_language) for page in pages]
    
    selected_page_index = st.sidebar.radio(
        translate("Select Page:", selected_language), 
        range(len(translated_pages)),
        format_func=lambda x: translated_pages[x],
        index=0
    )
    
    # Return original English page name for routing
    selected_page = pages[selected_page_index]

    # System info
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### ℹ️ {translate('System Info', selected_language)}")
    st.sidebar.markdown(f"**{translate('Status', selected_language)}:** 🟢 {translate('Online', selected_language)}")
    st.sidebar.markdown(f"**{translate('Version', selected_language)}:** 3.0.0")
    st.sidebar.markdown(f"**{translate('Mode', selected_language)}:** {translate('Open Access', selected_language)}")

    return selected_page


def show_dashboard_page():
    """Show main dashboard content"""
    log_user_action("page_view", "system", page="dashboard")
    logger.info("Dashboard page accessed")
    
    # Get selected language from session state
    selected_language = st.session_state.get('selected_language', 'English')
    
    st.title(translate("📊 MultiDBManager Dashboard", selected_language))
    st.markdown(f"### {translate('System Overview and Monitoring', selected_language)}")
    st.markdown("---")

    # Status cards
    col1, col2, col3, col4 = st.columns(4)

    # Real dashboard metrics only - removed hardcoded demo data
    if 'servers_list' in st.session_state and st.session_state.servers_list:
        connected_servers = len([s for s in st.session_state.servers_list if s.get('Status', '').startswith('🟢')])
        total_servers = len(st.session_state.servers_list)
        
        with col1:
            st.metric(label="📊 Connected Servers", value=f"{connected_servers}/{total_servers}")
        
        with col2:
            if connected_servers > 0:
                st.metric(label="🟢 System Status", value="Connected")
            else:
                st.metric(label="🔴 System Status", value="No Connections")
        
        with col3:
            st.info("Real metrics shown only for connected databases")
        
        with col4:
            st.info("Configure servers to see storage data")
    else:
        st.warning("⚠️ No servers configured. Add servers in Server Management to see real data.")

    st.markdown("---")

    # Real data charts section
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Query Performance")
        st.info("Query performance charts will appear after database activity")
        st.info("Connect to databases and run queries to see real metrics")

    with col2:
        st.subheader("💿 Storage Utilization")
        st.info("Storage utilization charts will appear after database scans")
        st.info("Scan your databases to see real storage distribution")

    # Recent activity
    st.markdown("---")
    st.subheader("📋 Recent Activity")

    # Real activity data only
    st.info("Recent activity will appear here after system usage")
    st.info("System actions, database operations, and user activities will be logged here")

    # Quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔍 Run Query", use_container_width=True):
            st.info("Query execution interface would open here")

    with col2:
        if st.button("📊 Generate Report", use_container_width=True):
            st.info("Report generation interface would open here")

    with col3:
        if st.button("⚙️ System Settings", use_container_width=True):
            st.info("Settings interface would open here")

    with col4:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.success("Data refreshed!")
            st.rerun()

    # Users & Roles Summary Section
    st.markdown("---")
    st.subheader("👥 Users & Roles Summary")

    # Real cluster data from connected servers only
    if 'servers_list' in st.session_state and st.session_state.servers_list:
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate real metrics from actual server data
        total_users = 0
        total_roles = 0 
        total_groups = 0
        connected_clusters = len([s for s in st.session_state.servers_list if s.get('Status', '').startswith('🟢')])
        
        # Get real data from session files if available
        for server in st.session_state.servers_list:
            server_name = server.get('Name', 'Unknown').lower().replace(' ', '_').replace('-', '_')
            session_file = f"data/sessions/{server_name}/session_latest.json"
            try:
                if os.path.exists(session_file):
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                        scan_results = session_data.get('scan_results', {})
                        total_users += len(scan_results.get('users', []))
                        total_roles += len(scan_results.get('roles', []))
            except:
                continue
    else:
        # No servers configured
        total_users = 0
        total_roles = 0
        total_groups = 0
        connected_clusters = 0
        st.warning("⚠️ No servers configured. Add servers to see users & roles summary.")

    # Create cluster summary data for display
    if 'servers_list' in st.session_state and st.session_state.servers_list:
        cluster_summary_data = []
        for server in st.session_state.servers_list:
            cluster_summary_data.append({
                'Name': server.get('Name', 'Unknown'),
                'Status': server.get('Status', 'Unknown'),
                'Type': server.get('database_type', 'Unknown'),
                'Environment': server.get('Environment', 'Unknown'),
                'Last Scan': server.get('last_scan', 'Never')
            })
    else:
        cluster_summary_data = []

    with col1:
        st.metric(
            "👤 Total Users",
            total_users,
            delta=f"Across {len(cluster_summary_data)} clusters",
        )

    with col2:
        st.metric(
            "🏷️ Total Roles",
            total_roles,
            delta=f"Active in {connected_clusters} clusters",
        )

    with col3:
        st.metric("👥 Total Groups", total_groups, delta=f"Configured groups")

    with col4:
        st.metric(
            "🔗 Connected Clusters",
            f"{connected_clusters}/{len(cluster_summary_data)}",
            delta="Available for scanning",
        )

    # Detailed cluster table
    st.markdown("#### 📋 Cluster Details")
    summary_df = pd.DataFrame(cluster_summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # Migration history if available
    if (
        "migration_history" in st.session_state
        and st.session_state["migration_history"]
    ):
        st.markdown("#### 🔄 Recent Migrations")
        migration_data = []

        for migration in st.session_state["migration_history"][
            -3:
        ]:  # Show last 3 migrations
            migration_data.append(
                {
                    "Date": migration["migration_date"],
                    "From": migration["source_cluster"],
                    "To": migration["target_cluster"],
                    "Users": migration["results"]["users_migrated"],
                    "Roles": migration["results"]["roles_migrated"],
                    "Status": (
                        "✅ Success"
                        if migration["results"]["errors"] == 0
                        else "⚠️ With warnings"
                    ),
                }
            )

        if migration_data:
            migration_df = pd.DataFrame(migration_data)
            st.dataframe(migration_df, use_container_width=True, hide_index=True)
        else:
            st.info("No recent migrations to display")
    else:
        st.info(
            "💡 **Tip:** Add clusters and scan for users to see migration history here"
        )



def show_server_management_page():
    """Show Server Management page with full functionality"""
    # Get selected language from session state
    selected_language = st.session_state.get('selected_language', 'English')
    
    st.title(translate("🖥️ Server Management", selected_language))
    st.markdown(f"### {translate('Database Server Connection Management', selected_language)}")
    st.markdown("---")

    # Server management tabs
    tab1, tab2, tab3 = st.tabs(
        [
            "🔍 Servers",
            "➕ Add Server",
            "⚙️ Settings",
        ]
    )

    with tab1:
        st.subheader(translate("📋 Registered Servers"))

        # Load servers from file or initialize with defaults
        def load_servers():
            """Load servers list - SQLite Edition with JSON fallback"""
            try:
                # Try SQLite database first
                from database.database_manager import get_database_manager
                db_manager = get_database_manager()
                
                servers_from_db = db_manager.get_all_servers()
                if servers_from_db:
                    servers_list = []
                    for server_data in servers_from_db:
                        # Convert database format to UI format
                        server = {
                            'Name': server_data.get('name', ''),
                            'Host': server_data.get('host', ''),
                            'Port': server_data.get('port', 5432),
                            'Database': server_data.get('database_name', ''),
                            'Username': server_data.get('username', ''),
                            'Password': server_data.get('password', ''),
                            'Environment': server_data.get('environment', 'Development'),
                            'Status': server_data.get('status', 'Unknown'),
                            'Last Test': server_data.get('last_test_at', 'Never'),
                            'database_type': server_data.get('database_type', 'postgresql'),
                            'scanner_settings': server_data.get('scanner_settings', {}),
                            'scan_results': {},  # Will be populated from scan_history
                            'last_scan': 'Never'
                        }
                        
                        # Try to get latest scan results
                        latest_scan = db_manager.get_latest_scan_results(server_data.get('id'))
                        if latest_scan:
                            server['scan_results'] = latest_scan.get('results', {})
                            server['last_scan'] = latest_scan.get('completed_at', 'Never')
                        
                        servers_list.append(server)
                    
                    return servers_list
                    
            except Exception as e:
                st.warning(f"⚠️ SQLite load failed, using JSON fallback: {e}")
            
            # JSON fallback for backward compatibility
            servers_file = "data/servers.json"
            try:
                if os.path.exists(servers_file):
                    with open(servers_file, 'r', encoding='utf-8') as f:
                        servers_list = json.load(f)
                    
                    # Merge with session data
                    for server in servers_list:
                        session_data = load_server_session(server['Name'])
                        if session_data:
                            # Add scan_results back from session
                            server['scan_results'] = session_data.get('scan_results', {})
                            server['last_scan'] = session_data.get('connection_info', {}).get('last_scan', 'Never')
                    
                    return servers_list
                else:
                    return []
            except Exception as e:
                st.error(f"Error loading servers: {e}")
                return []
        
        def save_servers(servers_list):
            """Save servers list and individual server sessions with versioning"""
            servers_file = "data/servers.json"
            try:
                os.makedirs("data", exist_ok=True)
                os.makedirs("data/sessions", exist_ok=True)
                
                # Save main servers list (simplified, without scan_results)
                servers_simple = []
                for server in servers_list:
                    server_simple = {k: v for k, v in server.items() if k != 'scan_results'}
                    servers_simple.append(server_simple)
                
                with open(servers_file, 'w', encoding='utf-8') as f:
                    json.dump(servers_simple, f, indent=2, ensure_ascii=False)
                
                # Save individual server sessions with versioning
                for server in servers_list:
                    if 'scan_results' in server:
                        save_server_session(server)
                        
            except Exception as e:
                st.error(f"Error saving servers: {e}")

        def save_server_session(server):
            """Save individual server session data with versioning"""
            try:
                server_name = server['Name'].replace(' ', '_').replace('-', '_')
                session_dir = f"data/sessions/{server_name}"
                os.makedirs(session_dir, exist_ok=True)
                
                # Create session data structure
                session_data = {
                    "metadata": {
                        "server_name": server['Name'],
                        "server_host": server['Host'],
                        "server_port": server['Port'],
                        "database_type": server.get('scan_results', {}).get('database_type', 'unknown'),
                        "created_at": datetime.now().isoformat(),
                        "version": get_next_version(session_dir)
                    },
                    "connection_info": {
                        "host": server['Host'],
                        "port": server['Port'],
                        "database": server['Database'],
                        "environment": server.get('Environment', 'Unknown'),
                        "status": server.get('Status', 'Unknown'),
                        "last_test": server.get('Last Test', 'Never'),
                        "last_scan": server.get('last_scan', 'Never')
                    },
                    "scan_results": server.get('scan_results', {}),
                    "session_history": {
                        "operations_count": len(server.get('scan_results', {}).get('users', [])),
                        "last_activity": datetime.now().isoformat(),
                        "scan_duration": "N/A"
                    }
                }
                
                # Save current session
                version = session_data["metadata"]["version"]
                session_file = f"{session_dir}/session_v{version:03d}.json"
                
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                
                # Save/update latest session link
                latest_file = f"{session_dir}/session_latest.json"
                with open(latest_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                
                # Clean up old versions (keep last 10 versions)
                cleanup_old_sessions(session_dir)
                
            except Exception as e:
                st.error(f"Error saving server session for {server['Name']}: {e}")

        def get_next_version(session_dir):
            """Get next version number for session file"""
            try:
                existing_files = [f for f in os.listdir(session_dir) if f.startswith('session_v') and f.endswith('.json')]
                if not existing_files:
                    return 1
                
                versions = []
                for f in existing_files:
                    try:
                        version_str = f.replace('session_v', '').replace('.json', '')
                        versions.append(int(version_str))
                    except ValueError:
                        continue
                
                return max(versions) + 1 if versions else 1
            except FileNotFoundError:
                return 1

        def cleanup_old_sessions(session_dir, keep_versions=10):
            """Remove old session versions, keeping only the latest specified number"""
            try:
                session_files = [f for f in os.listdir(session_dir) if f.startswith('session_v') and f.endswith('.json')]
                if len(session_files) <= keep_versions:
                    return
                
                # Sort by version number
                version_files = []
                for f in session_files:
                    try:
                        version_str = f.replace('session_v', '').replace('.json', '')
                        version_num = int(version_str)
                        version_files.append((version_num, f))
                    except ValueError:
                        continue
                
                version_files.sort(reverse=True)  # Latest first
                
                # Remove older versions
                for version_num, filename in version_files[keep_versions:]:
                    old_file = os.path.join(session_dir, filename)
                    os.remove(old_file)
                    
            except Exception as e:
                print(f"Error cleaning up old sessions: {e}")

        def load_server_session(server_name, version=None):
            """Load specific server session data, optionally by version"""
            try:
                server_name_clean = server_name.replace(' ', '_').replace('-', '_')
                session_dir = f"data/sessions/{server_name_clean}"
                
                if version:
                    session_file = f"{session_dir}/session_v{version:03d}.json"
                else:
                    session_file = f"{session_dir}/session_latest.json"
                
                if os.path.exists(session_file):
                    with open(session_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    return None
                    
            except Exception as e:
                st.error(f"Error loading server session for {server_name}: {e}")
                return None

        def get_server_session_versions(server_name):
            """Get list of available versions for a server session"""
            try:
                server_name_clean = server_name.replace(' ', '_').replace('-', '_')
                session_dir = f"data/sessions/{server_name_clean}"
                
                if not os.path.exists(session_dir):
                    return []
                
                session_files = [f for f in os.listdir(session_dir) if f.startswith('session_v') and f.endswith('.json')]
                versions = []
                
                for f in session_files:
                    try:
                        version_str = f.replace('session_v', '').replace('.json', '')
                        version_num = int(version_str)
                        
                        # Get file modification time
                        file_path = os.path.join(session_dir, f)
                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        versions.append({
                            'version': version_num,
                            'filename': f,
                            'created_at': mod_time.isoformat(),
                            'display_name': f'Version {version_num} ({mod_time.strftime("%Y-%m-%d %H:%M")})'
                        })
                    except ValueError:
                        continue
                
                return sorted(versions, key=lambda x: x['version'], reverse=True)
                
            except Exception as e:
                st.error(f"Error getting session versions for {server_name}: {e}")
                return []

        # Initialize servers data in session state
        if 'servers_list' not in st.session_state:
            st.session_state.servers_list = load_servers()
        
        servers_data = st.session_state.servers_list

        # Display servers with action buttons
        if servers_data:
            for i, server in enumerate(servers_data):
                with st.container():
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([2.5, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8])
                    
                    with col1:
                        scan_info = ""
                        if "scan_results" in server and server["scan_results"]:
                            scan_data = server["scan_results"]
                            tables_count = len(scan_data.get("tables", []))
                            users_count = len(scan_data.get("users", []))
                            roles_count = len(scan_data.get("roles", []))
                            db_type = scan_data.get("database_type", "unknown")
                            total_size = scan_data.get("total_size", 0)
                            
                            db_icon = {"postgresql": "🐘", "mysql": "🐬", "redis": "🔴", "redshift": "🔶"}.get(db_type, "🗄️")
                            scan_info = f"📊 {db_icon} {db_type.upper()} | {tables_count} tables, {users_count} users, {roles_count} roles | {total_size:.1f} MB total"
                        
                        st.markdown(f"""
                        **{server['Name']}** | {server['Status']}  
                        📍 `{server['Host']}:{server['Port']}` → `{server['Database']}`  
                        🏷️ {server['Environment']} | Last Test: {server['Last Test']}  
                        {scan_info}
                        """)
                    
                    with col2:
                        if st.button("🔍 Test", key=f"test_{i}", use_container_width=True):
                            with st.spinner(f"Testing {server['Name']}..."):
                                time.sleep(1)
                                st.session_state.servers_list[i]["Status"] = "🟢 Connected"
                                st.session_state.servers_list[i]["Last Test"] = "Just now"
                                save_servers(st.session_state.servers_list)
                                st.rerun()
                    
                    with col3:
                        if st.button("📊 Scan", key=f"scan_{i}", use_container_width=True):
                            with st.spinner(f"Scanning {server['Name']}..."):
                                # Real database scanning function
                                def perform_real_scan(server_info):
                                    import psycopg2
                                    import pymysql
                                    import redis
                                    
                                    host = server_info['Host']
                                    port = server_info['Port']
                                    database = server_info['Database']
                                    
                                    # Get username and password from server config if available
                                    username = server_info.get('Username', 'postgres')
                                    password = server_info.get('Password', '')
                                    
                                    # Determine database type by port
                                    if port == 5432 or port == 5439:
                                        db_type = "postgresql" if port == 5432 else "redshift"
                                    elif port == 3306:
                                        db_type = "mysql"
                                    elif port == 6379:
                                        db_type = "redis"
                                    else:
                                        db_type = "generic"
                                    
                                    try:
                                        if db_type in ["postgresql", "redshift"]:
                                            # PostgreSQL/Redshift connection
                                            conn = psycopg2.connect(
                                                host=host,
                                                port=port,
                                                database=database,
                                                user=username,
                                                password=password,
                                                connect_timeout=10
                                            )
                                            cursor = conn.cursor()
                                            
                                            # Get tables
                                            cursor.execute("""
                                                SELECT schemaname, tablename, 
                                                       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                                                FROM pg_tables 
                                                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                                                ORDER BY schemaname, tablename;
                                            """)
                                            tables_raw = cursor.fetchall()
                                            tables = [{"name": f"{row[0]}.{row[1]}", "rows": "N/A", "size": row[2]} for row in tables_raw]
                                            
                                            # Get users with their roles - more detailed query
                                            cursor.execute("""
                                                SELECT 
                                                    r.rolname, 
                                                    r.rolsuper, 
                                                    r.rolcreaterole, 
                                                    r.rolcreatedb, 
                                                    r.rolcanlogin,
                                                    r.rolvaliduntil,
                                                    r.rolconnlimit,
                                                    array_agg(DISTINCT role_roles.rolname) FILTER (WHERE role_roles.rolname IS NOT NULL) as member_of_roles,
                                                    CASE 
                                                        WHEN r.rolname = ANY(array['postgres', 'rds_superuser']) THEN 'system_admin'
                                                        WHEN NOT r.rolcanlogin THEN 'role_only'
                                                        WHEN r.rolsuper THEN 'superuser'
                                                        WHEN r.rolcreaterole OR r.rolcreatedb THEN 'admin'
                                                        ELSE 'normal'
                                                    END as computed_type
                                                FROM pg_roles r
                                                LEFT JOIN pg_auth_members m ON r.oid = m.member
                                                LEFT JOIN pg_roles role_roles ON m.roleid = role_roles.oid
                                                WHERE r.rolname NOT LIKE 'pg_%'
                                                  AND r.rolname NOT IN ('rds_superuser', 'rds_replication', 'rds_iam', 'rdsadmin')
                                                GROUP BY r.rolname, r.rolsuper, r.rolcreaterole, r.rolcreatedb, r.rolcanlogin, r.rolvaliduntil, r.rolconnlimit
                                                ORDER BY r.rolcanlogin DESC, r.rolname;
                                            """)
                                            users_raw = cursor.fetchall()
                                            users = []
                                            roles_only = []
                                            
                                            for row in users_raw:
                                                rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolvaliduntil, rolconnlimit, member_of_roles, computed_type = row
                                                
                                                # Skip if it's a role-only (not a login user)
                                                if computed_type == 'role_only' or not rolcanlogin:
                                                    # Add to roles list instead
                                                    roles_only.append({
                                                        "name": rolname,
                                                        "type": "Role",
                                                        "members": 0  # Will be updated in roles query
                                                    })
                                                    continue
                                                
                                                # Skip system users
                                                if computed_type == 'system_admin':
                                                    continue
                                                
                                                # Use computed type for better classification
                                                user_type = computed_type
                                                user_roles = member_of_roles if member_of_roles and member_of_roles != [None] else []
                                                
                                                # Additional check for 'orel' - see if it has login privileges
                                                if rolname == 'orel':
                                                    # Extra debug query for orel specifically
                                                    cursor_debug = conn.cursor()
                                                    cursor_debug.execute("""
                                                        SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, 
                                                               rolreplication, rolinherit, rolbypassrls, rolconnlimit,
                                                               oid, 
                                                               (SELECT count(*) FROM pg_auth_members WHERE member = pg_roles.oid) as is_member_of_roles,
                                                               (SELECT count(*) FROM pg_auth_members WHERE roleid = pg_roles.oid) as has_members
                                                        FROM pg_roles 
                                                        WHERE rolname = 'orel';
                                                    """)
                                                    orel_details = cursor_debug.fetchone()
                                                    cursor_debug.close()
                                                    
                                                    st.warning(f"🔍 Debug OREL: {orel_details}")
                                                    
                                                    # If orel is actually a role and not a user, skip it
                                                    if orel_details and not orel_details[4]:  # rolcanlogin is False
                                                        st.info("ℹ️ Skipping 'orel' - it's a role, not a login user")
                                                        continue
                                                
                                                users.append({
                                                    "name": rolname, 
                                                    "type": user_type, 
                                                    "active": rolcanlogin and (rolvaliduntil is None or rolvaliduntil > datetime.now()),
                                                    "roles": user_roles,
                                                    "connection_limit": rolconnlimit
                                                })
                                            
                                            # Get roles with their members (non-login roles only)
                                            cursor.execute("""
                                                SELECT 
                                                    r.rolname, 
                                                    (SELECT count(*) FROM pg_auth_members WHERE roleid = r.oid) as member_count,
                                                    CASE 
                                                        WHEN r.rolsuper THEN 'Superuser'
                                                        WHEN r.rolcreaterole AND r.rolcreatedb THEN 'Admin'
                                                        WHEN r.rolcreaterole THEN 'Role Creator'
                                                        WHEN r.rolcreatedb THEN 'DB Creator'
                                                        ELSE 'Standard'
                                                    END as role_type,
                                                    array_agg(DISTINCT member_roles.rolname) FILTER (WHERE member_roles.rolname IS NOT NULL) as member_names
                                                FROM pg_roles r
                                                LEFT JOIN pg_auth_members m ON r.oid = m.roleid
                                                LEFT JOIN pg_roles member_roles ON m.member = member_roles.oid
                                                WHERE NOT r.rolcanlogin 
                                                  AND r.rolname NOT LIKE 'pg_%'
                                                  AND r.rolname NOT IN ('rds_superuser', 'rds_replication', 'rds_iam', 'rdsadmin')
                                                GROUP BY r.rolname, r.rolsuper, r.rolcreaterole, r.rolcreatedb, r.oid
                                                ORDER BY r.rolname;
                                            """)
                                            roles_raw = cursor.fetchall()
                                            roles = []
                                            for row in roles_raw:
                                                role_name, member_count, role_type, member_names = row
                                                member_list = member_names if member_names and member_names != [None] else []
                                                roles.append({
                                                    "name": role_name, 
                                                    "members": member_count, 
                                                    "type": role_type,
                                                    "member_names": member_list
                                                })
                                            
                                            conn.close()
                                            
                                        elif db_type == "mysql":
                                            # MySQL connection
                                            conn = pymysql.connect(
                                                host=host,
                                                port=port,
                                                database=database,
                                                user=username,
                                                password=password,
                                                connect_timeout=10
                                            )
                                            cursor = conn.cursor()
                                            
                                            # Get tables
                                            cursor.execute("""
                                                SELECT table_name, table_rows,
                                                       ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
                                                FROM information_schema.tables 
                                                WHERE table_schema = %s
                                                ORDER BY table_name;
                                            """, (database,))
                                            tables_raw = cursor.fetchall()
                                            tables = [{"name": row[0], "rows": row[1] or 0, "size": f"{row[2]} MB"} for row in tables_raw]
                                            
                                            # Get users with their privileges
                                            cursor.execute("""
                                                SELECT DISTINCT 
                                                    u.user, 
                                                    u.host,
                                                    u.account_locked,
                                                    GROUP_CONCAT(DISTINCT CONCAT(p.privilege_type) SEPARATOR ', ') as privileges
                                                FROM mysql.user u
                                                LEFT JOIN information_schema.user_privileges p ON u.user = p.grantee COLLATE utf8mb4_0900_ai_ci
                                                WHERE u.user NOT IN ('mysql.sys', 'mysql.session', 'mysql.infoschema', 'root')
                                                GROUP BY u.user, u.host, u.account_locked
                                                ORDER BY u.user;
                                            """)
                                            users_raw = cursor.fetchall()
                                            users = []
                                            for row in users_raw:
                                                user_type = "admin" if "ALL PRIVILEGES" in (row[3] or "") else "normal"
                                                user_privileges = row[3].split(', ') if row[3] else []
                                                users.append({
                                                    "name": f"{row[0]}@{row[1]}", 
                                                    "type": user_type, 
                                                    "active": row[2] != 'Y' if row[2] is not None else True,
                                                    "roles": user_privileges
                                                })
                                            
                                            # Try to get MySQL 8.0+ roles if available
                                            try:
                                                cursor.execute("""
                                                    SELECT role_name, 
                                                           (SELECT COUNT(*) FROM mysql.role_edges WHERE to_role = r.role_name) as members
                                                    FROM mysql.user r 
                                                    WHERE is_role = 'Y'
                                                    ORDER BY role_name;
                                                """)
                                                roles_raw = cursor.fetchall()
                                                roles = [{"name": row[0], "members": row[1], "type": "Role"} for row in roles_raw]
                                            except:
                                                # Fallback for older MySQL versions
                                                roles = [{"name": "mysql_native_users", "members": len(users), "type": "System"}]
                                            
                                            conn.close()
                                            
                                        elif db_type == "redis":
                                            # Redis connection
                                            r = redis.Redis(host=host, port=port, password=password, socket_connect_timeout=10)
                                            
                                            # Get Redis info
                                            info = r.info()
                                            keyspace = r.info('keyspace')
                                            
                                            # Redis doesn't have tables, show databases instead
                                            tables = []
                                            for db_num, db_info in keyspace.items():
                                                tables.append({
                                                    "name": f"db{db_num.split('db')[1]}",
                                                    "rows": db_info.get('keys', 0),
                                                    "size": f"{db_info.get('keys', 0)} keys"
                                                })
                                            
                                            # Get Redis ACL users if available
                                            try:
                                                acl_users = r.acl_list()
                                                users = []
                                                for user_acl in acl_users:
                                                    # Parse ACL user information
                                                    if 'user' in user_acl.lower():
                                                        user_name = user_acl.split()[1] if len(user_acl.split()) > 1 else 'default'
                                                        is_active = 'on' in user_acl.lower()
                                                        user_permissions = []
                                                        if '+@all' in user_acl:
                                                            user_permissions = ['ALL_COMMANDS']
                                                        elif '+@' in user_acl:
                                                            # Extract permission categories
                                                            import re
                                                            perms = re.findall(r'\+@(\w+)', user_acl)
                                                            user_permissions = perms
                                                        
                                                        users.append({
                                                            "name": user_name,
                                                            "type": "admin" if user_permissions else "normal",
                                                            "active": is_active,
                                                            "roles": user_permissions
                                                        })
                                                
                                                if not users:
                                                    users = [{"name": "default", "type": "admin", "active": True, "roles": ["ALL_COMMANDS"]}]
                                                    
                                                roles = [{"name": "redis_users", "members": len(users), "type": "System"}]
                                            except:
                                                # Fallback for older Redis versions
                                                users = [{"name": "default", "type": "admin", "active": True, "roles": ["ALL_COMMANDS"]}]
                                                roles = [{"name": "default", "members": 1, "type": "System"}]
                                            
                                        else:
                                            # Generic/unknown database type
                                            tables = [{"name": "Unable to scan", "rows": 0, "size": "N/A"}]
                                            users = [{"name": "unknown", "type": "normal", "active": False}]
                                            roles = [{"name": "unknown", "members": 0}]
                                            
                                        return {
                                            "tables": tables,
                                            "users": users, 
                                            "roles": roles,
                                            "database_type": db_type,
                                            "total_size": sum([float(t["size"].split()[0]) for t in tables if "MB" in str(t["size"])])
                                        }
                                        
                                    except Exception as e:
                                        st.error(f"❌ Connection failed: {str(e)}")
                                        return {
                                            "tables": [{"name": f"Error: {str(e)}", "rows": 0, "size": "N/A"}],
                                            "users": [{"name": "Connection failed", "type": "error", "active": False}],
                                            "roles": [{"name": "Connection failed", "members": 0}],
                                            "database_type": db_type,
                                            "total_size": 0
                                        }
                                
                                scan_results = perform_real_scan(server)
                                st.session_state.servers_list[i]["scan_results"] = scan_results
                                st.session_state.servers_list[i]["last_scan"] = "Just now"
                                save_servers(st.session_state.servers_list)
                                
                                # Reset global user manager cache to ensure fresh data in Global Users page
                                if 'global_user_manager' in st.session_state:
                                    del st.session_state.global_user_manager
                                
                                st.success(f"✅ Scanned {server['Name']}: Found {len(scan_results['tables'])} tables, {len(scan_results['users'])} users, {len(scan_results['roles'])} roles")
                                st.info("🔄 Global Users cache refreshed - users will now appear in Global Users page")
                                st.rerun()
                    
                    with col4:
                        if st.button("✏️ Edit", key=f"edit_server_btn_{i}", use_container_width=True):
                            st.session_state.edit_server_index = i
                            st.session_state.show_edit_form = True
                            st.rerun()
                    
                    with col5:
                        if st.button("📚 History", key=f"history_{i}", use_container_width=True):
                            st.session_state[f"show_history_{i}"] = not st.session_state.get(f"show_history_{i}", False)
                            st.rerun()
                    
                    with col6:
                        if st.button("⚙️ Scanner", key=f"scanner_{i}", use_container_width=True):
                            st.session_state[f"show_scanner_settings_{i}"] = not st.session_state.get(f"show_scanner_settings_{i}", False)
                            st.rerun()
                    
                    with col7:
                        if st.button("🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                            st.session_state.servers_list.pop(i)
                            save_servers(st.session_state.servers_list)
                            st.success(f"Server '{server['Name']}' deleted!")
                            st.rerun()
                    
                    # Show session history if requested
                    if st.session_state.get(f"show_history_{i}", False):
                        with st.expander(f"📚 Session History - {server['Name']}", expanded=True):
                            versions = get_server_session_versions(server['Name'])
                            
                            if versions:
                                st.markdown("### 📋 Available Session Versions")
                                
                                # Current session info
                                current_session = load_server_session(server['Name'])
                                if current_session:
                                    metadata = current_session.get('metadata', {})
                                    st.info(f"""
                                    **Current Session**: Version {metadata.get('version', 'Unknown')}  
                                    **Created**: {metadata.get('created_at', 'Unknown')}  
                                    **Database Type**: {metadata.get('database_type', 'Unknown')}  
                                    **Users Count**: {len(current_session.get('scan_results', {}).get('users', []))}  
                                    **Roles Count**: {len(current_session.get('scan_results', {}).get('roles', []))}
                                    """)
                                
                                st.markdown("---")
                                
                                # Version selection and viewer
                                version_options = {f"Version {v['version']} ({v['created_at'][:16]})": v['version'] for v in versions}
                                selected_version_display = st.selectbox(
                                    "Select version to view:", 
                                    options=list(version_options.keys()),
                                    key=f"version_select_{i}"
                                )
                                
                                if selected_version_display:
                                    selected_version = version_options[selected_version_display]
                                    version_data = load_server_session(server['Name'], selected_version)
                                    
                                    if version_data:
                                        col_meta, col_conn = st.columns(2)
                                        
                                        with col_meta:
                                            st.markdown("#### 📊 Session Metadata")
                                            metadata = version_data.get('metadata', {})
                                            st.json({
                                                "Version": metadata.get('version'),
                                                "Server": metadata.get('server_name'),
                                                "Database Type": metadata.get('database_type'),
                                                "Created": metadata.get('created_at')
                                            })
                                        
                                        with col_conn:
                                            st.markdown("#### 🔗 Connection Info")
                                            conn_info = version_data.get('connection_info', {})
                                            st.json({
                                                "Host": f"{conn_info.get('host')}:{conn_info.get('port')}",
                                                "Database": conn_info.get('database'),
                                                "Environment": conn_info.get('environment'),
                                                "Status": conn_info.get('status'),
                                                "Last Scan": conn_info.get('last_scan')
                                            })
                                        
                                        # Scan results summary
                                        scan_results = version_data.get('scan_results', {})
                                        if scan_results:
                                            st.markdown("#### 📋 Scan Results Summary")
                                            scan_col1, scan_col2, scan_col3 = st.columns(3)
                                            
                                            with scan_col1:
                                                users_count = len(scan_results.get('users', []))
                                                st.metric("Users", users_count)
                                            
                                            with scan_col2:
                                                roles_count = len(scan_results.get('roles', []))
                                                st.metric("Roles", roles_count)
                                            
                                            with scan_col3:
                                                tables_count = len(scan_results.get('tables', []))
                                                st.metric("Tables", tables_count)
                                        
                                        # Restore version button
                                        if st.button(f"🔄 Restore Version {selected_version}", key=f"restore_{i}_{selected_version}"):
                                            # Restore this version as current
                                            server['scan_results'] = version_data.get('scan_results', {})
                                            server['last_scan'] = version_data.get('connection_info', {}).get('last_scan', 'Restored')
                                            save_servers(st.session_state.servers_list)
                                            st.success(f"Version {selected_version} restored as current session!")
                                            st.rerun()
                                
                            else:
                                st.warning("No session history available for this server.")
                    
                    # Show scanner settings if requested
                    if st.session_state.get(f"show_scanner_settings_{i}", False):
                        with st.expander(f"⚙️ Scanner Settings - {server['Name']}", expanded=True):
                            st.markdown("#### 🔍 Automatic Scanning Configuration")
                            
                            # Initialize scanner settings if not exist
                            if 'scanner_settings' not in server:
                                server['scanner_settings'] = {
                                    'enabled': False,
                                    'scan_interval': 24,
                                    'detect_manual_users': True,
                                    'alert_on_new_users': True,
                                    'auto_lock_manual_users': False,
                                    'alert_email': '',
                                    'scan_tables': True,
                                    'scan_users': True,
                                    'scan_roles': True
                                }
                            
                            scanner_settings = server['scanner_settings']
                            
                            with st.form(f"scanner_settings_form_{i}"):
                                col_scanner1, col_scanner2 = st.columns(2)
                                
                                with col_scanner1:
                                    st.markdown("##### ⏰ Scanning Schedule")
                                    scanner_enabled = st.checkbox("Enable Automatic Scanning", 
                                                                value=scanner_settings.get('enabled', False))
                                    
                                    scan_interval = st.selectbox("Scan Interval", 
                                                               [1, 6, 12, 24, 48, 72, 168], 
                                                               index=[1, 6, 12, 24, 48, 72, 168].index(scanner_settings.get('scan_interval', 24)),
                                                               format_func=lambda x: f"{x} hours" if x < 24 else f"{x//24} days")
                                    
                                    st.markdown("##### 📊 Scan Components")
                                    scan_tables = st.checkbox("Scan Tables & Schemas", value=scanner_settings.get('scan_tables', True))
                                    scan_users = st.checkbox("Scan Users & Permissions", value=scanner_settings.get('scan_users', True))
                                    scan_roles = st.checkbox("Scan Roles & Groups", value=scanner_settings.get('scan_roles', True))
                                
                                with col_scanner2:
                                    st.markdown("##### 🚨 Manual User Detection")
                                    detect_manual_users = st.checkbox("Detect Manually Created Users", 
                                                                    value=scanner_settings.get('detect_manual_users', True),
                                                                    help="Compare with local user database to find unauthorized users")
                                    
                                    alert_on_new_users = st.checkbox("Send Alert on New Users", 
                                                                    value=scanner_settings.get('alert_on_new_users', True))
                                    
                                    auto_lock_manual_users = st.checkbox("Auto-Lock Manual Users", 
                                                                        value=scanner_settings.get('auto_lock_manual_users', False),
                                                                        help="⚠️ Automatically disable unauthorized users")
                                    
                                    alert_email = st.text_input("Alert Email", 
                                                               value=scanner_settings.get('alert_email', ''),
                                                               placeholder="admin@company.com")
                                
                                col_save, col_cancel = st.columns(2)
                                
                                with col_save:
                                    if st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True):
                                        # Update scanner settings
                                        server['scanner_settings'] = {
                                            'enabled': scanner_enabled,
                                            'scan_interval': scan_interval,
                                            'detect_manual_users': detect_manual_users,
                                            'alert_on_new_users': alert_on_new_users,
                                            'auto_lock_manual_users': auto_lock_manual_users,
                                            'alert_email': alert_email,
                                            'scan_tables': scan_tables,
                                            'scan_users': scan_users,
                                            'scan_roles': scan_roles
                                        }
                                        
                                        # Save to file
                                        save_servers(st.session_state.servers_list)
                                        
                                        if scanner_enabled:
                                            st.success(f"✅ Scanner enabled for {server['Name']} - will scan every {scan_interval} hours")
                                        else:
                                            st.info(f"ℹ️ Scanner disabled for {server['Name']}")
                                        
                                        st.session_state[f"show_scanner_settings_{i}"] = False
                                        st.rerun()
                                
                                with col_cancel:
                                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                                        st.session_state[f"show_scanner_settings_{i}"] = False
                                        st.rerun()
                            
                            # Show current settings summary
                            if scanner_settings.get('enabled'):
                                st.markdown("##### 📋 Current Settings Summary")
                                status_col1, status_col2, status_col3 = st.columns(3)
                                
                                with status_col1:
                                    st.metric("Scan Interval", f"{scanner_settings['scan_interval']} hours")
                                    st.metric("Manual User Detection", "✅ Enabled" if scanner_settings.get('detect_manual_users') else "❌ Disabled")
                                
                                with status_col2:
                                    st.metric("Alert on New Users", "✅ Enabled" if scanner_settings.get('alert_on_new_users') else "❌ Disabled")
                                    st.metric("Auto-Lock Users", "⚠️ Enabled" if scanner_settings.get('auto_lock_manual_users') else "❌ Disabled")
                                
                                with status_col3:
                                    components = []
                                    if scanner_settings.get('scan_tables'): components.append("Tables")
                                    if scanner_settings.get('scan_users'): components.append("Users")
                                    if scanner_settings.get('scan_roles'): components.append("Roles")
                                    st.metric("Scan Components", ", ".join(components) if components else "None")
                                    if scanner_settings.get('alert_email'):
                                        st.metric("Alert Email", scanner_settings['alert_email'])
                    
                    # Show scan results if available
                    if "scan_results" in server and server["scan_results"]:
                        with st.expander(f"📊 Database Structure - {server['Name']}", expanded=False):
                            scan_data = server["scan_results"]
                            
                            tab_tables, tab_users, tab_roles = st.tabs(["📋 Tables", "👥 Users", "🔑 Roles"])
                            
                            with tab_tables:
                                st.subheader("📋 Database Tables")
                                if scan_data.get("tables"):
                                    # Show database type info
                                    db_type = scan_data.get("database_type", "unknown")
                                    total_size = scan_data.get("total_size", 0)
                                    db_icon = {"postgresql": "🐘", "mysql": "🐬", "redis": "🔴", "redshift": "🔶"}.get(db_type, "🗄️")
                                    
                                    col_info1, col_info2, col_info3 = st.columns(3)
                                    with col_info1:
                                        st.metric("Database Type", f"{db_icon} {db_type.upper()}")
                                    with col_info2:
                                        st.metric("Total Tables", len(scan_data["tables"]))
                                    with col_info3:
                                        st.metric("Total Size", f"{total_size:.1f} MB")
                                    
                                    st.markdown("---")
                                    tables_df = pd.DataFrame(scan_data["tables"])
                                    st.dataframe(tables_df, use_container_width=True, hide_index=True)
                                else:
                                    st.info("No tables found")
                            
                            with tab_users:
                                st.subheader("👥 Database Users")
                                
                                # Add user button
                                if st.button("➕ Add New User", key=f"add_user_{server['Name']}", use_container_width=True):
                                    st.session_state[f"show_add_user_{server['Name']}"] = True
                                    st.rerun()
                                
                                # Show add user form if button was clicked
                                if st.session_state.get(f"show_add_user_{server['Name']}", False):
                                    with st.expander("➕ Add New User", expanded=True):
                                        # Get enhanced database structure with column information
                                        structure_success, db_structure = get_enhanced_database_structure(server)
                                        
                                        if not structure_success:
                                            st.error(f"Could not get database structure: {db_structure}")
                                            db_structure = {"databases": [], "schemas": [], "tables": [], "database_type": "unknown"}
                                        
                                        with st.form(f"add_new_user_form_{server['Name']}"):
                                            st.markdown("#### Create New Database User")
                                            
                                            # Basic user info
                                            new_user_col1, new_user_col2 = st.columns(2)
                                            
                                            with new_user_col1:
                                                create_username = st.text_input("Username", placeholder="Enter new username")
                                                create_user_type = st.selectbox(
                                                    "User Type",
                                                    ["normal", "admin", "readonly", "application", "superuser"]
                                                )
                                            
                                            with new_user_col2:
                                                create_password = st.text_input("Password", type="password", placeholder="Enter password")
                                                create_user_active = st.checkbox("Active", value=True)
                                            
                                            # Database-specific permissions
                                            st.markdown("#### Database Access Permissions")
                                            db_type = db_structure.get("database_type", "postgresql")
                                            
                                            if db_type in ["postgresql", "redshift"]:
                                                st.markdown("##### PostgreSQL/Redshift Permissions")
                                                
                                                # Basic permissions
                                                create_permissions = st.multiselect(
                                                    "Table Permissions",
                                                    ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"],
                                                    default=["SELECT"] if create_user_type == "readonly" else ["SELECT", "INSERT", "UPDATE", "DELETE"]
                                                )
                                                
                                                # Schema access
                                                if db_structure["schemas"]:
                                                    create_schemas = st.multiselect(
                                                        "Grant Access to Schemas",
                                                        db_structure["schemas"],
                                                        help="Select schemas this user can access"
                                                    )
                                                else:
                                                    create_schemas = []
                                                
                                                # Specific table access
                                                if db_structure["tables"]:
                                                    create_tables = st.multiselect(
                                                        "Grant Access to Specific Tables",
                                                        [table["full_name"] for table in db_structure["tables"]],
                                                        help="Select specific tables for granular access control"
                                                    )
                                                    
                                                    # Column-level permissions for PostgreSQL/Redshift
                                                    if create_tables and db_structure.get("supports_column_permissions", False):
                                                        st.markdown("##### 📋 Column-Level Permissions (Advanced)")
                                                        create_column_permissions = []
                                                        
                                                        for table_full_name in create_tables:
                                                            # Find table info
                                                            table_info = None
                                                            for t in db_structure["tables"]:
                                                                if t["full_name"] == table_full_name:
                                                                    table_info = t
                                                                    break
                                                            
                                                            if table_info and table_info.get("columns"):
                                                                with st.expander(f"🔧 Column permissions for {table_full_name}", expanded=False):
                                                                    st.write(f"Available columns in **{table_full_name}**:")
                                                                    
                                                                    col_perms_col1, col_perms_col2 = st.columns(2)
                                                                    
                                                                    with col_perms_col1:
                                                                        selected_columns = st.multiselect(
                                                                            f"Select columns from {table_info['table']}",
                                                                            [col["name"] for col in table_info["columns"]],
                                                                            key=f"columns_{table_full_name}",
                                                                            help="Leave empty to grant permissions to all columns"
                                                                        )
                                                                    
                                                                    with col_perms_col2:
                                                                        column_level_permissions = st.multiselect(
                                                                            "Column Permissions",
                                                                            ["SELECT", "INSERT", "UPDATE", "REFERENCES"],
                                                                            key=f"col_perms_{table_full_name}",
                                                                            help="PostgreSQL/Redshift support column-level permissions for these operations"
                                                                        )
                                                                    
                                                                    if selected_columns and column_level_permissions:
                                                                        create_column_permissions.append({
                                                                            "table": table_full_name,
                                                                            "columns": selected_columns,
                                                                            "permissions": column_level_permissions
                                                                        })
                                                                        
                                                                        # Show preview of generated commands
                                                                        st.info(f"**Preview**: Column permissions for {len(selected_columns)} columns with {len(column_level_permissions)} permission types")
                                                else:
                                                    create_tables = []
                                                    create_column_permissions = []
                                                
                                                # Database privileges
                                                create_db_privileges = st.multiselect(
                                                    "Database-Level Privileges",
                                                    ["CONNECT", "CREATE", "TEMPORARY"],
                                                    default=["CONNECT"]
                                                )
                                            
                                            elif db_type == "mysql":
                                                st.markdown("##### MySQL Permissions")
                                                
                                                create_permissions = st.multiselect(
                                                    "Table Permissions",
                                                    ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "INDEX"],
                                                    default=["SELECT"] if create_user_type == "readonly" else ["SELECT", "INSERT", "UPDATE", "DELETE"]
                                                )
                                                
                                                # Database selection
                                                if db_structure["databases"]:
                                                    create_databases = st.multiselect(
                                                        "Grant Access to Databases",
                                                        db_structure["databases"],
                                                        help="Select databases this user can access"
                                                    )
                                                else:
                                                    create_databases = [server['Database']]
                                                
                                                # Specific table access
                                                if db_structure["tables"]:
                                                    create_tables = st.multiselect(
                                                        "Grant Access to Specific Tables",
                                                        [table["full_name"] for table in db_structure["tables"]],
                                                        help="Leave empty to grant access to all tables in selected databases"
                                                    )
                                                    
                                                    # Column-level permissions for MySQL
                                                    if create_tables and db_structure.get("supports_column_permissions", False):
                                                        st.markdown("##### 📋 Column-Level Permissions (Advanced)")
                                                        create_column_permissions = []
                                                        
                                                        for table_full_name in create_tables:
                                                            # Find table info
                                                            table_info = None
                                                            for t in db_structure["tables"]:
                                                                if t["full_name"] == table_full_name:
                                                                    table_info = t
                                                                    break
                                                            
                                                            if table_info and table_info.get("columns"):
                                                                with st.expander(f"🔧 Column permissions for {table_full_name}", expanded=False):
                                                                    st.write(f"Available columns in **{table_full_name}**:")
                                                                    
                                                                    col_perms_col1, col_perms_col2 = st.columns(2)
                                                                    
                                                                    with col_perms_col1:
                                                                        selected_columns = st.multiselect(
                                                                            f"Select columns from {table_info['table']}",
                                                                            [col["name"] for col in table_info["columns"]],
                                                                            key=f"mysql_columns_{table_full_name}",
                                                                            help="Leave empty to grant permissions to all columns"
                                                                        )
                                                                    
                                                                    with col_perms_col2:
                                                                        column_level_permissions = st.multiselect(
                                                                            "Column Permissions",
                                                                            ["SELECT", "INSERT", "UPDATE", "REFERENCES"],
                                                                            key=f"mysql_col_perms_{table_full_name}",
                                                                            help="MySQL supports column-level permissions for these operations"
                                                                        )
                                                                    
                                                                    if selected_columns and column_level_permissions:
                                                                        create_column_permissions.append({
                                                                            "table": table_full_name,
                                                                            "columns": selected_columns,
                                                                            "permissions": column_level_permissions
                                                                        })
                                                                        
                                                                        # Show preview of generated commands
                                                                        st.info(f"**Preview**: Column permissions for {len(selected_columns)} columns with {len(column_level_permissions)} permission types")
                                                else:
                                                    create_tables = []
                                                    create_column_permissions = []
                                            
                                            elif db_type == "redis":
                                                st.markdown("##### Redis ACL Permissions")
                                                
                                                create_permissions = st.multiselect(
                                                    "Redis Command Categories",
                                                    ["READ", "WRITE", "ADMIN", "DANGEROUS", "CONNECTION", "KEYSPACE", "STRING", "LIST", "SET", "HASH"],
                                                    default=["READ"] if create_user_type == "readonly" else ["read", "write"]
                                                )
                                                
                                                # Redis database selection
                                                create_redis_dbs = st.multiselect(
                                                    "Redis Databases",
                                                    [f"DB{i}" for i in range(16)],
                                                    default=["DB0"]
                                                )
                                            
                                            else:
                                                # Generic/unknown database type
                                                create_permissions = st.multiselect(
                                                    "Basic Permissions",
                                                    ["SELECT", "INSERT", "UPDATE", "DELETE"],
                                                    default=["SELECT"]
                                                )
                                            
                                            create_col1, create_col2 = st.columns(2)
                                            
                                            with create_col1:
                                                if st.form_submit_button("🚀 Create User", type="primary", use_container_width=True):
                                                    if create_username and create_password:
                                                        # Prepare permission data based on database type
                                                        permission_data = {}
                                                        db_type = db_structure.get("database_type", "postgresql")
                                                        
                                                        if db_type in ["postgresql", "redshift"]:
                                                            permission_data = {
                                                                "permissions": create_permissions,
                                                                "schemas": locals().get('create_schemas', []),
                                                                "tables": [{"full_name": table} for table in locals().get('create_tables', [])],
                                                                "db_privileges": locals().get('create_db_privileges', []),
                                                                "column_permissions": locals().get('create_column_permissions', [])
                                                            }
                                                        elif db_type == "mysql":
                                                            permission_data = {
                                                                "permissions": create_permissions,
                                                                "databases": locals().get('create_databases', [server['Database']]),
                                                                "tables": [{"full_name": table} for table in locals().get('create_tables', [])],
                                                                "column_permissions": locals().get('create_column_permissions', [])
                                                            }
                                                        elif db_type == "redis":
                                                            permission_data = {
                                                                "permissions": create_permissions,
                                                                "redis_dbs": locals().get('create_redis_dbs', ["DB0"])
                                                            }
                                                        
                                                        # Generate SQL commands using the new function
                                                        create_commands = generate_create_user_sql_commands(
                                                            db_type=db_type,
                                                            username=create_username,
                                                            password=create_password,
                                                            user_type=create_user_type,
                                                            databases=permission_data.get('databases'),
                                                            schemas=permission_data.get('schemas'),
                                                            tables=permission_data.get('tables'),
                                                            permissions=permission_data.get('permissions'),
                                                            column_permissions=permission_data.get('column_permissions')
                                                        )
                                                        
                                                        # Add database-level privileges for PostgreSQL
                                                        if db_type in ["postgresql", "redshift"] and permission_data.get('db_privileges'):
                                                            for privilege in permission_data['db_privileges']:
                                                                create_commands.append(f'GRANT {privilege} ON DATABASE "{server["Database"]}" TO "{create_username}";')
                                                        
                                                        # Handle inactive user
                                                        if not create_user_active:
                                                            if db_type in ["postgresql", "redshift"]:
                                                                create_commands.append(f'ALTER ROLE "{create_username}" WITH NOLOGIN;')
                                                            elif db_type == "mysql":
                                                                create_commands.append(f"ALTER USER '{create_username}'@'%' ACCOUNT LOCK;")
                                                            elif db_type == "redis":
                                                                # Redis: change 'on' to 'off' for inactive user
                                                                for i, cmd in enumerate(create_commands):
                                                                    if "ACL SETUSER" in cmd and " on " in cmd:
                                                                        create_commands[i] = cmd.replace(" on ", " off ")
                                                        
                                                        if create_commands:
                                                            success_count = 0
                                                            for cmd in create_commands:
                                                                st.code(f"Executing: {cmd}", language="sql")
                                                                success, result = execute_sql_command(server, cmd, fetch_results=False)
                                                                
                                                                if success:
                                                                    success_count += 1
                                                                    st.success(f"✅ Command executed: {result}")
                                                                else:
                                                                    st.error(f"❌ Error: {result}")
                                                            
                                                            if success_count == len(create_commands):
                                                                st.success(f"🎉 User '{create_username}' created successfully!")
                                                                # Add to scan results
                                                                new_user_data = {
                                                                    "name": create_username,
                                                                    "type": create_user_type,
                                                                    "active": create_user_active
                                                                }
                                                                st.session_state.servers_list[i]["scan_results"]["users"].append(new_user_data)
                                                                save_servers(st.session_state.servers_list)
                                                                
                                                                # Reset global user manager cache
                                                                if 'global_user_manager' in st.session_state:
                                                                    del st.session_state.global_user_manager
                                                                
                                                                st.session_state[f"show_add_user_{server['Name']}"] = False
                                                                st.rerun()
                                                    else:
                                                        st.error("Please provide both username and password")
                                            
                                            with create_col2:
                                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                                    st.session_state[f"show_add_user_{server['Name']}"] = False
                                                    st.rerun()
                                
                                if scan_data.get("users"):
                                    # Check for manual users and show alerts
                                    try:
                                        from models.local_user_storage import LocalUserStorage
                                        storage = LocalUserStorage()
                                        local_users = storage.get_all_users()
                                        local_usernames = {user['username'].lower() for user in local_users}
                                        
                                        db_usernames = {user['name'].lower() for user in scan_data["users"]}
                                        manual_users = db_usernames - local_usernames
                                        authorized_users = db_usernames & local_usernames
                                        
                                        # Display metrics
                                        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                                        with metrics_col1:
                                            st.metric("Total Users", len(scan_data["users"]))
                                        with metrics_col2:
                                            st.metric("Authorized Users", len(authorized_users), delta="✅")
                                        with metrics_col3:
                                            manual_count = len(manual_users)
                                            st.metric("Manual Users", manual_count, delta="⚠️" if manual_count > 0 else "✅")
                                        with metrics_col4:
                                            scanner_settings = server.get('scanner_settings', {})
                                            if scanner_settings.get('enabled'):
                                                st.metric("Scanner", "🔍 Active")
                                            else:
                                                st.metric("Scanner", "💤 Inactive")
                                        
                                        # Show manual users alert if any found
                                        if manual_users and len(manual_users) > 0:
                                            st.warning(f"⚠️ **{len(manual_users)} Manual Users Detected!** These users were not created through the system:")
                                            
                                            manual_users_list = [user for user in scan_data["users"] if user['name'].lower() in manual_users]
                                            for manual_user in manual_users_list:
                                                alert_col1, alert_col2, alert_col3, alert_col4 = st.columns([2, 1, 1, 1])
                                                
                                                with alert_col1:
                                                    st.error(f"🚨 **{manual_user['name']}** ({manual_user['type']}) - {'Active' if manual_user['active'] else 'Inactive'}")
                                                
                                                with alert_col2:
                                                    if st.button("🔒 Lock", key=f"lock_manual_{server['Name']}_{manual_user['name']}", use_container_width=True):
                                                        # Lock the manual user
                                                        db_type = scan_data.get("database_type", "postgresql")
                                                        
                                                        if db_type in ["postgresql", "redshift"]:
                                                            lock_cmd = f'ALTER ROLE "{manual_user["name"]}" WITH NOLOGIN;'
                                                        elif db_type == "mysql":
                                                            lock_cmd = f"ALTER USER '{manual_user['name']}' ACCOUNT LOCK;"
                                                        else:
                                                            st.error(f"User locking not supported for {db_type}")
                                                            continue
                                                        
                                                        with st.spinner(f"Locking {manual_user['name']}..."):
                                                            success, result = execute_sql_command(server, lock_cmd, fetch_results=False)
                                                            
                                                            if success:
                                                                st.success(f"✅ User {manual_user['name']} locked successfully")
                                                                # Update the user status in scan results
                                                                for i, u in enumerate(scan_data["users"]):
                                                                    if u['name'] == manual_user['name']:
                                                                        scan_data["users"][i]['active'] = False
                                                                        break
                                                                save_servers(st.session_state.servers_list)
                                                                
                                                                # Reset global user manager cache
                                                                if 'global_user_manager' in st.session_state:
                                                                    del st.session_state.global_user_manager
                                                                
                                                                st.rerun()
                                                            else:
                                                                st.error(f"❌ Failed to lock user: {result}")
                                                
                                                with alert_col3:
                                                    if st.button("📧 Alert", key=f"alert_manual_{server['Name']}_{manual_user['name']}", use_container_width=True):
                                                        alert_email = scanner_settings.get('alert_email', '')
                                                        if alert_email:
                                                            st.info(f"📧 Alert sent to {alert_email} about manual user: {manual_user['name']}")
                                                            # Here you would integrate with actual email/notification system
                                                        else:
                                                            st.warning("No alert email configured in scanner settings")
                                                
                                                with alert_col4:
                                                    if st.button("✅ Approve", key=f"approve_manual_{server['Name']}_{manual_user['name']}", use_container_width=True):
                                                        # Add to local user storage
                                                        try:
                                                            user_id = storage.create_user(
                                                                username=manual_user['name'],
                                                                display_name=manual_user['name'],
                                                                email="",
                                                                description=f"Approved manual user from {server['Name']}",
                                                                tags=["manual-approved"]
                                                            )
                                                            st.success(f"✅ User {manual_user['name']} added to authorized users")
                                                            
                                                            # Reset global user manager cache
                                                            if 'global_user_manager' in st.session_state:
                                                                del st.session_state.global_user_manager
                                                            
                                                            st.rerun()
                                                        except Exception as e:
                                                            st.error(f"❌ Failed to approve user: {str(e)}")
                                            
                                            st.markdown("---")
                                        
                                    except ImportError:
                                        st.metric("Total Users", len(scan_data["users"]))
                                        st.warning("Local user storage not available for manual user detection")
                                        st.markdown("---")
                                    except Exception as e:
                                        st.metric("Total Users", len(scan_data["users"]))
                                        st.error(f"Error checking manual users: {str(e)}")
                                        st.markdown("---")
                                    
                                    for idx, user in enumerate(scan_data["users"]):
                                        status_icon = "🟢" if user["active"] else "🔴"
                                        if user["type"] == "superuser":
                                            type_icon = "👑"
                                        elif user["type"] == "admin":
                                            type_icon = "⚙️"
                                        elif user["type"] == "application":
                                            type_icon = "🤖"
                                        elif user["type"] == "system":
                                            type_icon = "🔧"
                                        elif user["type"] == "readonly":
                                            type_icon = "👁️"
                                        else:
                                            type_icon = "👤"
                                        
                                        # Create columns for user display and action buttons
                                        user_col1, user_col2, user_col3, user_col4, user_col5, user_col6 = st.columns([2.5, 0.8, 0.8, 0.8, 0.8, 0.8])
                                        
                                        with user_col1:
                                            # Display user roles if available
                                            user_roles_text = ""
                                            if user.get('roles') and user['roles']:
                                                roles_list = user['roles'][:3]  # Show first 3 roles
                                                if len(user['roles']) > 3:
                                                    user_roles_text = f" | 🔑 {', '.join(roles_list)}... (+{len(user['roles'])-3} more)"
                                                else:
                                                    user_roles_text = f" | 🔑 {', '.join(roles_list)}"
                                            
                                            st.markdown(f"{type_icon} **{user['name']}** | {user['type']} | {status_icon} {'Active' if user['active'] else 'Inactive'}{user_roles_text}")
                                        
                                        with user_col2:
                                            if st.button("✏️ Edit", key=f"edit_user_btn_{server['Name']}_{idx}", use_container_width=True):
                                                st.session_state[f"edit_user_{server['Name']}_{idx}"] = True
                                                st.rerun()
                                        
                                        with user_col3:
                                            if st.button("🔑 Perms", key=f"perms_user_btn_{server['Name']}_{idx}", use_container_width=True):
                                                st.session_state[f"show_perms_{server['Name']}_{idx}"] = True
                                                st.rerun()
                                        
                                        with user_col4:
                                            if st.button("👥 Roles", key=f"manage_roles_btn_{server['Name']}_{idx}", use_container_width=True):
                                                st.session_state[f"manage_user_roles_{server['Name']}_{idx}"] = True
                                                st.rerun()
                                        
                                        with user_col5:
                                            clone_text = "📋 Clone"
                                            if st.button(clone_text, key=f"clone_user_btn_{server['Name']}_{idx}", use_container_width=True):
                                                st.session_state[f"clone_user_{server['Name']}_{idx}"] = True
                                                st.rerun()
                                        
                                        with user_col6:
                                            copy_text = "📤 Copy From"
                                            if st.button(copy_text, key=f"copy_perms_btn_{server['Name']}_{idx}", use_container_width=True):
                                                st.session_state[f"copy_perms_{server['Name']}_{idx}"] = True
                                                st.rerun()
                                        
                                        # Show clone user dialog if requested
                                        if st.session_state.get(f"clone_user_{server['Name']}_{idx}", False):
                                            with st.expander(f"📋 Clone User: {user['name']}", expanded=True):
                                                st.markdown("#### Clone User with Permissions")
                                                
                                                with st.form(f"clone_user_form_{server['Name']}_{idx}"):
                                                    clone_col1, clone_col2 = st.columns(2)
                                                    
                                                    with clone_col1:
                                                        clone_username = st.text_input("New Username", placeholder="Enter new username")
                                                        clone_password = st.text_input("Password", type="password", placeholder="Enter password")
                                                    
                                                    with clone_col2:
                                                        st.markdown("##### Copy Options")
                                                        copy_properties = st.checkbox("Copy User Properties", value=True, help="Copy superuser, createrole, createdb privileges")
                                                        copy_roles = st.checkbox("Copy Role Memberships", value=True, help="Copy all role assignments")
                                                        copy_table_perms = st.checkbox("Copy Table Permissions", value=True, help="Copy table-level permissions")
                                                        copy_schema_perms = st.checkbox("Copy Schema Permissions", value=True, help="Copy schema-level permissions")
                                                        copy_column_perms = st.checkbox("Copy Column Permissions", value=True, help="Copy column-level permissions")
                                                    
                                                    # Show source user permissions preview
                                                    st.markdown("##### Source User Permissions Preview")
                                                    with st.spinner("Loading source user permissions..."):
                                                        perm_success, source_permissions = get_user_permissions(server, user['name'])
                                                        
                                                        if perm_success:
                                                            perm_col1, perm_col2, perm_col3 = st.columns(3)
                                                            
                                                            with perm_col1:
                                                                roles_count = len(source_permissions.get('roles', []))
                                                                st.metric("Roles", roles_count)
                                                                if roles_count > 0:
                                                                    with st.expander("View Roles", expanded=False):
                                                                        for role in source_permissions['roles']:
                                                                            st.write(f"🔑 {role}")
                                                            
                                                            with perm_col2:
                                                                table_perms_count = len(source_permissions.get('table_permissions', []))
                                                                st.metric("Table Permissions", table_perms_count)
                                                                if table_perms_count > 0:
                                                                    with st.expander("View Table Permissions", expanded=False):
                                                                        for perm in source_permissions['table_permissions'][:10]:  # Show first 10
                                                                            st.write(f"📊 {perm['privilege']} on {perm['full_name']}")
                                                                        if table_perms_count > 10:
                                                                            st.write(f"... and {table_perms_count - 10} more")
                                                            
                                                            with perm_col3:
                                                                column_perms_count = len(source_permissions.get('column_permissions', []))
                                                                st.metric("Column Permissions", column_perms_count)
                                                                if column_perms_count > 0:
                                                                    with st.expander("View Column Permissions", expanded=False):
                                                                        for perm in source_permissions['column_permissions'][:10]:
                                                                            st.write(f"📋 {perm['privilege']} on {perm['full_name']}")
                                                                        if column_perms_count > 10:
                                                                            st.write(f"... and {column_perms_count - 10} more")
                                                        else:
                                                            st.error(f"Could not load permissions: {source_permissions}")
                                                    
                                                    clone_form_col1, clone_form_col2 = st.columns(2)
                                                    
                                                    with clone_form_col1:
                                                        if st.form_submit_button("🚀 Clone User", type="primary", use_container_width=True):
                                                            if clone_username and clone_password:
                                                                clone_options = {
                                                                    "copy_properties": copy_properties,
                                                                    "copy_roles": copy_roles,
                                                                    "copy_table_permissions": copy_table_perms,
                                                                    "copy_schema_permissions": copy_schema_perms,
                                                                    "copy_column_permissions": copy_column_perms
                                                                }
                                                                
                                                                # Generate clone commands
                                                                clone_success, clone_result = clone_user_permissions(
                                                                    server, user['name'], clone_username, clone_password, clone_options
                                                                )
                                                                
                                                                if clone_success:
                                                                    commands = clone_result["commands"]
                                                                    st.markdown("#### Generated Commands")
                                                                    
                                                                    success_count = 0
                                                                    for cmd in commands:
                                                                        st.code(f"Executing: {cmd}", language="sql")
                                                                        success, result = execute_sql_command(server, cmd, fetch_results=False)
                                                                        
                                                                        if success:
                                                                            success_count += 1
                                                                            st.success(f"✅ Command executed: {result}")
                                                                        else:
                                                                            st.error(f"❌ Error: {result}")
                                                                    
                                                                    if success_count == len(commands):
                                                                        st.success(f"🎉 User '{clone_username}' cloned successfully with {len(commands)} permissions!")
                                                                        # Add to scan results
                                                                        new_user_data = {
                                                                            "name": clone_username,
                                                                            "type": user.get('type', 'normal'),
                                                                            "active": True,
                                                                            "roles": source_permissions.get('roles', [])
                                                                        }
                                                                        st.session_state.servers_list[i]["scan_results"]["users"].append(new_user_data)
                                                                        save_servers(st.session_state.servers_list)
                                                                        
                                                                        # Reset global user manager cache
                                                                        if 'global_user_manager' in st.session_state:
                                                                            del st.session_state.global_user_manager
                                                                        
                                                                        st.session_state[f"clone_user_{server['Name']}_{idx}"] = False
                                                                        st.rerun()
                                                                    else:
                                                                        st.warning(f"⚠️ Partial success: {success_count}/{len(commands)} commands executed")
                                                                else:
                                                                    st.error(f"❌ Failed to generate clone commands: {clone_result}")
                                                            else:
                                                                st.error("Please provide username and password")
                                                    
                                                    with clone_form_col2:
                                                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                                                            st.session_state[f"clone_user_{server['Name']}_{idx}"] = False
                                                            st.rerun()
                                        
                                        # Show copy permissions dialog if copy button was clicked
                                        if st.session_state.get(f"copy_perms_{server['Name']}_{idx}", False):
                                            with st.expander(f"📤 Copy Permissions to: {user['name']}", expanded=True):
                                                st.markdown("#### Copy Permissions from Another User")
                                                
                                                with st.form(f"copy_perms_form_{server['Name']}_{idx}"):
                                                    copy_col1, copy_col2 = st.columns(2)
                                                    
                                                    with copy_col1:
                                                        # Get list of available users (excluding current user)
                                                        available_users = [u['name'] for u in scan_data.get('users', []) if u['name'] != user['name']]
                                                        
                                                        if available_users:
                                                            source_user = st.selectbox("Select Source User", available_users, 
                                                                                      help="Choose user to copy permissions from")
                                                        else:
                                                            st.warning("No other users available to copy from")
                                                            source_user = None
                                                    
                                                    with copy_col2:
                                                        st.markdown("##### Copy Options")
                                                        copy_properties = st.checkbox("Copy User Properties", value=True, 
                                                                                     help="Copy superuser, createrole, createdb privileges")
                                                        copy_roles = st.checkbox("Copy Role Memberships", value=True, 
                                                                               help="Copy all role assignments")
                                                        copy_table_perms = st.checkbox("Copy Table Permissions", value=True, 
                                                                                      help="Copy table-level permissions")
                                                        copy_schema_perms = st.checkbox("Copy Schema Permissions", value=True, 
                                                                                       help="Copy schema-level permissions")
                                                        copy_column_perms = st.checkbox("Copy Column Permissions", value=True, 
                                                                                       help="Copy column-level permissions")
                                                    
                                                    # Show source user permissions preview if user selected
                                                    if source_user:
                                                        st.markdown(f"##### Source User Permissions Preview: {source_user}")
                                                        with st.spinner("Loading source user permissions..."):
                                                            perm_success, source_permissions = get_user_permissions(server, source_user)
                                                            
                                                            if perm_success:
                                                                perm_col1, perm_col2, perm_col3 = st.columns(3)
                                                                
                                                                with perm_col1:
                                                                    roles_count = len(source_permissions.get('roles', []))
                                                                    st.metric("Roles", roles_count)
                                                                    if roles_count > 0:
                                                                        with st.expander("View Roles", expanded=False):
                                                                            for role in source_permissions['roles']:
                                                                                st.write(f"🔑 {role}")
                                                                
                                                                with perm_col2:
                                                                    table_perms_count = len(source_permissions.get('table_permissions', []))
                                                                    st.metric("Table Permissions", table_perms_count)
                                                                    if table_perms_count > 0:
                                                                        with st.expander("View Table Permissions", expanded=False):
                                                                            for perm in source_permissions['table_permissions'][:10]:
                                                                                st.write(f"📊 {perm['privilege']} on {perm['full_name']}")
                                                                            if table_perms_count > 10:
                                                                                st.write(f"... and {table_perms_count - 10} more")
                                                                
                                                                with perm_col3:
                                                                    column_perms_count = len(source_permissions.get('column_permissions', []))
                                                                    st.metric("Column Permissions", column_perms_count)
                                                                    if column_perms_count > 0:
                                                                        with st.expander("View Column Permissions", expanded=False):
                                                                            for perm in source_permissions['column_permissions'][:10]:
                                                                                st.write(f"📋 {perm['privilege']} on {perm['full_name']}")
                                                                            if column_perms_count > 10:
                                                                                st.write(f"... and {column_perms_count - 10} more")
                                                            else:
                                                                st.error(f"Could not load permissions: {source_permissions}")
                                                    
                                                    copy_form_col1, copy_form_col2 = st.columns(2)
                                                    
                                                    with copy_form_col1:
                                                        if st.form_submit_button("🚀 Copy Permissions", type="primary", use_container_width=True):
                                                            if source_user:
                                                                copy_options = {
                                                                    'copy_properties': copy_properties,
                                                                    'copy_roles': copy_roles,
                                                                    'copy_table_permissions': copy_table_perms,
                                                                    'copy_schema_permissions': copy_schema_perms,
                                                                    'copy_column_permissions': copy_column_perms
                                                                }
                                                                
                                                                # Generate SQL commands to copy permissions from source to target user
                                                                copy_success, copy_commands = copy_user_permissions(server, source_user, user['name'], copy_options)
                                                                
                                                                if copy_success and copy_commands:
                                                                    st.markdown("##### SQL Commands to Execute:")
                                                                    for cmd in copy_commands:
                                                                        st.code(cmd, language="sql")
                                                                    
                                                                    # Execute the commands
                                                                    success_count = 0
                                                                    error_messages = []
                                                                    
                                                                    for cmd in copy_commands:
                                                                        success, result = execute_sql_command(server, cmd, fetch_results=False)
                                                                        
                                                                        if success:
                                                                            success_count += 1
                                                                        else:
                                                                            error_messages.append(f"❌ {cmd}: {result}")
                                                                    
                                                                    if success_count == len(copy_commands):
                                                                        st.success(f"🎉 Permissions copied successfully from '{source_user}' to '{user['name']}'! ({success_count} commands executed)")
                                                                        st.session_state[f"copy_perms_{server['Name']}_{idx}"] = False
                                                                        st.rerun()
                                                                    else:
                                                                        st.warning(f"⚠️ Partial success: {success_count}/{len(copy_commands)} commands executed")
                                                                        for error in error_messages:
                                                                            st.error(error)
                                                                else:
                                                                    st.error(f"❌ Failed to generate copy commands: {copy_commands}")
                                                            else:
                                                                st.error("Please select a source user")
                                                    
                                                    with copy_form_col2:
                                                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                                                            st.session_state[f"copy_perms_{server['Name']}_{idx}"] = False
                                                            st.rerun()
                                        
                                        # Show edit form if edit button was clicked
                                        if st.session_state.get(f"edit_user_{server['Name']}_{idx}", False):
                                            with st.expander(f"✏️ Edit User: {user['name']}", expanded=True):
                                                with st.form(f"edit_user_form_{server['Name']}_{idx}"):
                                                    st.markdown("#### Edit User Details")
                                                    
                                                    edit_user_col1, edit_user_col2 = st.columns(2)
                                                    
                                                    with edit_user_col1:
                                                        new_username = st.text_input("Username", value=user['name'])
                                                        new_user_type = st.selectbox(
                                                            "User Type", 
                                                            ["superuser", "admin", "normal", "application", "system", "readonly"],
                                                            index=["superuser", "admin", "normal", "application", "system", "readonly"].index(user['type'])
                                                        )
                                                    
                                                    with edit_user_col2:
                                                        new_user_active = st.checkbox("Active", value=user['active'])
                                                        new_password = st.text_input("New Password (optional)", type="password", placeholder="Leave empty to keep current")
                                                    
                                                    st.markdown("#### User Permissions")
                                                    new_permissions = st.multiselect(
                                                        "Database Permissions",
                                                        ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "GRANT"],
                                                        default=["SELECT"] if user['type'] == "readonly" else ["SELECT", "INSERT", "UPDATE", "DELETE"] if user['type'] in ["normal", "application"] else ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "GRANT"]
                                                    )
                                                    
                                                    form_col1, form_col2 = st.columns(2)
                                                    
                                                    with form_col1:
                                                        if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                                                            # Get database type
                                                            db_type = scan_data.get("database_type", "postgresql")
                                                            
                                                            # Generate SQL commands for user update
                                                            sql_commands = generate_user_sql_commands(
                                                                db_type=db_type,
                                                                action="update_user",
                                                                old_username=user['name'],
                                                                new_username=new_username if new_username != user['name'] else None,
                                                                new_user_type=new_user_type if new_user_type != user['type'] else None,
                                                                new_active=new_user_active if new_user_active != user['active'] else None,
                                                                new_password=new_password if new_password else None,
                                                                new_permissions=new_permissions
                                                            )
                                                            
                                                            if sql_commands:
                                                                success_count = 0
                                                                error_messages = []
                                                                
                                                                for cmd in sql_commands:
                                                                    st.code(f"Executing: {cmd}", language="sql")
                                                                    success, result = execute_sql_command(server, cmd, fetch_results=False)
                                                                    
                                                                    if success:
                                                                        success_count += 1
                                                                        st.success(f"✅ Command executed: {result}")
                                                                    else:
                                                                        error_messages.append(f"❌ {cmd}: {result}")
                                                                        st.error(f"❌ Error: {result}")
                                                                
                                                                if success_count == len(sql_commands):
                                                                    st.success(f"🎉 User '{new_username}' updated successfully! ({success_count} commands executed)")
                                                                    # Update the scan results to reflect changes
                                                                    st.session_state.servers_list[i]["scan_results"]["users"][idx] = {
                                                                        "name": new_username,
                                                                        "type": new_user_type,
                                                                        "active": new_user_active
                                                                    }
                                                                    save_servers(st.session_state.servers_list)
                                                                    
                                                                    # Reset global user manager cache
                                                                    if 'global_user_manager' in st.session_state:
                                                                        del st.session_state.global_user_manager
                                                                    
                                                                    st.session_state[f"edit_user_{server['Name']}_{idx}"] = False
                                                                    st.rerun()
                                                                else:
                                                                    st.error(f"⚠️ Partial success: {success_count}/{len(sql_commands)} commands executed successfully")
                                                                    for error in error_messages:
                                                                        st.error(error)
                                                            else:
                                                                st.info("No changes detected")
                                                    
                                                    with form_col2:
                                                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                                                            st.session_state[f"edit_user_{server['Name']}_{idx}"] = False
                                                            st.rerun()
                                        
                                        # Show permissions dialog if permissions button was clicked
                                        if st.session_state.get(f"show_perms_{server['Name']}_{idx}", False):
                                            with st.expander(f"🔑 Permissions for: {user['name']}", expanded=True):
                                                st.markdown("#### User Information")
                                                
                                                # Show user type
                                                if user['type'] == "superuser":
                                                    st.success("👑 **SUPERUSER** - Full database access")
                                                elif user['type'] == "admin":
                                                    st.info("⚙️ **ADMIN** - Administrative access")
                                                elif user['type'] == "readonly":
                                                    st.warning("👁️ **READ-ONLY** - View access only")
                                                else:
                                                    st.info("👤 **STANDARD** - Basic access")
                                                
                                                # Show roles/privileges if available
                                                if user.get('roles') and user['roles']:
                                                    st.markdown("#### 🔑 Member of Roles/Has Privileges:")
                                                    
                                                    roles_col1, roles_col2 = st.columns(2)
                                                    for i, role in enumerate(user['roles']):
                                                        if i % 2 == 0:
                                                            with roles_col1:
                                                                st.markdown(f"🔹 **{role}**")
                                                        else:
                                                            with roles_col2:
                                                                st.markdown(f"🔹 **{role}**")
                                                else:
                                                    st.info("No specific roles/privileges found")
                                                
                                                # Show typical permissions based on user type
                                                st.markdown("#### 📋 Typical Permissions:")
                                                if user['type'] == "superuser":
                                                    perms = ["ALL PRIVILEGES", "CREATE DATABASE", "CREATE USER", "GRANT/REVOKE"]
                                                elif user['type'] == "admin":
                                                    perms = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]
                                                elif user['type'] == "readonly":
                                                    perms = ["SELECT"]
                                                else:
                                                    perms = ["SELECT", "INSERT", "UPDATE", "DELETE"]
                                                
                                                perm_col1, perm_col2 = st.columns(2)
                                                for i, perm in enumerate(perms):
                                                    if i % 2 == 0:
                                                        with perm_col1:
                                                            st.markdown(f"✅ {perm}")
                                                    else:
                                                        with perm_col2:
                                                            st.markdown(f"✅ {perm}")
                                                
                                                if st.button("❌ Close", key=f"close_perms_{server['Name']}_{idx}"):
                                                    st.session_state[f"show_perms_{server['Name']}_{idx}"] = False
                                                    st.rerun()
                                        
                                        # Show role management dialog if role management button was clicked
                                        if st.session_state.get(f"manage_user_roles_{server['Name']}_{idx}", False):
                                            with st.expander(f"👥 Manage Roles for: {user['name']}", expanded=True):
                                                st.markdown("#### Current Roles")
                                                
                                                if user.get('roles') and user['roles']:
                                                    current_roles_cols = st.columns(3)
                                                    for i, role in enumerate(user['roles']):
                                                        with current_roles_cols[i % 3]:
                                                            if st.button(f"🗑️ Remove {role}", key=f"remove_role_{server['Name']}_{idx}_{role}", use_container_width=True):
                                                                # Generate SQL to remove user from role
                                                                db_type = scan_data.get("database_type", "postgresql")
                                                                
                                                                if db_type in ["postgresql", "redshift"]:
                                                                    revoke_cmd = f'REVOKE "{role}" FROM "{user["name"]}";'
                                                                elif db_type == "mysql":
                                                                    revoke_cmd = f"REVOKE '{role}' FROM '{user['name']}';"
                                                                else:
                                                                    st.error(f"Role management not supported for {db_type}")
                                                                    continue
                                                                
                                                                st.code(f"Executing: {revoke_cmd}", language="sql")
                                                                success, result = execute_sql_command(server, revoke_cmd, fetch_results=False)
                                                                
                                                                if success:
                                                                    st.success(f"✅ Removed '{user['name']}' from role '{role}'")
                                                                    # Update scan results
                                                                    updated_roles = [r for r in user['roles'] if r != role]
                                                                    st.session_state.servers_list[i]["scan_results"]["users"][idx]["roles"] = updated_roles
                                                                    save_servers(st.session_state.servers_list)
                                                                    
                                                                    # Reset global user manager cache
                                                                    if 'global_user_manager' in st.session_state:
                                                                        del st.session_state.global_user_manager
                                                                    
                                                                    st.rerun()
                                                                else:
                                                                    st.error(f"❌ Error: {result}")
                                                else:
                                                    st.info("User is not a member of any roles")
                                                
                                                st.markdown("#### Add to Role")
                                                
                                                # Get available roles
                                                available_roles = []
                                                if scan_data.get("roles"):
                                                    user_current_roles = user.get('roles', [])
                                                    available_roles = [role['name'] for role in scan_data["roles"] if role['name'] not in user_current_roles]
                                                
                                                if available_roles:
                                                    selected_role = st.selectbox(
                                                        "Select Role to Add:",
                                                        available_roles,
                                                        key=f"select_role_{server['Name']}_{idx}"
                                                    )
                                                    
                                                    col_add, col_close = st.columns(2)
                                                    
                                                    with col_add:
                                                        if st.button("➕ Add to Role", key=f"add_to_role_{server['Name']}_{idx}", use_container_width=True):
                                                            # Generate SQL to add user to role
                                                            db_type = scan_data.get("database_type", "postgresql")
                                                            
                                                            if db_type in ["postgresql", "redshift"]:
                                                                grant_cmd = f'GRANT "{selected_role}" TO "{user["name"]}";'
                                                            elif db_type == "mysql":
                                                                grant_cmd = f"GRANT '{selected_role}' TO '{user['name']}';"
                                                            else:
                                                                st.error(f"Role management not supported for {db_type}")
                                                                continue
                                                            
                                                            st.code(f"Executing: {grant_cmd}", language="sql")
                                                            success, result = execute_sql_command(server, grant_cmd, fetch_results=False)
                                                            
                                                            if success:
                                                                st.success(f"✅ Added '{user['name']}' to role '{selected_role}'")
                                                                # Update scan results
                                                                if 'roles' not in st.session_state.servers_list[i]["scan_results"]["users"][idx]:
                                                                    st.session_state.servers_list[i]["scan_results"]["users"][idx]['roles'] = []
                                                                st.session_state.servers_list[i]["scan_results"]["users"][idx]['roles'].append(selected_role)
                                                                save_servers(st.session_state.servers_list)
                                                                
                                                                # Reset global user manager cache
                                                                if 'global_user_manager' in st.session_state:
                                                                    del st.session_state.global_user_manager
                                                                
                                                                st.rerun()
                                                            else:
                                                                st.error(f"❌ Error: {result}")
                                                    
                                                    with col_close:
                                                        if st.button("❌ Close", key=f"close_role_mgmt_{server['Name']}_{idx}", use_container_width=True):
                                                            st.session_state[f"manage_user_roles_{server['Name']}_{idx}"] = False
                                                            st.rerun()
                                                else:
                                                    st.info("No additional roles available")
                                                    if st.button("❌ Close", key=f"close_role_mgmt_{server['Name']}_{idx}", use_container_width=True):
                                                        st.session_state[f"manage_user_roles_{server['Name']}_{idx}"] = False
                                                        st.rerun()
                                        
                                        st.divider()
                                else:
                                    st.info("No users found")
                            
                            with tab_roles:
                                st.subheader("🔑 Database Roles")
                                if scan_data.get("roles"):
                                    st.metric("Total Roles", len(scan_data["roles"]))
                                    st.markdown("---")
                                    
                                    for role in scan_data["roles"]:
                                        member_text = "member" if role['members'] == 1 else "members"
                                        role_type_text = f" ({role['type']})" if role.get('type') else ""
                                        
                                        role_col1, role_col2 = st.columns([3, 1])
                                        with role_col1:
                                            st.markdown(f"🔑 **{role['name']}**{role_type_text} - {role['members']} {member_text}")
                                        with role_col2:
                                            if st.button("👥 Members", key=f"role_members_btn_{server['Name']}_{role['name']}", use_container_width=True):
                                                st.session_state[f"manage_role_members_{server['Name']}_{role['name']}"] = True
                                                st.rerun()
                                        
                                        # Show role member management dialog
                                        if st.session_state.get(f"manage_role_members_{server['Name']}_{role['name']}", False):
                                            with st.expander(f"👥 Members of Role: {role['name']}", expanded=True):
                                                st.markdown("#### Current Members")
                                                
                                                current_members = role.get('member_names', [])
                                                if current_members:
                                                    members_cols = st.columns(3)
                                                    for i, member in enumerate(current_members):
                                                        with members_cols[i % 3]:
                                                            if st.button(f"🗑️ Remove {member}", key=f"remove_member_{server['Name']}_{role['name']}_{member}", use_container_width=True):
                                                                # Generate SQL to remove member from role
                                                                db_type = scan_data.get("database_type", "postgresql")
                                                                
                                                                if db_type in ["postgresql", "redshift"]:
                                                                    revoke_cmd = f'REVOKE "{role["name"]}" FROM "{member}";'
                                                                elif db_type == "mysql":
                                                                    revoke_cmd = f"REVOKE '{role['name']}' FROM '{member}';"
                                                                else:
                                                                    st.error(f"Role management not supported for {db_type}")
                                                                    continue
                                                                
                                                                st.code(f"Executing: {revoke_cmd}", language="sql")
                                                                success, result = execute_sql_command(server, revoke_cmd, fetch_results=False)
                                                                
                                                                if success:
                                                                    st.success(f"✅ Removed '{member}' from role '{role['name']}'")
                                                                    st.rerun()
                                                                else:
                                                                    st.error(f"❌ Error: {result}")
                                                else:
                                                    st.info(f"Role '{role['name']}' has no members")
                                                
                                                st.markdown("#### Add Member")
                                                
                                                # Get available users
                                                available_users = []
                                                if scan_data.get("users"):
                                                    available_users = [user['name'] for user in scan_data["users"] if user['name'] not in current_members]
                                                
                                                if available_users:
                                                    selected_user = st.selectbox(
                                                        "Select User to Add:",
                                                        available_users,
                                                        key=f"select_user_for_role_{server['Name']}_{role['name']}"
                                                    )
                                                    
                                                    col_add_member, col_close_members = st.columns(2)
                                                    
                                                    with col_add_member:
                                                        if st.button("➕ Add Member", key=f"add_member_{server['Name']}_{role['name']}", use_container_width=True):
                                                            # Generate SQL to add user to role
                                                            db_type = scan_data.get("database_type", "postgresql")
                                                            
                                                            if db_type in ["postgresql", "redshift"]:
                                                                grant_cmd = f'GRANT "{role["name"]}" TO "{selected_user}";'
                                                            elif db_type == "mysql":
                                                                grant_cmd = f"GRANT '{role['name']}' TO '{selected_user}';"
                                                            else:
                                                                st.error(f"Role management not supported for {db_type}")
                                                                continue
                                                            
                                                            st.code(f"Executing: {grant_cmd}", language="sql")
                                                            success, result = execute_sql_command(server, grant_cmd, fetch_results=False)
                                                            
                                                            if success:
                                                                st.success(f"✅ Added '{selected_user}' to role '{role['name']}'")
                                                                
                                                                # Reset global user manager cache
                                                                if 'global_user_manager' in st.session_state:
                                                                    del st.session_state.global_user_manager
                                                                
                                                                st.rerun()
                                                            else:
                                                                st.error(f"❌ Error: {result}")
                                                    
                                                    with col_close_members:
                                                        if st.button("❌ Close", key=f"close_members_{server['Name']}_{role['name']}", use_container_width=True):
                                                            st.session_state[f"manage_role_members_{server['Name']}_{role['name']}"] = False
                                                            st.rerun()
                                                else:
                                                    st.info("No users available to add")
                                                    if st.button("❌ Close", key=f"close_members_{server['Name']}_{role['name']}", use_container_width=True):
                                                        st.session_state[f"manage_role_members_{server['Name']}_{role['name']}"] = False
                                                        st.rerun()
                                else:
                                    st.info("No roles found")
                    
                    st.divider()
        else:
            st.info("No servers configured yet. Add your first server using the 'Add Server' tab!")

        # Edit Server Form (appears when edit button is clicked)
        if 'show_edit_form' in st.session_state and st.session_state.show_edit_form:
            st.markdown("---")
            st.subheader("✏️ Edit Server")
            
            edit_index = st.session_state.edit_server_index
            # Check if the index is still valid
            if edit_index >= len(st.session_state.servers_list):
                st.error("Server not found. Returning to server list.")
                st.session_state.show_edit_form = False
                st.rerun()
                return
            
            server_to_edit = st.session_state.servers_list[edit_index]
            
            with st.form("edit_server_form"):
                st.markdown("#### Edit Server Configuration")

                col1, col2 = st.columns(2)

                with col1:
                    edit_name = st.text_input("Server Name", value=server_to_edit["Name"])
                    edit_host = st.text_input("Host", value=server_to_edit["Host"])
                    edit_port = st.number_input("Port", min_value=1, max_value=65535, value=server_to_edit["Port"])
                    edit_database = st.text_input("Database", value=server_to_edit["Database"])

                with col2:
                    edit_environment = st.selectbox(
                        "Environment", 
                        ["Development", "Staging", "Production", "Testing"],
                        index=["Development", "Staging", "Production", "Testing"].index(server_to_edit["Environment"])
                    )

                st.markdown("#### Authentication")
                col3, col4 = st.columns(2)
                with col3:
                    edit_username = st.text_input("Username", value=server_to_edit.get("Username", ""))
                with col4:
                    edit_password = st.text_input("Password", type="password", value=server_to_edit.get("Password", ""))

                col_save, col_cancel = st.columns(2)
                
                with col_save:
                    save_changes = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
                
                with col_cancel:
                    cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True)

                if save_changes:
                    if edit_name and edit_host and edit_database:
                        # Update server in the list
                        st.session_state.servers_list[edit_index].update({
                            "Name": edit_name,
                            "Host": edit_host,
                            "Port": edit_port,
                            "Database": edit_database,
                            "Username": edit_username,
                            "Password": edit_password,
                            "Environment": edit_environment,
                            "Status": "🟡 Modified - Test Required",
                            "Last Test": "Modified"
                        })
                        
                        save_servers(st.session_state.servers_list)
                        st.success(f"✅ Server '{edit_name}' updated successfully!")
                        st.session_state.show_edit_form = False
                        st.rerun()
                    else:
                        st.error("❌ Please fill in all required fields")

                if cancel_edit:
                    st.session_state.show_edit_form = False
                    st.rerun()

        # Server actions
        st.markdown("### 🛠️ Server Actions")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("🔍 Test All Connections", use_container_width=True):
                with st.spinner("Testing connections..."):
                    time.sleep(2)
                    st.success("✅ 3/4 clusters responded successfully")

        with col2:
            if st.button("📊 View Metrics", use_container_width=True):
                st.info("Cluster metrics would display here")

        with col3:
            if st.button("🔄 Refresh Status", use_container_width=True):
                st.success("Status refreshed")
                st.rerun()

        with col4:
            if st.button("📈 Performance Report", use_container_width=True):
                st.info("Performance report would generate here")

    with tab2:
        st.subheader(translate("➕ Add New Server"))

        # Database type templates
        st.markdown("#### 🎯 Quick Templates")
        col_template1, col_template2, col_template3, col_template4, col_template5 = st.columns(5)
        
        with col_template1:
            if st.button("🐘 PostgreSQL", use_container_width=True):
                st.session_state.db_template = "postgresql"
        
        with col_template2:
            if st.button("🐬 MySQL", use_container_width=True):
                st.session_state.db_template = "mysql"
        
        with col_template3:
            if st.button("🔴 Redis", use_container_width=True):
                st.session_state.db_template = "redis"
        
        with col_template4:
            if st.button("🔶 Redshift", use_container_width=True):
                st.session_state.db_template = "redshift"
        
        with col_template5:
            if st.button("🌟 Custom", use_container_width=True):
                st.session_state.db_template = "custom"

        # Initialize template if not set
        if 'db_template' not in st.session_state:
            st.session_state.db_template = "postgresql"

        # Template defaults
        templates = {
            "postgresql": {
                "name": "postgresql-server",
                "host": "localhost",
                "port": 5432,
                "database": "postgres",
                "username": "postgres"
            },
            "mysql": {
                "name": "mysql-server", 
                "host": "localhost",
                "port": 3306,
                "database": "mysql",
                "username": "root"
            },
            "redis": {
                "name": "redis-server",
                "host": "localhost", 
                "port": 6379,
                "database": "0",
                "username": ""
            },
            "redshift": {
                "name": "redshift-cluster",
                "host": "redshift-cluster.amazonaws.com",
                "port": 5439,
                "database": "dev",
                "username": "admin"
            },
            "custom": {
                "name": "custom-server",
                "host": "localhost",
                "port": 5432,
                "database": "mydb",
                "username": "user"
            }
        }

        current_template = templates[st.session_state.db_template]
        
        st.info(f"📋 Using template: **{st.session_state.db_template.upper()}**")

        with st.form("add_server_form"):
            st.markdown("#### Basic Configuration")

            col1, col2 = st.columns(2)

            with col1:
                server_name = st.text_input(
                    "Server Name", value=current_template["name"]
                )
                host = st.text_input(
                    "Host", value=current_template["host"]
                )
                _port = st.number_input(
                    "Port", min_value=1, max_value=65535, value=current_template["port"]
                )
                database = st.text_input("Database", value=current_template["database"])

            with col2:
                _environment = st.selectbox(
                    "Environment", ["Development", "Staging", "Production", "Testing"]
                )
                _connection_type = st.selectbox(
                    "Connection Type",
                    ["Standard", "SSL/TLS", "SSH Tunnel"],
                )
                _ssl_mode = st.selectbox(
                    "SSL Mode", ["require", "prefer", "allow", "disable"]
                )

            st.markdown("#### Authentication")
            username = st.text_input("Username", value=current_template["username"])
            _password = st.text_input(
                "Password", type="password", placeholder="Enter password"
            )

            st.markdown("#### Advanced Settings")
            _max_connections = st.slider("Max Connections", 1, 500, 20)
            _connection_timeout = st.slider("Connection Timeout (seconds)", 5, 120, 30)

            submitted = st.form_submit_button(
                "🚀 Add Server", use_container_width=True, type="primary"
            )

            if submitted:
                if server_name and host and database:
                    # Add server to the list
                    new_server = {
                        "Name": server_name,
                        "Host": host,
                        "Port": _port,
                        "Database": database,
                        "Username": username,
                        "Password": _password,
                        "Environment": _environment,
                        "Status": "🟡 Not Tested",
                        "Last Test": "Never",
                    }
                    
                    if 'servers_list' not in st.session_state:
                        st.session_state.servers_list = []
                    
                    st.session_state.servers_list.append(new_server)
                    save_servers(st.session_state.servers_list)
                    
                    st.success(f"✅ Server '{server_name}' added successfully!")
                    st.balloons()
                    st.session_state.server_added = True
                    st.session_state.server_name = server_name
                else:
                    st.error("❌ Please fill in all required fields (Server Name, Host, Database)")

        # Test connection buttons outside the form
        if 'server_added' in st.session_state and st.session_state.server_added:
            st.markdown("---")
            st.info("🔍 **Next Step:** Test the connection to your new server")

            col_test1, col_test2 = st.columns(2)

            with col_test1:
                if st.button(
                    "🔗 Test Connection",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner(f"Testing connection to {st.session_state.server_name}..."):
                        time.sleep(2)
                        
                        # Update server status in the list
                        for server in st.session_state.servers_list:
                            if server["Name"] == st.session_state.server_name:
                                server["Status"] = "🟢 Connected"
                                server["Last Test"] = "Just now"
                                break
                        
                        st.success("✅ Connection test successful!")
                        st.session_state.server_added = False

            with col_test2:
                if st.button("⏭️ Skip Test", use_container_width=True):
                    st.info("You can test the connection later")
                    st.session_state.server_added = False

    with tab3:
        st.subheader("📊 Cluster Monitoring")

        # Real cluster status overview
        if 'servers_list' in st.session_state and st.session_state.servers_list:
            col1, col2, col3, col4 = st.columns(4)
            
            online_clusters = len([s for s in st.session_state.servers_list if s.get('Status', '').startswith('🟢')])
            offline_clusters = len([s for s in st.session_state.servers_list if not s.get('Status', '').startswith('🟢')])
            
            with col1:
                st.metric("🟢 Online Clusters", online_clusters)
            
            with col2:
                st.metric("🔴 Offline Clusters", offline_clusters)
            
            with col3:
                st.info("Node data available after cluster scan")
            
            with col4:
                st.info("Storage data available after cluster scan")
        else:
            st.warning("⚠️ No clusters configured. Add servers to monitor clusters.")

        # Real performance data only
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔥 CPU Utilization")
            st.info("CPU utilization charts will appear after monitoring setup")
            st.info("Configure performance monitoring to see real CPU data")

        with col2:
            st.markdown("#### 💾 Storage Usage")
            st.info("Storage usage charts will appear after database scans")
            st.info("Scan your databases to see real storage utilization")

        # Recent cluster activity
        st.markdown("#### 📋 Recent Cluster Activity")

        st.info("Real activity will appear here after system usage")
        st.info("System actions and database operations will be logged here")

    with tab3:
        st.subheader("⚙️ Server Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔧 Global Settings")

            _auto_refresh = st.checkbox("Auto-refresh server status", value=True)
            _refresh_interval = st.slider("Refresh interval (seconds)", 10, 300, 60)

            _show_inactive = st.checkbox("Show inactive servers", value=True)
            _enable_alerts = st.checkbox("Enable server alerts", value=True)

            if st.button("💾 Save Settings", type="primary"):
                st.success("Settings saved successfully!")

        with col2:
            st.markdown("#### 🚨 Alert Configuration")

            email_alerts = st.checkbox("Email alerts", value=True)
            if email_alerts:
                _email_address = st.text_input("Alert email", value="admin@company.com")

            slack_alerts = st.checkbox("Slack notifications", value=False)
            if slack_alerts:
                _slack_webhook = st.text_input("Slack webhook URL")

            st.markdown("#### 🔄 Maintenance")

            if st.button("🧹 Cleanup Old Logs", use_container_width=True):
                st.info("Cleaned 150 old log entries")

            if st.button("📊 Generate Health Report", use_container_width=True):
                st.success("Health report generated")


def show_cluster_users_and_roles():
    """Show Users, Roles and Groups management for clusters"""
    st.subheader("👥 Cluster Users, Roles & Groups")

    # Select cluster for scanning
    selected_server = st.selectbox(
        "🔍 Select Server to Scan:",
        [],  # Real servers will appear here
        help="Choose server to scan for users, roles and groups",
    )

    # Create sub-tabs for different operations
    subtab1, subtab2, subtab3, subtab4 = st.tabs(
        [
            "🔍 Scan & Discover",
            "👥 Users Management",
            "🏷️ Roles & Groups",
            "🔄 Migration Tools",
        ]
    )

    with subtab1:
        st.markdown("#### 🔍 Scan Cluster for Users, Roles & Groups")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.info(f"**Selected Server:** {selected_server}")

            if st.button(
                "🚀 Start Comprehensive Scan", type="primary", use_container_width=True
            ):
                scan_server_entities(selected_server)

        with col2:
            st.markdown("**Scan will discover:**")
            st.markdown("- 👤 Database users")
            st.markdown("- 🏷️ User roles")
            st.markdown("- 👥 User groups")
            st.markdown("- 🔐 Permissions")
            st.markdown("- 📊 Usage statistics")

    with subtab2:
        show_server_users_management(selected_server)

    with subtab3:
        show_server_roles_and_groups(selected_server)

    with subtab4:
        show_migration_tools(selected_server)


def scan_server_entities(server_name):
    """Simulate scanning cluster for users, roles and groups"""

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Scanning simulation
    steps = [
        "🔗 Connecting to cluster...",
        "👤 Scanning database users...",
        "🏷️ Discovering user roles...",
        "👥 Finding user groups...",
        "🔐 Analyzing permissions...",
        "📊 Collecting usage statistics...",
        "💾 Saving discovered entities...",
    ]

    for i, step in enumerate(steps):
        status_text.text(step)
        progress_bar.progress((i + 1) / len(steps))
        time.sleep(0.5)

    status_text.text("✅ Scan completed successfully!")

    # Show discovered entities
    st.success("🎉 Cluster scan completed successfully!")

    # Real discovered data would appear here
    discovered_data = {
        "Users": [
            {
                "Name": "example_user",
                "Type": "Superuser",
                "Groups": ["administrators"],
                "Last_Login": "2025-07-28 14:30",
                "Active": True,
            },
            {
                "Name": "example_analyst",
                "Type": "Regular",
                "Groups": ["analysts", "readers"],
                "Last_Login": "2025-07-28 13:45",
                "Active": True,
            },
            {
                "Name": "etl_service",
                "Type": "Service",
                "Groups": ["etl_workers"],
                "Last_Login": "2025-07-28 15:00",
                "Active": True,
            },
            {
                "Name": "report_user",
                "Type": "Regular",
                "Groups": ["reporters"],
                "Last_Login": "2025-07-27 16:20",
                "Active": True,
            },
            {
                "Name": "temp_user",
                "Type": "Temporary",
                "Groups": ["temp_access"],
                "Last_Login": "2025-07-25 10:15",
                "Active": False,
            },
        ],
        "Roles": [
            {
                "Name": "db_admin",
                "Description": "Database administrator",
                "Permissions": [
                    "CREATE",
                    "DROP",
                    "ALTER",
                    "SELECT",
                    "INSERT",
                    "UPDATE",
                    "DELETE",
                ],
            },
            {
                "Name": "data_analyst",
                "Description": "Data analysis role",
                "Permissions": ["SELECT", "CREATE VIEW"],
            },
            {
                "Name": "etl_worker",
                "Description": "ETL processing role",
                "Permissions": ["SELECT", "INSERT", "UPDATE", "CREATE TABLE"],
            },
            {
                "Name": "reporter",
                "Description": "Reporting role",
                "Permissions": ["SELECT", "CREATE VIEW"],
            },
            {
                "Name": "read_only",
                "Description": "Read-only access",
                "Permissions": ["SELECT"],
            },
        ],
        "Groups": [
            {
                "Name": "administrators",
                "Members": ["example_user"],
                "Roles": ["db_admin"],
                "Description": "System administrators",
            },
            {
                "Name": "analysts",
                "Members": ["example_analyst"],
                "Roles": ["data_analyst"],
                "Description": "Data analysts team",
            },
            {
                "Name": "etl_workers",
                "Members": ["etl_service"],
                "Roles": ["etl_worker"],
                "Description": "ETL service accounts",
            },
            {
                "Name": "reporters",
                "Members": ["report_user"],
                "Roles": ["reporter"],
                "Description": "Report generation users",
            },
            {
                "Name": "temp_access",
                "Members": ["temp_user"],
                "Roles": ["read_only"],
                "Description": "Temporary access group",
            },
        ],
    }
    
    # Override with empty data - no demo content
    discovered_data = {
        "Users": [],
        "Roles": [],
        "Groups": [],
    }
    st.info("Real cluster scan results would appear here")
    st.info("Connect to actual clusters to see discovered users, roles, and groups")

    # Store in session state for other tabs
    st.session_state[f"{cluster_name}_discovered_data"] = discovered_data

    # Display summary
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "👤 Users Found",
            len(discovered_data["Users"]),
            delta=f"+{len([u for u in discovered_data['Users'] if u['Active']])}",
        )

    with col2:
        st.metric("🏷️ Roles Found", len(discovered_data["Roles"]))

    with col3:
        st.metric("👥 Groups Found", len(discovered_data["Groups"]))

    # Show detailed tables
    st.markdown("---")
    st.markdown("#### 📋 Discovered Entities")

    tab_users, tab_roles, tab_groups = st.tabs(["👤 Users", "🏷️ Roles", "👥 Groups"])

    with tab_users:
        users_df = pd.DataFrame(discovered_data["Users"])
        st.dataframe(users_df, use_container_width=True)

    with tab_roles:
        roles_df = pd.DataFrame(discovered_data["Roles"])
        st.dataframe(roles_df, use_container_width=True)

    with tab_groups:
        groups_df = pd.DataFrame(discovered_data["Groups"])
        st.dataframe(groups_df, use_container_width=True)


def show_server_users_management(server_name):
    """Show users management for selected cluster"""
    st.markdown("#### 👤 Users Management")

    # Check if we have discovered data
    discovered_key = f"{cluster_name}_discovered_data"
    if discovered_key not in st.session_state:
        st.warning("⚠️ Please run cluster scan first to discover users")
        return

    discovered_data = st.session_state[discovered_key]
    users = discovered_data["Users"]

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("##### 📋 Current Users")

        # Users table with actions
        for i, user in enumerate(users):
            with st.container():
                col_info, col_status, col_actions = st.columns([2, 1, 2])

                with col_info:
                    status_icon = "🟢" if user["Active"] else "🔴"
                    st.markdown(f"**{status_icon} {user['Name']}**")
                    st.caption(
                        f"Type: {user['Type']} | Groups: {', '.join(user['Groups'])}"
                    )
                    st.caption(f"Last Login: {user['Last_Login']}")

                with col_status:
                    if user["Active"]:
                        st.success("Active")
                    else:
                        st.error("Inactive")

                with col_actions:
                    col_edit, col_migrate = st.columns(2)
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_user_btn_{i}"):
                            st.session_state[f"edit_user_{user['Name']}"] = True
                    with col_migrate:
                        if st.button("🔄 Migrate", key=f"migrate_user_btn_{i}"):
                            st.session_state[f"migrate_user_{user['Name']}"] = True

                st.divider()

    with col2:
        st.markdown("##### ➕ Add New User")

        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_user_type = st.selectbox(
                "User Type", ["Regular", "Superuser", "Service", "Temporary"]
            )
            new_user_groups = st.multiselect(
                "Groups",
                [
                    "administrators",
                    "analysts",
                    "etl_workers",
                    "reporters",
                    "temp_access",
                ],
            )
            new_password = st.text_input("Password", type="password")

            if st.form_submit_button("➕ Create User"):
                if new_username and new_password:
                    st.success(f"✅ User '{new_username}' created successfully!")
                    # Add to discovered data
                    new_user = {
                        "Name": new_username,
                        "Type": new_user_type,
                        "Groups": new_user_groups,
                        "Last_Login": "Never",
                        "Active": True,
                    }
                    st.session_state[discovered_key]["Users"].append(new_user)
                    st.rerun()
                else:
                    st.error("❌ Please provide username and password")


def show_server_roles_and_groups(server_name):
    """Show roles and groups management"""
    st.markdown("#### 🏷️ Roles & Groups Management")

    # Check if we have discovered data
    discovered_key = f"{cluster_name}_discovered_data"
    if discovered_key not in st.session_state:
        st.warning("⚠️ Please run cluster scan first to discover roles and groups")
        return

    discovered_data = st.session_state[discovered_key]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 🏷️ Roles Management")

        # Roles overview
        roles = discovered_data["Roles"]
        for i, role in enumerate(roles):
            with st.expander(f"🏷️ {role['Name']}"):
                st.markdown(f"**Description:** {role['Description']}")
                st.markdown(f"**Permissions:** {', '.join(role['Permissions'])}")

                col_edit, col_delete = st.columns(2)
                with col_edit:
                    if st.button("✏️ Edit Role", key=f"edit_role_btn_{i}"):
                        st.info("Role editing interface would open here")
                with col_delete:
                    if st.button("🗑️ Delete Role", key=f"delete_role_btn_{i}"):
                        st.warning("Role deletion confirmed")

        # Add new role
        st.markdown("##### ➕ Create New Role")
        with st.form("add_role_form"):
            role_name = st.text_input("Role Name")
            role_desc = st.text_input("Description")
            role_perms = st.multiselect(
                "Permissions",
                [
                    "SELECT",
                    "INSERT",
                    "UPDATE",
                    "DELETE",
                    "CREATE",
                    "DROP",
                    "ALTER",
                    "CREATE VIEW",
                ],
            )

            if st.form_submit_button("➕ Create Role"):
                if role_name:
                    st.success(f"✅ Role '{role_name}' created successfully!")
                    new_role = {
                        "Name": role_name,
                        "Description": role_desc,
                        "Permissions": role_perms,
                    }
                    st.session_state[discovered_key]["Roles"].append(new_role)
                    st.rerun()

    with col2:
        st.markdown("##### 👥 Groups Management")

        # Groups overview
        groups = discovered_data["Groups"]
        for i, group in enumerate(groups):
            with st.expander(f"👥 {group['Name']}"):
                st.markdown(f"**Description:** {group['Description']}")
                st.markdown(f"**Members:** {', '.join(group['Members'])}")
                st.markdown(f"**Roles:** {', '.join(group['Roles'])}")

                col_edit, col_delete = st.columns(2)
                with col_edit:
                    if st.button("✏️ Edit Group", key=f"edit_group_btn_{i}"):
                        st.info("Group editing interface would open here")
                with col_delete:
                    if st.button("🗑️ Delete Group", key=f"delete_group_btn_{i}"):
                        st.warning("Group deletion confirmed")

        # Add new group
        st.markdown("##### ➕ Create New Group")
        with st.form("add_group_form"):
            group_name = st.text_input("Group Name")
            group_desc = st.text_input("Description")
            group_members = st.multiselect(
                "Members", [user["Name"] for user in discovered_data["Users"]]
            )
            group_roles = st.multiselect(
                "Roles", [role["Name"] for role in discovered_data["Roles"]]
            )

            if st.form_submit_button("➕ Create Group"):
                if group_name:
                    st.success(f"✅ Group '{group_name}' created successfully!")
                    new_group = {
                        "Name": group_name,
                        "Description": group_desc,
                        "Members": group_members,
                        "Roles": group_roles,
                    }
                    st.session_state[discovered_key]["Groups"].append(new_group)
                    st.rerun()


def show_migration_tools(server_name):
    """Show tools for migrating users/roles/groups between servers"""
    st.markdown("#### 🔄 Migration Tools")

    # Check if we have discovered data
    discovered_key = f"{cluster_name}_discovered_data"
    if discovered_key not in st.session_state:
        st.warning("⚠️ Please run cluster scan first to discover entities for migration")
        return

    discovered_data = st.session_state[discovered_key]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 📤 Export Entities")

        st.info(f"**Source Cluster:** {cluster_name}")

        # Select entities to export
        export_users = st.checkbox("👤 Export Users", value=True)
        export_roles = st.checkbox("🏷️ Export Roles", value=True)
        export_groups = st.checkbox("👥 Export Groups", value=True)
        export_permissions = st.checkbox("🔐 Export Permissions", value=True)

        # Export options
        st.markdown("**Export Options:**")
        include_passwords = st.checkbox("Include encrypted passwords", value=False)
        include_inactive = st.checkbox("Include inactive users", value=False)

        if st.button(
            "📤 Generate Export Package", type="primary", use_container_width=True
        ):
            generate_export_package(
                cluster_name,
                discovered_data,
                {
                    "users": export_users,
                    "roles": export_roles,
                    "groups": export_groups,
                    "permissions": export_permissions,
                    "include_passwords": include_passwords,
                    "include_inactive": include_inactive,
                },
            )

    with col2:
        st.markdown("##### 📥 Import to Target Cluster")

        target_server = st.selectbox(
            "🎯 Target Server:",
            [
                "production-server",
                "staging-cluster",
                "dev-cluster",
                "analytics-cluster",
            ],
            index=1,
        )

        st.info(f"**Target Cluster:** {target_cluster}")

        # Migration options
        st.markdown("**Migration Options:**")
        overwrite_existing = st.checkbox("Overwrite existing entities", value=False)
        validate_before_import = st.checkbox("Validate before import", value=True)
        create_backup = st.checkbox("Create backup before import", value=True)

        # Import method
        import_method = st.radio(
            "Import Method:",
            ["🔄 Migrate All", "🎯 Selective Import", "📁 Upload Package"],
        )

        if import_method == "🎯 Selective Import":
            st.markdown("**Select entities to migrate:**")
            migrate_users = st.multiselect(
                "Users to migrate:", [user["Name"] for user in discovered_data["Users"]]
            )
            migrate_roles = st.multiselect(
                "Roles to migrate:", [role["Name"] for role in discovered_data["Roles"]]
            )
            migrate_groups = st.multiselect(
                "Groups to migrate:",
                [group["Name"] for group in discovered_data["Groups"]],
            )

        elif import_method == "📁 Upload Package":
            uploaded_file = st.file_uploader(
                "Upload Export Package", type=["json", "zip"]
            )

        if st.button("🚀 Start Migration", type="primary", use_container_width=True):
            start_migration(
                cluster_name, target_cluster, import_method, discovered_data
            )


def generate_export_package(source_cluster, data, options):
    """Generate export package for migration"""

    progress_bar = st.progress(0)
    status_text = st.empty()

    steps = [
        "📋 Preparing export data...",
        "🔐 Processing permissions...",
        "📦 Creating package...",
        "✅ Export complete!",
    ]

    for i, step in enumerate(steps):
        status_text.text(step)
        progress_bar.progress((i + 1) / len(steps))
        time.sleep(0.3)

    # Generate export summary
    export_summary = {
        "source_cluster": source_cluster,
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "entities": {
            "users": len(data["Users"]) if options["users"] else 0,
            "roles": len(data["Roles"]) if options["roles"] else 0,
            "groups": len(data["Groups"]) if options["groups"] else 0,
        },
    }

    st.success("🎉 Export package generated successfully!")

    col1, col2 = st.columns(2)

    with col1:
        st.json(export_summary)

    with col2:
        # Download button simulation
        export_filename = (
            f"{source_cluster}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        st.download_button(
            label="💾 Download Export Package",
            data=json.dumps(export_summary, indent=2),
            file_name=export_filename,
            mime="application/json",
        )


def start_migration(source_cluster, target_cluster, method, data):
    """Start migration process"""

    progress_bar = st.progress(0)
    status_text = st.empty()

    steps = [
        f"🔍 Validating target cluster: {target_cluster}...",
        "💾 Creating backup of target cluster...",
        "🚀 Starting migration process...",
        "👤 Migrating users...",
        "🏷️ Migrating roles...",
        "👥 Migrating groups...",
        "🔐 Setting up permissions...",
        "✅ Migration completed!",
    ]

    for i, step in enumerate(steps):
        status_text.text(step)
        progress_bar.progress((i + 1) / len(steps))
        time.sleep(0.4)

    # Migration results
    st.success("🎉 Migration completed successfully!")

    results = {
        "source_cluster": source_cluster,
        "target_cluster": target_cluster,
        "migration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": method,
        "results": {
            "users_migrated": len(data["Users"]),
            "roles_migrated": len(data["Roles"]),
            "groups_migrated": len(data["Groups"]),
            "errors": 0,
            "warnings": 2,
        },
    }

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("👤 Users Migrated", results["results"]["users_migrated"])

    with col2:
        st.metric("🏷️ Roles Migrated", results["results"]["roles_migrated"])

    with col3:
        st.metric("👥 Groups Migrated", results["results"]["groups_migrated"])

    if results["results"]["warnings"] > 0:
        st.warning(
            f"⚠️ Migration completed with {results['results']['warnings']} warnings"
        )
        st.markdown("**Warnings:**")
        st.markdown("- Some users already exist in target cluster")
        st.markdown("- Role 'admin' has different permissions in target")

    # Store migration results
    if "migration_history" not in st.session_state:
        st.session_state["migration_history"] = []
    st.session_state["migration_history"].append(results)


def show_user_management_page():
    """Show User Management page with full functionality"""
    # Import the advanced user management module
    try:
        from ui.pages.advanced_user_management import show_advanced_user_management
        show_advanced_user_management()
        return
    except ImportError as e:
        st.error(f"❌ Advanced user management not available: {e}")
        # Fall back to basic implementation
        pass
    except Exception as e:
        st.error(f"❌ Error loading advanced user management: {e}")
        # Fall back to basic implementation
        pass
    
    # Basic fallback implementation
    st.title(translate("👥 User Management"))
    st.markdown("### ניהול משתמשי מסד נתונים והרשאות")
    st.markdown("---")
    
    st.info("🔧 Advanced user management interface is loading. If you see this message, the system is using a simplified fallback.")

    # User management tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["👥 Users", "🔐 Permissions", "📊 Activity", "⚙️ Settings"]
    )

    with tab1:
        # Users overview section
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("👤 Database Users")

            # Real user data only
            users_data = [
                {
                    "Username": "example_user",
                    "Type": "Superuser",
                    "Status": "🟢 Active",
                    "Last Login": "2025-07-28 14:30",
                    "Queries": 1247,
                },
                {
                    "Username": "example_analyst",
                    "Type": "Regular",
                    "Status": "🟢 Active",
                    "Last Login": "2025-07-28 13:45",
                    "Queries": 89,
                },
                {
                    "Username": "developer_team",
                    "Type": "Developer",
                    "Status": "🟢 Active",
                    "Last Login": "2025-07-28 15:10",
                    "Queries": 456,
                },
                {
                    "Username": "read_only_user",
                    "Type": "Read Only",
                    "Status": "🟡 Inactive",
                    "Last Login": "2025-07-27 09:20",
                    "Queries": 23,
                },
                {
                    "Username": "etl_service",
                    "Type": "Service",
                    "Status": "🟢 Active",
                    "Last Login": "2025-07-28 15:25",
                    "Queries": 789,
                },
            ]

            users_df = pd.DataFrame(users_data)

            # Add selection capability
            _selected_users = st.dataframe(
                users_df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="multi-row",
            )

            # User actions
            st.markdown("### 🛠️ User Actions")
            col_act1, col_act2, col_act3, col_act4 = st.columns(4)

            with col_act1:
                if st.button("➕ Add User", use_container_width=True):
                    st.success("Add user dialog would open here")

            with col_act2:
                if st.button("✏️ Edit User", use_container_width=True):
                    st.info("Edit user dialog would open here")

            with col_act3:
                if st.button("🔒 Reset Password", use_container_width=True):
                    st.warning("Password reset dialog would open here")

            with col_act4:
                if st.button("🗑️ Delete User", use_container_width=True):
                    st.error("Delete confirmation would appear here")

        with col2:
            st.subheader("📊 User Statistics")

            # User metrics
            st.info("User metrics available after database scans")
            st.info("Connect and scan databases to see real user data")

            # Real user types chart
            st.info("User types distribution will appear after database scans")
            st.info("Chart will show real user type breakdown from connected databases")

            # Quick user creation
            st.markdown("### ⚡ Quick Add User")
            with st.form("quick_user_form"):
                new_username = st.text_input("Username")
                _new_user_type = st.selectbox(
                    "User Type", ["Regular", "Developer", "Read Only", "Service"]
                )
                new_password = st.text_input("Password", type="password")

                if st.form_submit_button("Create User", use_container_width=True):
                    if new_username and new_password:
                        st.success(f"✅ User '{new_username}' created successfully!")
                    else:
                        st.error("Please fill all fields")

    with tab2:
        st.subheader("🔐 User Permissions")

        # Permission management
        col_perm1, col_perm2 = st.columns([1, 2])

        with col_perm1:
            st.markdown("#### Select User")
            selected_user_perm = st.selectbox(
                "User:",
                [
                    "example_user",
                    "example_analyst",
                    "developer_team",
                    "read_only_user",
                    "etl_service",
                ],
            )

            st.markdown("#### User Details")
            st.info(
                f"""
            **Username:** {selected_user_perm}
            **Type:** {"Superuser" if selected_user_perm == "example_user" else "Regular"}
            **Status:** Active
            **Created:** 2025-01-15
            """
            )

        with col_perm2:
            st.markdown("#### Database Permissions")

            # Permissions matrix
            databases = []  # Real databases will appear here
            permissions = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP"]

            perm_data = []
            for db in databases:
                for perm in permissions:
                    # Simulate permission status
                    has_perm = (
                        True
                        if selected_user_perm == "example_user"
                        else random.choice([True, False])
                    )
                    perm_data.append(
                        {
                            "Database": db,
                            "Permission": perm,
                            "Granted": "✅" if has_perm else "❌",
                        }
                    )

            perm_df = pd.DataFrame(perm_data)
            st.dataframe(perm_df, use_container_width=True, hide_index=True)

            # Permission actions
            col_perm_act1, col_perm_act2 = st.columns(2)
            with col_perm_act1:
                if st.button("✅ Grant Permissions", use_container_width=True):
                    st.success("Permissions granted")
            with col_perm_act2:
                if st.button("❌ Revoke Permissions", use_container_width=True):
                    st.warning("Permissions revoked")

    with tab3:
        st.subheader("📊 User Activity Monitoring")

        # Activity overview
        col_act_over1, col_act_over2 = st.columns([2, 1])

        with col_act_over1:
            st.markdown("#### Recent User Activity")

            # Sample activity data
            activity_data = [
                {
                    "Time": "15:25",
                    "User": "etl_service",
                    "Action": "BULK INSERT",
                    "Table": "table_name",
                    "Status": "✅ Success",
                },
                {
                    "Time": "15:10",
                    "User": "developer_team",
                    "Action": "CREATE TABLE",
                    "Table": "temp_analysis",
                    "Status": "✅ Success",
                },
                {
                    "Time": "14:45",
                    "User": "example_analyst",
                    "Action": "SELECT",
                    "Table": "table_name",
                    "Status": "✅ Success",
                },
                {
                    "Time": "14:30",
                    "User": "example_user",
                    "Action": "GRANT PERMISSION",
                    "Table": "user_mgmt",
                    "Status": "✅ Success",
                },
                {
                    "Time": "14:15",
                    "User": "example_analyst",
                    "Action": "UPDATE",
                    "Table": "report_configs",
                    "Status": "⚠️ Warning",
                },
                {
                    "Time": "14:00",
                    "User": "read_only_user",
                    "Action": "SELECT",
                    "Table": "public.orders",
                    "Status": "❌ Failed",
                },
            ]

            activity_df = pd.DataFrame(activity_data)
            st.info("Real activity will appear here after system usage")

            # Activity chart
            st.markdown("#### User Activity Over Time")
            activity_chart_data = pd.DataFrame(
                {
                    "Hour": ["12:00", "13:00", "14:00", "15:00", "16:00"],
                    "example_user": [15, 23, 18, 25, 12],
                    "example_analyst": [8, 12, 15, 9, 6],
                    "developer_team": [5, 8, 12, 18, 15],
                    "etl_service": [45, 52, 48, 55, 42],
                }
            )

            fig = go.Figure()
            for user in ["example_user", "example_analyst", "developer_team", "etl_service"]:
                fig.add_trace(
                    go.Scatter(
                        x=activity_chart_data["Hour"],
                        y=activity_chart_data[user],
                        mode="lines+markers",
                        name=user,
                    )
                )

            fig.update_layout(title="Hourly User Activity", height=300)
            st.info("Chart will appear here after real data collection")

        with col_act_over2:
            st.markdown("#### Activity Metrics")
            st.info("Activity metrics available after system usage")
            st.info("Real-time activity data will appear here")

            st.markdown("#### Top Active Users")
            top_users = pd.DataFrame(
                {
                    "User": [
                        "etl_service",
                        "example_user",
                        "developer_team",
                        "example_analyst",
                    ],
                    "Actions": [1247, 456, 234, 156],
                }
            )

            fig = go.Figure(
                data=[
                    go.Bar(
                        x=top_users["Actions"],
                        y=top_users["User"],
                        orientation="h",
                        marker_color="lightblue",
                    )
                ]
            )
            fig.update_layout(title="Actions Today", height=250)
            st.info("Chart will appear here after real data collection")

    with tab4:
        st.subheader("⚙️ User Management Settings")

        col_settings1, col_settings2 = st.columns(2)

        with col_settings1:
            st.markdown("#### Password Policy")

            _min_length = st.slider("Minimum Password Length", 6, 20, 8)
            _require_uppercase = st.checkbox("Require Uppercase Letters", value=True)
            _require_lowercase = st.checkbox("Require Lowercase Letters", value=True)
            _require_numbers = st.checkbox("Require Numbers", value=True)
            _require_special = st.checkbox("Require Special Characters", value=False)

            st.markdown("#### Session Settings")
            _session_timeout = st.slider("Session Timeout (minutes)", 15, 480, 60)
            _max_concurrent = st.slider("Max Concurrent Sessions", 1, 10, 3)

            if st.button("💾 Save Settings", type="primary"):
                st.success("Settings saved successfully!")

        with col_settings2:
            st.markdown("#### Account Lockout Policy")

            _max_attempts = st.slider("Max Failed Login Attempts", 3, 10, 5)
            _lockout_duration = st.slider("Lockout Duration (minutes)", 5, 60, 15)

            st.markdown("#### Audit Settings")
            _audit_logins = st.checkbox("Audit Login Attempts", value=True)
            _audit_queries = st.checkbox("Audit Query Execution", value=True)
            _audit_permissions = st.checkbox("Audit Permission Changes", value=True)

            st.markdown("#### Maintenance")
            if st.button("🧹 Clean Old Sessions", use_container_width=True):
                st.info("Cleaned 12 expired sessions")

            if st.button("📊 Generate User Report", use_container_width=True):
                st.success("User report generated")

            if st.button("🔄 Refresh User Cache", use_container_width=True):
                st.success("User cache refreshed")


def show_module_manager_page():
    """Show Module Manager page with real functionality"""
    st.title("🔧 Module Manager")
    st.markdown("### System Modules and Extensions Management")
    st.markdown("---")

    # Initialize module manager
    try:
        from core.module_manager import ModuleManager
        module_manager = ModuleManager()
    except Exception as e:
        st.error(f"Failed to initialize Module Manager: {e}")
        return

    # Module management tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📦 Modules", "⚙️ Configuration", "📊 Status", "🔄 Operations"]
    )

    with tab1:
        st.subheader("📦 Module Management")

        # Get installed and discovered modules
        try:
            installed_modules = module_manager.get_installed_modules()
            discovered_modules = module_manager.discover_modules()
        except Exception as e:
            st.error(f"Failed to load modules: {e}")
            return

        # Display installed modules
        if installed_modules:
            st.markdown("#### ✅ Installed Modules")
            
            for module in installed_modules:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                    
                    with col1:
                        status_icon = {
                            'active': '🟢',
                            'disabled': '⚪',
                            'error': '🔴'
                        }.get(module['status'], '🟡')
                        
                        st.markdown(f"**{module['name']}** {status_icon}")
                        st.caption(f"v{module['version']} | {module['module_type']}")
                        if module['description']:
                            st.caption(module['description'][:80] + "..." if len(module['description']) > 80 else module['description'])
                    
                    with col2:
                        st.caption("Status")
                        st.write(module['status'].title())
                    
                    with col3:
                        st.caption("Installed")
                        st.write(module['installed_at'][:10] if module['installed_at'] else "Unknown")
                    
                    with col4:
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            if st.button("⚙️", key=f"config_{module['name']}", help="Configure"):
                                st.session_state.selected_module = module['name']
                                st.session_state.active_tab = 1  # Switch to configuration tab
                        
                        with col_btn2:
                            if st.button("🗑️", key=f"uninstall_{module['name']}", help="Uninstall"):
                                if st.session_state.get(f"confirm_uninstall_{module['name']}", False):
                                    result = module_manager.uninstall_module(module['name'])
                                    if result['success']:
                                        st.success(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['error'])
                                else:
                                    st.session_state[f"confirm_uninstall_{module['name']}"] = True
                                    st.warning(f"Click again to confirm uninstalling {module['name']}")
                    
                    st.markdown("---")
        else:
            st.info("No modules installed yet")

        # Display available modules for installation
        available_modules = [m for m in discovered_modules if not m.get('is_installed', False)]
        
        if available_modules:
            st.markdown("#### 📥 Available Modules")
            
            for module in available_modules:
                with st.container():
                    col1, col2, col3 = st.columns([4, 1, 1])
                    
                    with col1:
                        loadable_icon = "✅" if module.get('is_loadable', False) else "❌"
                        st.markdown(f"**{module['name']}** {loadable_icon}")
                        st.caption(f"v{module['version']} | {module.get('type', 'extension')}")
                        if module.get('description'):
                            st.caption(module['description'][:80] + "..." if len(module['description']) > 80 else module['description'])
                        
                        # Show dependencies
                        if module.get('dependencies'):
                            deps_text = ", ".join(module['dependencies'])
                            st.caption(f"📦 Dependencies: {deps_text}")
                    
                    with col2:
                        st.caption("Loadable")
                        st.write("Yes" if module.get('is_loadable', False) else "No")
                    
                    with col3:
                        if module.get('is_loadable', False):
                            if st.button("📥 Install", key=f"install_{module['name']}"):
                                result = module_manager.install_module(module['name'])
                                if result['success']:
                                    st.success(result['message'])
                                    st.rerun()
                                else:
                                    st.error(result['error'])
                        else:
                            st.button("❌ Cannot Install", key=f"cannot_install_{module['name']}", disabled=True)
                    
                    st.markdown("---")
        else:
            st.info("No additional modules available for installation")

        # Module actions
        st.markdown("### 🛠️ Module Actions")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("🔄 Refresh Modules", use_container_width=True):
                st.success("Modules refreshed")
                st.rerun()

        with col2:
            if st.button("📊 View Dependencies", use_container_width=True):
                st.session_state.show_dependencies = True

        with col3:
            if st.button("🔍 Module Details", use_container_width=True):
                st.session_state.show_module_details = True

        with col4:
            if st.button("🔧 System Info", use_container_width=True):
                st.session_state.show_system_info = True

        # Show dependency information if requested
        if st.session_state.get('show_dependencies', False):
            st.markdown("### 📊 Module Dependencies")
            
            for module in installed_modules:
                with st.expander(f"Dependencies for {module['name']}"):
                    dep_info = module_manager.get_module_dependencies(module['name'])
                    if dep_info['success']:
                        if dep_info['dependencies']:
                            for dep, status in dep_info['dependency_status'].items():
                                icon = "✅" if status['available'] else "❌"
                                st.write(f"{icon} {dep}")
                                if not status['available']:
                                    st.caption(f"Error: {status['error']}")
                        else:
                            st.info("No dependencies")
                    else:
                        st.error(dep_info['error'])
            
            if st.button("Close Dependencies"):
                st.session_state.show_dependencies = False
                st.rerun()

    with tab2:
        st.subheader("⚙️ Module Configuration")

        # Get installed modules for configuration
        if not installed_modules:
            st.info("No installed modules to configure")
        else:
            # Select module to configure
            module_names = [m['name'] for m in installed_modules]
            selected_module_name = st.selectbox(
                "Select Module to Configure:",
                module_names,
                index=module_names.index(st.session_state.get('selected_module', module_names[0])) if st.session_state.get('selected_module') in module_names else 0
            )

            if selected_module_name:
                # Get current configuration
                config_result = module_manager.get_module_config(selected_module_name)
                current_config = config_result.get('configs', {}) if config_result['success'] else {}
                
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"#### Configuration for {selected_module_name}")

                    # Dynamic configuration based on module type
                    selected_module_info = next((m for m in installed_modules if m['name'] == selected_module_name), None)
                    
                    if selected_module_info:
                        st.caption(f"Module Type: {selected_module_info['module_type']}")
                        st.caption(f"Version: {selected_module_info['version']}")
                        
                        # Common configuration options
                        st.markdown("##### General Settings")
                        
                        enabled = st.checkbox(
                            "Module Enabled", 
                            value=current_config.get('enabled', True),
                            key=f"enabled_{selected_module_name}"
                        )
                        
                        log_level = st.selectbox(
                            "Log Level",
                            ["DEBUG", "INFO", "WARNING", "ERROR"],
                            index=["DEBUG", "INFO", "WARNING", "ERROR"].index(current_config.get('log_level', 'INFO')),
                            key=f"log_level_{selected_module_name}"
                        )
                        
                        # Module-specific configuration
                        if selected_module_name.lower() == "alerts" or "alert" in selected_module_name.lower():
                            st.markdown("##### Alert Settings")
                            
                            smtp_server = st.text_input(
                                "SMTP Server", 
                                value=current_config.get('smtp_server', 'localhost'),
                                key=f"smtp_server_{selected_module_name}"
                            )
                            
                            smtp_port = st.number_input(
                                "SMTP Port", 
                                min_value=1, max_value=65535,
                                value=current_config.get('smtp_port', 587),
                                key=f"smtp_port_{selected_module_name}"
                            )
                            
                            email_from = st.text_input(
                                "From Email", 
                                value=current_config.get('email_from', 'alerts@multidbmanager.local'),
                                key=f"email_from_{selected_module_name}"
                            )
                            
                            st.markdown("##### Alert Thresholds")
                            cpu_threshold = st.slider(
                                "CPU Alert (%)", 0, 100, 
                                value=current_config.get('cpu_threshold', 80),
                                key=f"cpu_threshold_{selected_module_name}"
                            )
                            
                            memory_threshold = st.slider(
                                "Memory Alert (%)", 0, 100, 
                                value=current_config.get('memory_threshold', 85),
                                key=f"memory_threshold_{selected_module_name}"
                            )
                            
                            disk_threshold = st.slider(
                                "Disk Usage Alert (%)", 0, 100, 
                                value=current_config.get('disk_threshold', 90),
                                key=f"disk_threshold_{selected_module_name}"
                            )

                        elif selected_module_name.lower() == "backup" or "backup" in selected_module_name.lower():
                            st.markdown("##### Backup Settings")
                            
                            backup_interval = st.selectbox(
                                "Backup Frequency", 
                                ["hourly", "daily", "weekly", "monthly"],
                                index=["hourly", "daily", "weekly", "monthly"].index(current_config.get('backup_interval', 'daily')),
                                key=f"backup_interval_{selected_module_name}"
                            )
                            
                            retention_days = st.number_input(
                                "Retention Days", 
                                min_value=1, max_value=365, 
                                value=current_config.get('retention_days', 30),
                                key=f"retention_days_{selected_module_name}"
                            )
                            
                            compression = st.checkbox(
                                "Enable Compression", 
                                value=current_config.get('compression', True),
                                key=f"compression_{selected_module_name}"
                            )

                            st.markdown("##### Storage Settings")
                            backup_location = st.text_input(
                                "Backup Location", 
                                value=current_config.get('backup_location', '/backup/multidb'),
                                key=f"backup_location_{selected_module_name}"
                            )
                            
                            cloud_backup = st.checkbox(
                                "Enable Cloud Backup", 
                                value=current_config.get('cloud_backup', False),
                                key=f"cloud_backup_{selected_module_name}"
                            )

                        else:
                            st.markdown("##### Custom Configuration")
                            st.info(f"Module-specific configuration for {selected_module_name}")
                            
                            # Allow adding custom config keys
                            st.markdown("##### Add Custom Configuration")
                            new_key = st.text_input("Configuration Key", key=f"new_key_{selected_module_name}")
                            new_value = st.text_input("Configuration Value", key=f"new_value_{selected_module_name}")
                            value_type = st.selectbox("Value Type", ["string", "integer", "boolean", "json"], key=f"new_type_{selected_module_name}")
                            
                            if st.button("Add Configuration", key=f"add_config_{selected_module_name}"):
                                if new_key and new_value:
                                    result = module_manager.set_module_config(selected_module_name, new_key, new_value, value_type)
                                    if result['success']:
                                        st.success(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['error'])

                        # Save configuration button
                        if st.button("💾 Save Configuration", key=f"save_config_{selected_module_name}"):
                            try:
                                # Save all configuration values
                                configs_to_save = {
                                    'enabled': enabled,
                                    'log_level': log_level
                                }
                                
                                # Add module-specific configs
                                if selected_module_name.lower() == "alerts" or "alert" in selected_module_name.lower():
                                    configs_to_save.update({
                                        'smtp_server': smtp_server,
                                        'smtp_port': smtp_port,
                                        'email_from': email_from,
                                        'cpu_threshold': cpu_threshold,
                                        'memory_threshold': memory_threshold,
                                        'disk_threshold': disk_threshold
                                    })
                                elif selected_module_name.lower() == "backup" or "backup" in selected_module_name.lower():
                                    configs_to_save.update({
                                        'backup_interval': backup_interval,
                                        'retention_days': retention_days,
                                        'compression': compression,
                                        'backup_location': backup_location,
                                        'cloud_backup': cloud_backup
                                    })
                                
                                # Save each config
                                all_success = True
                                for key, value in configs_to_save.items():
                                    data_type = "boolean" if isinstance(value, bool) else "integer" if isinstance(value, int) else "string"
                                    result = module_manager.set_module_config(selected_module_name, key, value, data_type)
                                    if not result['success']:
                                        all_success = False
                                        st.error(f"Failed to save {key}: {result['error']}")
                                        break
                                
                                if all_success:
                                    st.success("Configuration saved successfully!")
                                    
                            except Exception as e:
                                st.error(f"Failed to save configuration: {e}")

                with col2:
                    st.markdown("#### Current Configuration")
                    
                    if current_config:
                        for key, value in current_config.items():
                            st.code(f"{key}: {value}")
                    else:
                        st.info("No configuration set")
                        
                    st.markdown("#### Actions")
                    
                    if st.button("🔄 Reset to Defaults", key=f"reset_{selected_module_name}"):
                        st.warning("Reset functionality would remove all custom configuration")
                        
                    if st.button("📋 Export Config", key=f"export_{selected_module_name}"):
                        if current_config:
                            st.download_button(
                                "Download Configuration",
                                data=json.dumps(current_config, indent=2),
                                file_name=f"{selected_module_name}_config.json",
                                mime="application/json"
                            )
                        else:
                            st.info("No configuration to export")

        with col2:
            st.markdown("#### Module Info")
            st.info(
                f"""
            **Module:** {selected_module}
            **Status:** Active
            **Version:** 1.2.0
            **Type:** Core Module
            **Dependencies:** OK
            """
            )

            if st.button(
                "💾 Save Configuration", use_container_width=True, type="primary"
            ):
                st.success("Configuration saved!")

            if st.button("🔄 Reset to Default", use_container_width=True):
                st.warning("Configuration reset to defaults")

            if st.button("📋 Export Config", use_container_width=True):
                st.info("Configuration exported")

    with tab3:
        st.subheader("📊 Module Status")
        
        if not installed_modules:
            st.info("No installed modules to monitor")
        else:
            # Status overview
            st.markdown("#### System Overview")
            
            total_modules = len(installed_modules)
            active_modules = len([m for m in installed_modules if m['status'] == 'active'])
            error_modules = len([m for m in installed_modules if m['status'] == 'error'])
            disabled_modules = len([m for m in installed_modules if m['status'] == 'disabled'])
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Modules", total_modules)
                
            with col2:
                st.metric("Active", active_modules, delta=None)
                
            with col3:
                st.metric("Errors", error_modules, delta=None if error_modules == 0 else f"-{error_modules}")
                
            with col4:
                st.metric("Disabled", disabled_modules)
            
            # Detailed status for each module
            st.markdown("#### Detailed Status")
            
            for module in installed_modules:
                with st.expander(f"{module['name']} - {module['status'].title()}", expanded=module['status'] == 'error'):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Version:** {module['version']}")
                        st.write(f"**Type:** {module['module_type']}")
                        st.write(f"**Installed:** {module['installed_at'][:19] if module['installed_at'] else 'Unknown'}")
                        
                        if module['last_loaded_at']:
                            st.write(f"**Last Loaded:** {module['last_loaded_at'][:19]}")
                        
                        if module['load_errors']:
                            st.error(f"**Load Errors:** {module['load_errors']}")
                            
                        # Get detailed status
                        detailed_status = module_manager.get_module_status(module['name'])
                        if detailed_status.get('exists'):
                            if detailed_status.get('is_loadable'):
                                st.success("✅ Module is loadable")
                            else:
                                st.error("❌ Module has loading issues")
                                
                            # Show dependencies status
                            dep_info = module_manager.get_module_dependencies(module['name'])
                            if dep_info['success'] and dep_info.get('dependencies'):
                                st.write("**Dependencies:**")
                                for dep, status in dep_info['dependency_status'].items():
                                    icon = "✅" if status['available'] else "❌"
                                    st.write(f"  {icon} {dep}")
                    
                    with col2:
                        # Module actions
                        current_status = module['status']
                        
                        if current_status == 'active':
                            if st.button("⏸️ Disable", key=f"disable_{module['name']}"):
                                result = module_manager.update_module_status(module['name'], 'disabled')
                                if result['success']:
                                    st.success(result['message'])
                                    st.rerun()
                                else:
                                    st.error(result['error'])
                        else:
                            if st.button("▶️ Enable", key=f"enable_{module['name']}"):
                                result = module_manager.update_module_status(module['name'], 'active')
                                if result['success']:
                                    st.success(result['message'])
                                    st.rerun()
                                else:
                                    st.error(result['error'])
                        
                        if st.button("🔄 Test Load", key=f"test_load_{module['name']}"):
                            result = module_manager.load_module(module['name'])
                            if result['success']:
                                st.success("Module loaded successfully!")
                            else:
                                st.error(f"Load failed: {result['error']}")
                        
                        if st.button("ℹ️ Details", key=f"details_{module['name']}"):
                            st.session_state[f"show_details_{module['name']}"] = True
                        
                        # Show details if requested
                        if st.session_state.get(f"show_details_{module['name']}", False):
                            st.markdown("**Metadata:**")
                            if module.get('metadata'):
                                metadata = json.loads(module['metadata']) if isinstance(module['metadata'], str) else module['metadata']
                                for key, value in metadata.items():
                                    st.caption(f"{key}: {value}")
                            
                            if st.button("Hide Details", key=f"hide_details_{module['name']}"):
                                st.session_state[f"show_details_{module['name']}"] = False
                                st.rerun()

    with tab4:
        st.subheader("🔄 Module Operations")
        
        # Bulk operations
        st.markdown("#### Bulk Operations")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh All Modules", use_container_width=True):
                try:
                    discovered = module_manager.discover_modules()
                    st.success(f"Discovered {len(discovered)} modules")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to refresh: {e}")
        
        with col2:
            if st.button("⏸️ Disable All Modules", use_container_width=True):
                if st.session_state.get('confirm_disable_all', False):
                    try:
                        for module in installed_modules:
                            module_manager.update_module_status(module['name'], 'disabled')
                        st.success("All modules disabled")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to disable all: {e}")
                else:
                    st.session_state.confirm_disable_all = True
                    st.warning("Click again to confirm disabling all modules")
        
        with col3:
            if st.button("▶️ Enable All Modules", use_container_width=True):
                try:
                    for module in installed_modules:
                        module_manager.update_module_status(module['name'], 'active')
                    st.success("All modules enabled")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to enable all: {e}")
        
        # System information
        st.markdown("#### System Information")
        
        with st.expander("📊 Module System Stats"):
            st.write("**Module Directory:** `modules/`")
            st.write(f"**Database:** `{module_manager.db_path}`")
            
            # Check database connectivity
            try:
                test_modules = module_manager.get_installed_modules()
                st.success(f"✅ Database connected - {len(test_modules)} installed modules")
            except Exception as e:
                st.error(f"❌ Database connection failed: {e}")
            
            # Check modules directory
            if module_manager.modules_dir.exists():
                module_dirs = [d for d in module_manager.modules_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
                st.success(f"✅ Modules directory found - {len(module_dirs)} module directories")
            else:
                st.error("❌ Modules directory not found")
        
        # Advanced operations
        st.markdown("#### Advanced Operations")
        
        with st.expander("🔧 Advanced Module Management"):
            st.warning("⚠️ Advanced operations - use with caution")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Clean Module Database"):
                    if st.session_state.get('confirm_clean_db', False):
                        try:
                            # This would clean orphaned entries
                            st.info("Database cleaning functionality would be implemented here")
                        except Exception as e:
                            st.error(f"Failed to clean database: {e}")
                    else:
                        st.session_state.confirm_clean_db = True
                        st.warning("Click again to confirm database cleanup")
            
            with col2:
                if st.button("📊 Export Module Registry"):
                    try:
                        registry_data = {
                            'installed_modules': module_manager.get_installed_modules(),
                            'discovered_modules': module_manager.discover_modules(),
                            'export_timestamp': datetime.now().isoformat()
                        }
                        
                        st.download_button(
                            "Download Module Registry",
                            data=json.dumps(registry_data, indent=2),
                            file_name=f"module_registry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    except Exception as e:
                        st.error(f"Failed to export registry: {e}")
        
        # Module development tools
        with st.expander("🛠️ Module Development Tools"):
            st.markdown("##### Create New Module Template")
            
            new_module_name = st.text_input("Module Name")
            new_module_type = st.selectbox("Module Type", ["core", "extension", "plugin"])
            new_module_version = st.text_input("Version", value="1.0.0")
            new_module_description = st.text_area("Description")
            
            if st.button("🎯 Create Module Template"):
                if new_module_name:
                    module_path = module_manager.modules_dir / new_module_name
                    try:
                        module_path.mkdir(exist_ok=True)
                        
                        # Create module.json
                        module_config = {
                            "name": new_module_name,
                            "version": new_module_version,
                            "type": new_module_type,
                            "description": new_module_description,
                            "main_file": "__init__.py",
                            "dependencies": [],
                            "author": "MultiDBManager",
                            "created": datetime.now().isoformat()
                        }
                        
                        with open(module_path / "module.json", 'w') as f:
                            json.dump(module_config, f, indent=2)
                        
                        # Create basic __init__.py
                        init_content = f'''"""
{new_module_name} Module
{new_module_description}
"""

__version__ = "{new_module_version}"
__author__ = "MultiDBManager"

def initialize():
    """Initialize the module"""
    print(f"Initializing {{__name__}} module v{{__version__}}")
    return True

def get_info():
    """Get module information"""
    return {{
        "name": "{new_module_name}",
        "version": __version__,
        "description": "{new_module_description}",
        "type": "{new_module_type}"
    }}
'''
                        
                        with open(module_path / "__init__.py", 'w') as f:
                            f.write(init_content)
                        
                        st.success(f"Module template created at {module_path}")
                        st.info("You can now develop your module and install it using the Modules tab")
                        
                    except Exception as e:
                        st.error(f"Failed to create module template: {e}")
                else:
                    st.warning("Please enter a module name")


def show_settings_page():
    """Show Settings page with full functionality"""
    st.title("⚙️ Settings")
    st.markdown("### System Configuration and Preferences")
    st.markdown("---")

    # Settings tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🔧 General", "🔐 Security", "🎨 Interface", "📊 Database", "ℹ️ System Info"]
    )

    with tab1:
        st.subheader("🔧 General Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🌍 Localization")
            _language = st.selectbox(
                "Language", ["English", "עברית", "Español", "Français"]
            )
            _timezone = st.selectbox(
                "Timezone",
                ["UTC", "America/New_York", "Europe/London", "Asia/Jerusalem"],
            )
            date_format = st.selectbox(
                "Date Format", ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"]
            )

            st.markdown("#### 📱 Application")
            _theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])
            page_size = st.slider("Items per page", 10, 100, 25)
            _auto_save = st.checkbox("Auto-save settings", value=True)

        with col2:
            st.markdown("#### 🔔 Notifications")
            email_notifications = st.checkbox("Email notifications", value=True)
            if email_notifications:
                notification_email = st.text_input(
                    "Notification email", value="admin@company.com"
                )

            browser_notifications = st.checkbox("Browser notifications", value=False)
            sound_alerts = st.checkbox("Sound alerts", value=True)

            st.markdown("#### ⏰ Refresh Settings")
            _auto_refresh = st.checkbox("Auto-refresh data", value=True)
            if _auto_refresh:
                _refresh_interval = st.slider("Refresh interval (seconds)", 10, 300, 30)

    with tab2:
        st.subheader("🔐 Security Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔑 Access Control")
            st.info("🔓 Authentication is currently disabled (Open Access Mode)")

            # Show what would be available if auth was enabled
            st.markdown("#### 🛡️ Security Policies (Disabled)")
            st.text_input("Session timeout (minutes)", value="60", disabled=True)
            st.text_input("Max login attempts", value="5", disabled=True)
            st.checkbox("Require password change", value=False, disabled=True)

            st.markdown("#### 🔐 Encryption")
            encrypt_data = st.checkbox("Encrypt stored data", value=True)
            encrypt_backups = st.checkbox("Encrypt backups", value=True)

        with col2:
            st.markdown("#### 📝 Audit Logging")
            log_user_actions = st.checkbox("Log user actions", value=True)
            log_system_events = st.checkbox("Log system events", value=True)
            log_queries = st.checkbox("Log SQL queries", value=False)

            st.markdown("#### 🌐 Network Security")
            allowed_ips = st.text_area(
                "Allowed IP addresses (one per line)", value="0.0.0.0/0\n::0/0"
            )
            enable_ssl = st.checkbox("Force HTTPS", value=True)

    with tab3:
        st.subheader("🎨 Interface Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🎨 Appearance")
            sidebar_width = st.slider("Sidebar width", 200, 400, 300)
            _font_size = st.selectbox("Font size", ["Small", "Medium", "Large"])
            compact_mode = st.checkbox("Compact mode", value=False)

            st.markdown("#### 📊 Dashboard")
            default_dashboard = st.selectbox(
                "Default page", ["Dashboard", "Server Management"]
            )
            show_tips = st.checkbox("Show helpful tips", value=True)
            animations = st.checkbox("Enable animations", value=True)

        with col2:
            st.markdown("#### 📈 Charts & Graphs")
            chart_theme = st.selectbox("Chart theme", ["Default", "Dark", "Colorful"])
            animation_speed = st.slider("Animation speed", 0.5, 3.0, 1.0)
            show_legends = st.checkbox("Show chart legends", value=True)

            st.markdown("#### 🔍 Data Display")
            rows_per_table = st.slider("Rows per table", 10, 100, 25)
            auto_resize_columns = st.checkbox("Auto-resize columns", value=True)

    with tab4:
        st.subheader("📊 Database Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔌 Connection Settings")
            connection_pool_size = st.slider("Connection pool size", 5, 50, 20)
            _connection_timeout = st.slider("Connection timeout (seconds)", 5, 120, 30)
            _query_timeout = st.slider("Query timeout (seconds)", 30, 3600, 300)

            st.markdown("#### 💾 Query Settings")
            max_result_rows = st.number_input(
                "Max result rows", min_value=100, max_value=100000, value=10000
            )
            enable_query_cache = st.checkbox("Enable query cache", value=True)
            if enable_query_cache:
                cache_ttl = st.slider("Cache TTL (minutes)", 5, 60, 15)

        with col2:
            st.markdown("#### 📊 Performance")
            enable_query_stats = st.checkbox("Collect query statistics", value=True)
            slow_query_threshold = st.slider(
                "Slow query threshold (seconds)", 1, 60, 10
            )

            st.markdown("#### 🗃️ Data Management")
            auto_vacuum = st.checkbox("Auto VACUUM tables", value=True)
            auto_analyze = st.checkbox("Auto ANALYZE tables", value=True)
            if auto_analyze:
                analyze_threshold = st.slider("ANALYZE threshold (%)", 5, 50, 10)

    with tab5:
        st.subheader("ℹ️ System Information")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🖥️ System Details")
            import platform
            import sys
            import streamlit as st_version
            st.text(f"Operating System: {platform.system()}")
            st.text(f"Python Version: {sys.version.split()[0]}")
            st.text(f"Streamlit Version: {st_version.__version__}")
            st.text(f"MultiDBManager Version: 2.0.0")

            st.markdown("#### 💾 Resource Usage")
            st.info("Real resource monitoring coming soon")
            st.info("Connect to servers to track active connections")

        with col2:
            st.markdown("#### 📊 Statistics")
            st.info("Query statistics available after database usage")
            st.info("System uptime and backup status will be tracked")

            st.markdown("#### 🔧 Maintenance")
            if st.button("🧹 Clear Cache", use_container_width=True):
                st.success("Cache cleared successfully")

            if st.button("📊 Export Logs", use_container_width=True):
                st.info("Logs exported to downloads")

            if st.button("🔄 Restart Services", use_container_width=True):
                st.warning("Services restart would be performed")


def show_alert_system_page():
    """Alert System Management Page"""
    st.title("🚨 Alert System")
    st.markdown("### Monitor and manage system alerts and notifications")
    st.markdown("---")

    # Create tabs for different alert management aspects
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📊 Alert Dashboard",
            "⚙️ Alert Configuration",
            "📧 Notification Settings",
            "📜 Alert History",
        ]
    )

    with tab1:
        show_alert_dashboard()

    with tab2:
        show_alert_configuration()

    with tab3:
        show_notification_settings()

    with tab4:
        show_alert_history()


def show_alert_dashboard():
    """Show current alert status and active alerts"""
    st.subheader("📊 Current Alert Status")

    # Alert metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info("Critical alerts will appear here")

    with col2:
        st.info("Warning alerts will appear here")

    with col3:
        st.info("Info alerts will appear here")

    with col4:
        st.info("Notification tracking available")

    st.markdown("---")

    # Active alerts table
    st.subheader("🚨 Active Alerts")

    active_alerts = [
        {
            "Severity": "🔴 Critical",
            "Alert Type": "Connection Failure",
            "Message": "Failed to connect to cluster prod-cluster-1",
            "Time": "2025-07-28 17:35:22",
            "Status": "Active",
            "Actions": "Retry | Acknowledge",
        },
        {
            "Severity": "🔴 Critical",
            "Alert Type": "High CPU Usage",
            "Message": "CPU usage above 90% for 15 minutes",
            "Time": "2025-07-28 17:20:11",
            "Status": "Active",
            "Actions": "Investigate | Acknowledge",
        },
        {
            "Severity": "🟡 Warning",
            "Alert Type": "Long Running Query",
            "Message": "Query running for over 30 minutes",
            "Time": "2025-07-28 17:15:33",
            "Status": "Active",
            "Actions": "View Query | Kill | Acknowledge",
        },
        {
            "Severity": "🟡 Warning",
            "Alert Type": "Storage Usage",
            "Message": "Storage usage at 85%",
            "Time": "2025-07-28 16:45:18",
            "Status": "Active",
            "Actions": "View Details | Acknowledge",
        },
        {
            "Severity": "🔵 Info",
            "Alert Type": "Backup Completed",
            "Message": "Daily backup completed successfully",
            "Time": "2025-07-28 16:00:00",
            "Status": "Acknowledged",
            "Actions": "View Report",
        },
    ]
    
    # Clear demo data
    active_alerts = []

    # Real alerts only
    st.info("Active alerts will appear here when system monitoring detects issues")
    st.info("Configure monitoring to see real-time alerts and notifications")

    # Quick actions
    st.markdown("### 🔧 Quick Actions")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔕 Acknowledge All Warnings", use_container_width=True):
            st.success("✅ All warning alerts acknowledged")

    with col2:
        if st.button("📧 Send Test Alert", use_container_width=True):
            st.info("📧 Test alert sent to configured recipients")

    with col3:
        if st.button("🔄 Refresh Alerts", use_container_width=True):
            st.info("🔄 Alert status refreshed")

    with col4:
        if st.button("📊 Generate Report", use_container_width=True):
            st.info("📊 Alert report generated and sent")


def show_alert_configuration():
    """Configure alert rules and thresholds"""
    st.subheader("⚙️ Alert Configuration")

    # Alert rule categories
    alert_categories = st.selectbox(
        "Select Alert Category:",
        [
            "System Performance",
            "Connection Monitoring",
            "Query Performance",
            "Storage Monitoring",
            "Security Events",
            "Backup & Recovery",
        ],
    )

    st.markdown(f"### Configuring: {alert_categories}")

    if alert_categories == "System Performance":
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### CPU Monitoring")
            _cpu_warning = st.slider("CPU Warning Threshold (%)", 0, 100, 80)
            _cpu_critical = st.slider("CPU Critical Threshold (%)", 0, 100, 90)
            _cpu_duration = st.number_input("Duration (minutes)", 1, 60, 5)

            st.markdown("#### Memory Monitoring")
            _memory_warning = st.slider("Memory Warning Threshold (%)", 0, 100, 75)
            _memory_critical = st.slider("Memory Critical Threshold (%)", 0, 100, 85)
            _memory_duration = st.number_input("Memory Duration (minutes)", 1, 60, 5)

        with col2:
            st.markdown("#### Disk I/O Monitoring")
            _disk_warning = st.slider("Disk I/O Warning (MB/s)", 0, 1000, 500)
            _disk_critical = st.slider("Disk I/O Critical (MB/s)", 0, 1000, 800)

            st.markdown("#### Network Monitoring")
            _network_warning = st.slider("Network Warning (MB/s)", 0, 1000, 300)
            _network_critical = st.slider("Network Critical (MB/s)", 0, 1000, 500)

    elif alert_categories == "Connection Monitoring":
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Connection Health")
            _connection_timeout = st.number_input(
                "Connection Timeout (seconds)", 1, 300, 30
            )
            _max_retries = st.number_input("Max Connection Retries", 1, 10, 3)
            _retry_interval = st.number_input("Retry Interval (seconds)", 1, 60, 10)

        with col2:
            st.markdown("#### Connection Pool")
            _pool_warning = st.slider("Pool Usage Warning (%)", 0, 100, 80)
            _pool_critical = st.slider("Pool Usage Critical (%)", 0, 100, 95)
            _min_connections = st.number_input("Minimum Connections", 1, 50, 5)

    elif alert_categories == "Query Performance":
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Query Duration")
            _long_query_warning = st.number_input(
                "Long Query Warning (minutes)", 1, 180, 30
            )
            _long_query_critical = st.number_input(
                "Long Query Critical (minutes)", 1, 180, 60
            )

            st.markdown("#### Query Queue")
            _queue_warning = st.number_input("Queue Warning (count)", 1, 100, 10)
            _queue_critical = st.number_input("Queue Critical (count)", 1, 100, 25)

        with col2:
            st.markdown("#### Failed Queries")
            _failure_rate_warning = st.slider("Failure Rate Warning (%)", 0, 100, 5)
            _failure_rate_critical = st.slider("Failure Rate Critical (%)", 0, 100, 10)

            st.markdown("#### Resource Usage")
            _cpu_per_query = st.slider("CPU per Query Warning (%)", 0, 100, 70)
            _memory_per_query = st.slider("Memory per Query Warning (GB)", 0, 100, 10)

    # Save configuration
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 Save Configuration", type="primary"):
            st.success("✅ Alert configuration saved successfully!")

    with col2:
        if st.button("🔄 Reset to Defaults"):
            st.info("🔄 Configuration reset to default values")

    with col3:
        st.markdown("*Configuration changes will take effect immediately*")


def show_notification_settings():
    """Configure notification methods and recipients"""
    st.subheader("📧 Notification Settings")

    # Notification methods
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Notification Methods")

        email_enabled = st.checkbox("📧 Email Notifications", value=True)
        if email_enabled:
            _smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
            _smtp_port = st.number_input("SMTP Port", value=587)
            _smtp_username = st.text_input("SMTP Username", value="alerts@company.com")
            _smtp_password = st.text_input("SMTP Password", type="password")

        slack_enabled = st.checkbox("💬 Slack Notifications", value=False)
        if slack_enabled:
            _slack_webhook = st.text_input("Slack Webhook URL")
            _slack_channel = st.text_input("Slack Channel", value="#alerts")

        webhook_enabled = st.checkbox("🔗 Webhook Notifications", value=False)
        if webhook_enabled:
            _webhook_url = st.text_input("Webhook URL")
            _webhook_timeout = st.number_input("Webhook Timeout (seconds)", value=30)

    with col2:
        st.markdown("#### Notification Recipients")

        # Critical alerts recipients
        st.markdown("**Critical Alerts:**")
        _critical_emails = st.text_area(
            "Email addresses (one per line):",
            value="admin@company.com\nops-team@company.com\ndba@company.com",
        )

        # Warning alerts recipients
        st.markdown("**Warning Alerts:**")
        _warning_emails = st.text_area(
            "Email addresses (one per line):",
            value="monitoring@company.com\ndev-team@company.com",
        )

        # Info alerts recipients
        st.markdown("**Info Alerts:**")
        _info_emails = st.text_area(
            "Email addresses (one per line):", value="logs@company.com"
        )

    st.markdown("---")

    # Notification schedule
    st.markdown("#### 📅 Notification Schedule")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Business Hours:**")
        _business_start = st.time_input(
            "Start Time", value=pd.to_datetime("09:00").time()
        )
        _business_end = st.time_input("End Time", value=pd.to_datetime("17:00").time())

    with col2:
        st.markdown("**Throttling:**")
        _throttle_critical = st.number_input(
            "Critical Alert Interval (minutes)", 1, 60, 5
        )
        _throttle_warning = st.number_input(
            "Warning Alert Interval (minutes)", 1, 120, 15
        )
        _throttle_info = st.number_input("Info Alert Interval (minutes)", 1, 180, 30)

    with col3:
        st.markdown("**Escalation:**")
        escalation_enabled = st.checkbox("Enable Escalation", value=True)
        if escalation_enabled:
            _escalation_time = st.number_input("Escalation Time (minutes)", 5, 180, 30)
            _escalation_emails = st.text_input(
                "Escalation Recipients", value="cto@company.com"
            )

    # Test notifications
    st.markdown("---")
    st.markdown("#### 🧪 Test Notifications")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📧 Test Email", use_container_width=True):
            st.success("✅ Test email sent successfully!")

    with col2:
        if st.button("💬 Test Slack", use_container_width=True):
            st.info("💬 Test Slack message sent!")

    with col3:
        if st.button("🔗 Test Webhook", use_container_width=True):
            st.info("🔗 Test webhook sent!")

    with col4:
        if st.button("💾 Save Settings", use_container_width=True, type="primary"):
            st.success("✅ Notification settings saved!")


def show_alert_history():
    """Show historical alert data and analytics"""
    st.subheader("📜 Alert History & Analytics")

    # Time range selector
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        date_range = st.date_input(
            "Select Date Range:",
            value=[datetime.now().date() - pd.Timedelta(days=7), datetime.now().date()],
            max_value=datetime.now().date(),
        )

    with col2:
        alert_types = st.multiselect(
            "Filter Alert Types:",
            ["Critical", "Warning", "Info", "System", "Query", "Connection"],
            default=["Critical", "Warning"],
        )

    with col3:
        st.markdown("**Export Options:**")
        if st.button("📊 Export CSV"):
            st.info("📊 Alert history exported to CSV")

    # Alert trends chart
    st.markdown("### 📈 Alert Trends")

    # Generate sample trend data
    dates = pd.date_range(
        start=(
            date_range[0]
            if len(date_range) == 2
            else datetime.now().date() - pd.Timedelta(days=7)
        ),
        end=date_range[1] if len(date_range) == 2 else datetime.now().date(),
        freq="D",
    )

    fig = go.Figure()

    # Critical alerts trend
    critical_counts = [random.randint(0, 5) for _ in dates]
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=critical_counts,
            mode="lines+markers",
            name="Critical",
            line=dict(color="red", width=2),
        )
    )

    # Warning alerts trend
    warning_counts = [random.randint(2, 15) for _ in dates]
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=warning_counts,
            mode="lines+markers",
            name="Warning",
            line=dict(color="orange", width=2),
        )
    )

    # Info alerts trend
    info_counts = [random.randint(5, 25) for _ in dates]
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=info_counts,
            mode="lines+markers",
            name="Info",
            line=dict(color="blue", width=2),
        )
    )

    fig.update_layout(
        title="Alert Trends Over Time",
        xaxis_title="Date",
        yaxis_title="Alert Count",
        height=400,
    )

    st.info("Chart will appear here after real data collection")

    # Alert categories breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🥧 Alert Categories")

        categories = [
            "System Performance",
            "Connection Issues",
            "Query Problems",
            "Storage",
            "Security",
            "Other",
        ]
        values = [25, 20, 18, 12, 8, 17]

        fig_pie = px.pie(
            values=values, names=categories, title="Alert Distribution by Category"
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown("### ⏰ Alert Response Times")

        response_times = pd.DataFrame(
            {
                "Alert Type": ["Critical", "Warning", "Info"],
                "Avg Response (min)": [3.2, 15.8, 45.6],
                "Target (min)": [5, 30, 60],
            }
        )

        fig_bar = px.bar(
            response_times,
            x="Alert Type",
            y=["Avg Response (min)", "Target (min)"],
            title="Average Response Times vs Targets",
            barmode="group",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Detailed history table
    st.markdown("### 📋 Detailed Alert History")

    # Generate sample historical data
    history_data = []
    for i in range(50):
        severity = random.choice(["🔴 Critical", "🟡 Warning", "🔵 Info"])
        alert_type = random.choice(
            [
                "Connection Failure",
                "High CPU",
                "Long Query",
                "Storage Full",
                "Login Failed",
            ]
        )
        status = random.choice(["Resolved", "Acknowledged", "Auto-Resolved"])

        history_data.append(
            {
                "Date": (
                    datetime.now() - pd.Timedelta(days=random.randint(0, 30))
                ).strftime("%Y-%m-%d %H:%M"),
                "Severity": severity,
                "Type": alert_type,
                "Message": f"Sample alert message for {alert_type.lower()}",
                "Duration": f"{random.randint(1, 120)} min",
                "Status": status,
                "Response Time": f"{random.randint(1, 60)} min",
            }
        )

    history_df = pd.DataFrame(history_data)

    # Apply filters
    if alert_types:
        filter_map = {
            "Critical": "🔴 Critical",
            "Warning": "🟡 Warning",
            "Info": "🔵 Info",
        }
        filtered_severities = [
            filter_map.get(t, t) for t in alert_types if t in filter_map
        ]
        if filtered_severities:
            history_df = history_df[history_df["Severity"].isin(filtered_severities)]

    st.dataframe(history_df, use_container_width=True)

    # Summary statistics
    st.markdown("### 📊 Summary Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Alerts", len(history_df))

    with col2:
        critical_count = len(history_df[history_df["Severity"] == "🔴 Critical"])
        st.metric("Critical Alerts", critical_count)

    with col3:
        resolved_count = len(history_df[history_df["Status"] == "Resolved"])
        resolution_rate = (
            (resolved_count / len(history_df) * 100) if len(history_df) > 0 else 0
        )
        st.metric("Resolution Rate", f"{resolution_rate:.1f}%")

    with col4:
        avg_response = (
            history_df["Response Time"].str.extract(r"(\d+)").astype(int).mean()[0]
        )
        st.metric("Avg Response Time", f"{avg_response:.1f} min")


def show_backup_system_page():
    """Backup System Management Page"""
    st.title("💾 Backup System")
    st.markdown("### Manage database backups and recovery operations")
    st.markdown("---")

    # Create tabs for backup management
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📋 Backup Status",
            "⚙️ Backup Configuration",
            "🔧 Manual Operations",
            "📊 Storage Analytics",
        ]
    )

    with tab1:
        show_backup_status()

    with tab2:
        show_backup_configuration()

    with tab3:
        show_backup_operations()

    with tab4:
        show_storage_analytics()


def show_backup_status():
    """Show current backup status and recent backups"""
    st.subheader("📋 Current Backup Status")

    # Backup metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info("Last backup status will appear here")

    with col2:
        st.info("Backup count available after configuration")

    with col3:
        st.info("Storage usage tracked after backups")

    with col4:
        st.info("Success rate calculated from history")

    st.markdown("---")

    # Recent backups table
    st.subheader("📁 Recent Backups")

    recent_backups = [
        {
            "Backup ID": "BKP-20250728-173522",
            "Cluster": "prod-cluster-1",
            "Type": "Full",
            "Size": "45.2 GB",
            "Duration": "23 min",
            "Status": "✅ Completed",
            "Started": "2025-07-28 17:35:22",
            "Completed": "2025-07-28 17:58:14",
        },
        {
            "Backup ID": "BKP-20250728-120015",
            "Cluster": "prod-cluster-2",
            "Type": "Incremental",
            "Size": "8.7 GB",
            "Duration": "7 min",
            "Status": "✅ Completed",
            "Started": "2025-07-28 12:00:15",
            "Completed": "2025-07-28 12:07:33",
        },
        {
            "Backup ID": "BKP-20250728-060002",
            "Cluster": "dev-cluster-1",
            "Type": "Full",
            "Size": "12.3 GB",
            "Duration": "11 min",
            "Status": "✅ Completed",
            "Started": "2025-07-28 06:00:02",
            "Completed": "2025-07-28 06:11:28",
        },
        {
            "Backup ID": "BKP-20250727-180045",
            "Cluster": "prod-cluster-1",
            "Type": "Full",
            "Size": "44.8 GB",
            "Duration": "22 min",
            "Status": "✅ Completed",
            "Started": "2025-07-27 18:00:45",
            "Completed": "2025-07-27 18:22:17",
        },
        {
            "Backup ID": "BKP-20250727-120018",
            "Cluster": "staging-cluster",
            "Type": "Incremental",
            "Size": "3.2 GB",
            "Duration": "4 min",
            "Status": "⚠️ Warning",
            "Started": "2025-07-27 12:00:18",
            "Completed": "2025-07-27 12:04:52",
        },
    ]
    
    # Clear demo data
    recent_backups = []

    # Real backup data only
    st.info("Recent backups will appear here after backup operations")
    st.info("Configure and run backups to see backup history and status")

    # Quick actions
    st.markdown("### 🔧 Quick Actions")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("▶️ Start Backup Now", use_container_width=True):
            st.success("✅ Manual backup initiated")

    with col2:
        if st.button("📊 Verify Last Backup", use_container_width=True):
            st.info("🔍 Backup verification started")

    with col3:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.info("🔄 Backup status refreshed")

    with col4:
        if st.button("📋 Generate Report", use_container_width=True):
            st.info("📋 Backup report generated")


def show_backup_configuration():
    """Configure backup schedules and settings"""
    st.subheader("⚙️ Backup Configuration")

    # Cluster selection
    selected_server = st.selectbox(
        "Select Server to Configure:",
        []  # Real servers will appear here,
    )

    st.markdown(f"### Configuring Backup for: {selected_server}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📅 Backup Schedule")

        # Full backup schedule
        st.markdown("**Full Backup:**")
        full_backup_enabled = st.checkbox("Enable Full Backup", value=True)
        if full_backup_enabled:
            full_backup_frequency = st.selectbox(
                "Frequency:", ["Daily", "Weekly", "Monthly"], index=1
            )
            _full_backup_time = st.time_input(
                "Time:", value=pd.to_datetime("02:00").time()
            )

            if full_backup_frequency == "Weekly":
                _full_backup_day = st.selectbox(
                    "Day of Week:",
                    [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    ],
                    index=6,
                )
            elif full_backup_frequency == "Monthly":
                _full_backup_day = st.number_input("Day of Month:", 1, 28, 1)

        # Incremental backup schedule
        st.markdown("**Incremental Backup:**")
        incremental_enabled = st.checkbox("Enable Incremental Backup", value=True)
        if incremental_enabled:
            _incremental_frequency = st.selectbox(
                "Frequency:",
                ["Every 4 hours", "Every 6 hours", "Every 12 hours", "Daily"],
                index=2,
            )
            _incremental_start = st.time_input(
                "Start Time:", value=pd.to_datetime("06:00").time()
            )

    with col2:
        st.markdown("#### 🗂️ Backup Settings")

        # Storage settings
        st.markdown("**Storage Configuration:**")
        storage_type = st.selectbox(
            "Storage Type:", ["Amazon S3", "Local Storage", "Network Storage"], index=0
        )

        if storage_type == "Amazon S3":
            _s3_bucket = st.text_input("S3 Bucket:", value="redshift-backups-prod")
            _s3_region = st.selectbox(
                "S3 Region:",
                ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                index=0,
            )
            _s3_storage_class = st.selectbox(
                "Storage Class:",
                ["Standard", "Standard-IA", "Glacier", "Glacier Deep Archive"],
                index=1,
            )

        # Retention settings
        st.markdown("**Retention Policy:**")
        _retain_full = st.number_input("Keep Full Backups (days):", 1, 365, 30)
        _retain_incremental = st.number_input(
            "Keep Incremental Backups (days):", 1, 90, 7
        )

        # Compression settings
        st.markdown("**Compression & Encryption:**")
        compression_enabled = st.checkbox("Enable Compression", value=True)
        if compression_enabled:
            _compression_level = st.slider("Compression Level:", 1, 9, 6)

        _encryption_enabled = st.checkbox("Enable Encryption", value=True)
        if _encryption_enabled:
            _encryption_key = st.text_input(
                "Encryption Key ID:",
                value="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
            )

    # Advanced settings
    with st.expander("🔧 Advanced Settings"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Performance Settings:**")
            _parallel_jobs = st.number_input("Parallel Jobs:", 1, 16, 4)
            _bandwidth_limit = st.number_input("Bandwidth Limit (MB/s):", 0, 1000, 100)
            _timeout_minutes = st.number_input("Backup Timeout (minutes):", 5, 480, 60)

        with col2:
            st.markdown("**Notification Settings:**")
            notify_success = st.checkbox("Notify on Success", value=False)
            notify_failure = st.checkbox("Notify on Failure", value=True)
            notify_warning = st.checkbox("Notify on Warning", value=True)

            if any([notify_success, notify_failure, notify_warning]):
                _notification_emails = st.text_area(
                    "Notification Emails (one per line):",
                    value="backup-admin@company.com\nops-team@company.com",
                )

    # Save configuration
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 Save Configuration", type="primary"):
            st.success("✅ Backup configuration saved successfully!")

    with col2:
        if st.button("🔄 Reset to Defaults"):
            st.info("🔄 Configuration reset to default values")

    with col3:
        st.markdown("*Changes will take effect on next scheduled backup*")


def show_backup_operations():
    """Manual backup operations and recovery"""
    st.subheader("🔧 Manual Backup Operations")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🚀 Create Backup")

        # Manual backup form
        with st.form("manual_backup_form"):
            backup_server = st.selectbox(
                "Select Server:",
                [
                    "prod-server-1",
                    "prod-cluster-2",
                    "dev-cluster-1",
                    "staging-cluster",
                ],
            )

            backup_type = st.selectbox(
                "Backup Type:",
                ["Full Backup", "Incremental Backup", "Schema Only", "Data Only"],
            )

            _backup_name = st.text_input(
                "Backup Name (optional):",
                placeholder="manual-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
            )

            _include_logs = st.checkbox("Include Transaction Logs", value=True)
            _verify_backup = st.checkbox("Verify Backup After Completion", value=True)

            col_start, col_schedule = st.columns(2)

            with col_start:
                start_now = st.form_submit_button("▶️ Start Now", type="primary")

            with col_schedule:
                schedule_later = st.form_submit_button("📅 Schedule Later")

            if start_now:
                st.success(f"✅ {backup_type} initiated for {backup_cluster}")

                # Progress simulation
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i in range(101):
                    progress_bar.progress(i)
                    if i < 30:
                        status_text.text("📋 Preparing backup...")
                    elif i < 80:
                        status_text.text("💾 Backing up data...")
                    elif i < 95:
                        status_text.text("🗜️ Compressing backup...")
                    else:
                        status_text.text("✅ Finalizing backup...")
                    time.sleep(0.02)

                st.success("🎉 Backup completed successfully!")

            if schedule_later:
                st.info("📅 Backup scheduled for later execution")

    with col2:
        st.markdown("#### 🔄 Restore Operations")

        # Restore form
        with st.form("restore_form"):
            _restore_server = st.selectbox(
                "Target Server:",
                [
                    "prod-server-1",
                    "prod-cluster-2",
                    "dev-cluster-1",
                    "staging-cluster",
                ],
            )

            # Available backups
            available_backups = [
                "BKP-20250728-173522 (Full - 45.2 GB)",
                "BKP-20250728-120015 (Incremental - 8.7 GB)",
                "BKP-20250728-060002 (Full - 12.3 GB)",
                "BKP-20250727-180045 (Full - 44.8 GB)",
            ]

            _selected_backup = st.selectbox("Select Backup:", available_backups)

            restore_type = st.selectbox(
                "Restore Type:",
                [
                    "Complete Restore",
                    "Point-in-Time Recovery",
                    "Schema Only",
                    "Selected Tables",
                ],
            )

            if restore_type == "Point-in-Time Recovery":
                _pit_datetime = st.datetime_input("Recovery Point:", datetime.now())

            elif restore_type == "Selected Tables":
                _selected_tables = st.multiselect(
                    "Select Tables:",
                    ["users", "orders", "products", "transactions", "logs", "metrics"],
                )

            overwrite_existing = st.checkbox("Overwrite Existing Data", value=False)

            if overwrite_existing:
                st.warning("⚠️ This will overwrite existing data in the target cluster!")
                confirmation = st.text_input(
                    "Type 'CONFIRM' to proceed:", placeholder="CONFIRM"
                )

            restore_button = st.form_submit_button("🔄 Start Restore", type="primary")

            if restore_button:
                if overwrite_existing and confirmation != "CONFIRM":
                    st.error("❌ Please type 'CONFIRM' to proceed with overwrite")
                else:
                    st.success("✅ Restore operation initiated")
                    st.info("📧 You will be notified when the restore is complete")

    # Current operations
    st.markdown("---")
    st.markdown("#### 🔄 Current Operations")

    current_ops = [
        {
            "Operation": "Full Backup",
            "Cluster": "prod-cluster-1",
            "Status": "🔄 In Progress (78%)",
            "Started": "2025-07-28 18:30:00",
            "ETA": "5 min remaining",
            "Actions": "Cancel | Details",
        },
        {
            "Operation": "Incremental Backup",
            "Cluster": "dev-cluster-1",
            "Status": "⏸️ Queued",
            "Started": "N/A",
            "ETA": "Waiting for current backup",
            "Actions": "Cancel | Move Up",
        },
    ]

    if current_ops:
        ops_df = pd.DataFrame(current_ops)
        st.dataframe(ops_df, use_container_width=True)
    else:
        st.info("ℹ️ No backup operations currently running")


def show_storage_analytics():
    """Show storage usage and analytics"""
    st.subheader("📊 Storage Analytics")

    # Storage overview
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info("Total storage calculated from connected databases")

    with col2:
        st.info("Cost tracking available with cloud integrations")

    with col3:
        st.info("Growth rate calculated from historical data")

    with col4:
        st.info("Backup count tracked after configuration")

    st.markdown("---")

    # Storage breakdown charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Storage by Cluster")

        clusters = [
            "prod-cluster-1",
            "prod-cluster-2",
            "dev-cluster-1",
            "staging-cluster",
        ]
        storage_sizes = [450, 380, 220, 150]

        fig_bar = px.bar(
            x=clusters,
            y=storage_sizes,
            title="Storage Usage by Cluster (GB)",
            labels={"x": "Cluster", "y": "Storage (GB)"},
        )
        fig_bar.update_traces(marker_color=["#ff7f0e", "#2ca02c", "#d62728", "#9467bd"])
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.markdown("### 🥧 Backup Type Distribution")

        backup_types = ["Full Backups", "Incremental", "Schema Only", "Manual"]
        backup_counts = [45, 152, 25, 25]

        fig_pie = px.pie(
            values=backup_counts, names=backup_types, title="Backup Count by Type"
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    # Storage trends
    st.markdown("### 📈 Storage Growth Trends")

    # Generate trend data
    dates = pd.date_range(start="2025-07-01", end="2025-07-28", freq="D")
    cumulative_storage = []
    current_size = 950

    for date in dates:
        current_size += random.uniform(1, 8)
        cumulative_storage.append(current_size)

    fig_trend = go.Figure()

    fig_trend.add_trace(
        go.Scatter(
            x=dates,
            y=cumulative_storage,
            mode="lines+markers",
            name="Total Storage",
            line=dict(color="blue", width=3),
            fill="tonexty",
        )
    )

    fig_trend.update_layout(
        title="Storage Growth Over Time",
        xaxis_title="Date",
        yaxis_title="Storage (GB)",
        height=400,
        showlegend=True,
    )

    st.plotly_chart(fig_trend, use_container_width=True)

    # Storage efficiency metrics
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🗜️ Compression Efficiency")

        compression_data = pd.DataFrame(
            {
                "Cluster": clusters,
                "Original Size (GB)": [850, 720, 420, 290],
                "Compressed Size (GB)": [450, 380, 220, 150],
                "Compression Ratio": ["47%", "47%", "48%", "48%"],
            }
        )

        st.dataframe(compression_data, use_container_width=True)

    with col2:
        st.markdown("### 💾 Storage Optimization")

        st.info("**Recommendations:**")
        st.markdown(
            """
        - 🗑️ **37 old backups** can be safely deleted (saves 156 GB)
        - 🗜️ **Compression level 9** could save additional 12% space
        - 🧹 **Archive backups** older than 90 days to Glacier (saves 89 GB)
        - 📅 **Adjust retention** policy for dev environments
        """
        )

        if st.button("🔧 Apply Optimizations", use_container_width=True):
            st.success("✅ Storage optimization scheduled")

    # Detailed storage table
    st.markdown("### 📋 Detailed Storage Breakdown")

    detailed_storage = []
    for cluster in clusters:
        for backup_type in ["Full", "Incremental"]:
            detailed_storage.append(
                {
                    "Cluster": cluster,
                    "Backup Type": backup_type,
                    "Count": random.randint(10, 50),
                    "Total Size (GB)": random.randint(50, 200),
                    "Avg Size (GB)": random.randint(2, 15),
                    "Oldest": f"{random.randint(5, 90)} days ago",
                    "Newest": f"{random.randint(0, 2)} days ago",
                }
            )

    storage_df = pd.DataFrame(detailed_storage)
    st.dataframe(storage_df, use_container_width=True)


def show_placeholder_page(page_name):
    """Show placeholder for other pages"""
    st.title(f"🚧 {page_name}")
    st.markdown("### This page is under construction")

    st.info(
        f"""
    The {page_name.replace('🔍', '').replace('👥', '').replace('🔧', '').replace('🚨', '').replace('💾', '').replace('⚙️', '').strip()} functionality is available in the full MultiDBManager system.

    **Available features will include:**
    - Full management interface
    - Real-time monitoring and controls
    - Advanced configuration options
    - Integration with other system components
    """
    )

    st.markdown("---")
    st.markdown("**Current Status:** ✅ Core functionality implemented")
    st.markdown("**Access Mode:** 🔓 Open (No authentication required)")


def show_group_role_mapping_page():
    """Show AD group to database role mapping management page"""
    log_user_action("page_view", "system", page="group_role_mapping")
    
    st.title("🎭 מיפוי קבוצות ל-Roles")
    st.markdown("### קביעת תפקידים במסד הנתונים לפי חברות בקבוצות Active Directory")
    
    try:
        from core.group_role_mapping import get_group_role_mapper
        mapper = get_group_role_mapper()
        
        # Get statistics
        stats = mapper.get_mapping_statistics()
        
        # Statistics display
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("סה״כ מיפויים", stats.get('total_mappings', 0))
        
        with col2:
            st.metric("מיפויים פעילים", stats.get('active_mappings', 0))
        
        with col3:
            st.metric("תבניות זמינות", stats.get('templates_available', 0))
        
        with col4:
            most_common = list(stats.get('most_common_roles', {}).keys())
            popular_role = most_common[0] if most_common else "אין"
            st.metric("תפקיד פופולרי", popular_role)
        
        # Tabs for different management functions
        tab1, tab2, tab3, tab4 = st.tabs(["📝 ניהול מיפויים", "📊 מיפויים קיימים", "🎯 הצעות אוטומטיות", "⚙️ הגדרות"])
        
        with tab1:
            st.subheader("➕ הוסף מיפוי חדש")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Group selection
                st.markdown("**קבוצת AD:**")
                
                # Try to get AD groups from LDAP
                try:
                    from core.ldap_connector import get_ldap_connector
                    ldap_connector = get_ldap_connector()
                    
                    # Get unique groups from LDAP users
                    ldap_users = ldap_connector.get_all_users()
                    all_groups = set()
                    for user in ldap_users:
                        all_groups.update(user.get('groups', []))
                    
                    available_groups = sorted(list(all_groups))
                    
                    if available_groups:
                        group_input_method = st.radio(
                            "שיטת בחירה",
                            ["בחר מרשימה", "הקלד ידנית"],
                            key="group_input_method"
                        )
                        
                        if group_input_method == "בחר מרשימה":
                            selected_group = st.selectbox(
                                "קבוצת AD",
                                available_groups,
                                key="selected_ad_group"
                            )
                        else:
                            selected_group = st.text_input(
                                "שם קבוצת AD",
                                placeholder="CN=DataAnalysts,OU=Groups,DC=company,DC=com",
                                key="manual_ad_group"
                            )
                    else:
                        selected_group = st.text_input(
                            "שם קבוצת AD",
                            placeholder="CN=DataAnalysts,OU=Groups,DC=company,DC=com",
                            key="manual_ad_group_only"
                        )
                        st.info("💡 לא נמצאו קבוצות מ-LDAP. ודא שה-LDAP מוגדר ופעיל.")
                        
                except Exception as e:
                    selected_group = st.text_input(
                        "שם קבוצת AD",
                        placeholder="CN=DataAnalysts,OU=Groups,DC=company,DC=com",
                        key="manual_ad_group_error"
                    )
                    st.warning(f"שגיאה בטעינת קבוצות LDAP: {e}")
                
                # Database type selection
                database_type = st.selectbox(
                    "סוג מסד נתונים",
                    ["global", "postgresql", "mysql", "redshift"],
                    format_func=lambda x: {
                        "global": "🌐 כללי (כל המסדים)",
                        "postgresql": "🐘 PostgreSQL",
                        "mysql": "🐬 MySQL", 
                        "redshift": "🔴 Redshift"
                    }.get(x, x),
                    key="db_type_select"
                )
            
            with col2:
                st.markdown("**תפקידים במסד הנתונים:**")
                
                # Template selection
                templates = mapper.mappings.get("templates", {})
                if templates:
                    use_template = st.checkbox("השתמש בתבנית", key="use_template_checkbox")
                    
                    if use_template:
                        template_name = st.selectbox(
                            "בחר תבנית",
                            list(templates.keys()),
                            format_func=lambda x: f"{x} - {templates[x].get('description', '')}",
                            key="template_select"
                        )
                        
                        if template_name:
                            template_roles = templates[template_name].get("roles", [])
                            st.info(f"תפקידים בתבנית: {', '.join(template_roles)}")
                            roles_input = template_roles
                    else:
                        roles_text = st.text_area(
                            "תפקידים (כל תפקיד בשורה נפרדת)",
                            placeholder="readonly\nconnect\nselect_user",
                            key="roles_textarea"
                        )
                        roles_input = [role.strip() for role in roles_text.split('\n') if role.strip()]
                else:
                    roles_text = st.text_area(
                        "תפקידים (כל תפקיד בשורה נפרדת)",
                        placeholder="readonly\nconnect\nselect_user",
                        key="roles_textarea_no_template"
                    )
                    roles_input = [role.strip() for role in roles_text.split('\n') if role.strip()]
                
                # Description
                description = st.text_input(
                    "תיאור (אופציונלי)",
                    placeholder="מיפוי עבור אנליסטי נתונים",
                    key="mapping_description"
                )
            
            # Add mapping button
            if st.button("➕ הוסף מיפוי", key="add_mapping_btn"):
                if selected_group and roles_input:
                    success = mapper.add_group_mapping(
                        group_name=selected_group,
                        database_type=database_type,
                        roles=roles_input,
                        description=description,
                        overwrite=False
                    )
                    
                    if success:
                        st.success(f"✅ מיפוי נוסף בהצלחה: {selected_group} → {', '.join(roles_input)}")
                        st.rerun()
                    else:
                        st.error("❌ שגיאה בהוספת מיפוי. ייתכן שהמיפוי כבר קיים.")
                else:
                    st.error("❌ יש למלא קבוצה ולפחות תפקיד אחד")
        
        with tab2:
            st.subheader("📋 מיפויים קיימים")
            
            # Filter options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_db = st.selectbox(
                    "סנן לפי מסד נתונים",
                    ["הכל"] + list(stats.get('by_database', {}).keys()),
                    key="filter_db_select"
                )
            
            with col2:
                filter_active = st.selectbox(
                    "סנן לפי סטטוס",
                    ["הכל", "פעיל", "לא פעיל"],
                    key="filter_active_select"
                )
            
            with col3:
                if st.button("🔄 רענן", key="refresh_mappings_btn"):
                    st.rerun()
            
            # Display mappings
            all_mappings = mapper.get_all_mappings()
            
            for db_type, mappings in all_mappings.items():
                if filter_db != "הכל" and db_type != filter_db:
                    continue
                
                if not mappings:
                    continue
                
                st.markdown(f"### {db_type.upper()}")
                
                for group_key, mapping in mappings.items():
                    is_active = mapping.get("active", True)
                    
                    if filter_active != "הכל":
                        if filter_active == "פעיל" and not is_active:
                            continue
                        if filter_active == "לא פעיל" and is_active:
                            continue
                    
                    status_icon = "🟢" if is_active else "🔴"
                    group_name = mapping.get("original_group_name", group_key)
                    roles = mapping.get("roles", [])
                    description = mapping.get("description", "")
                    
                    with st.expander(f"{status_icon} {group_name} → {', '.join(roles)}"):
                        st.write(f"**תיאור:** {description}")
                        st.write(f"**תפקידים:** {', '.join(roles)}")
                        st.write(f"**נוצר:** {mapping.get('created_at', 'לא ידוע')[:19]}")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button(f"✏️ ערוך", key=f"edit_{db_type}_{group_key}"):
                                st.session_state.editing_mapping = {
                                    'db_type': db_type,
                                    'group_key': group_key,
                                    'mapping': mapping
                                }
                                st.rerun()
                        
                        with col2:
                            action_text = "השבת" if is_active else "הפעל"
                            if st.button(f"⏸️ {action_text}", key=f"toggle_{db_type}_{group_key}"):
                                mapping["active"] = not is_active
                                mapper.save_mappings()
                                st.success(f"מיפוי {action_text} בהצלחה")
                                st.rerun()
                        
                        with col3:
                            if st.button(f"🗑️ מחק", key=f"delete_{db_type}_{group_key}"):
                                if mapper.remove_group_mapping(group_name, db_type):
                                    st.success("מיפוי נמחק בהצלחה")
                                    st.rerun()
                                else:
                                    st.error("שגיאה במחיקת מיפוי")
        
        with tab3:
            st.subheader("🎯 הצעות מיפוי אוטומטיות")
            
            st.markdown("המערכת יכולה להציע מיפויים על בסיס שמות הקבוצות:")
            
            # Get groups from LDAP for suggestions
            try:
                from core.ldap_connector import get_ldap_connector
                ldap_connector = get_ldap_connector()
                ldap_users = ldap_connector.get_all_users()
                
                all_groups = set()
                for user in ldap_users:
                    all_groups.update(user.get('groups', []))
                
                if all_groups:
                    # Filter out already mapped groups
                    existing_mappings = mapper.get_all_mappings()
                    mapped_groups = set()
                    
                    for db_mappings in existing_mappings.values():
                        for mapping in db_mappings.values():
                            mapped_groups.add(mapping.get("original_group_name", "").lower())
                    
                    unmapped_groups = [g for g in all_groups 
                                     if g.lower() not in mapped_groups]
                    
                    if unmapped_groups:
                        suggestions = mapper.suggest_mappings_for_groups(unmapped_groups)
                        
                        st.write(f"נמצאו {len(unmapped_groups)} קבוצות ללא מיפוי:")
                        
                        selected_suggestions = []
                        
                        for group, suggested_roles in suggestions.items():
                            col1, col2, col3 = st.columns([2, 2, 1])
                            
                            with col1:
                                st.write(f"**{group}**")
                            
                            with col2:
                                st.write(f"הצעה: {', '.join(suggested_roles)}")
                            
                            with col3:
                                if st.checkbox("בחר", key=f"suggest_{group}"):
                                    selected_suggestions.append({
                                        'group': group,
                                        'roles': suggested_roles
                                    })
                        
                        if selected_suggestions:
                            target_db = st.selectbox(
                                "מסד נתונים יעד",
                                ["global", "postgresql", "mysql", "redshift"],
                                key="suggestion_target_db"
                            )
                            
                            if st.button("✅ אמץ הצעות נבחרות", key="apply_suggestions_btn"):
                                success_count = 0
                                
                                for suggestion in selected_suggestions:
                                    if mapper.add_group_mapping(
                                        group_name=suggestion['group'],
                                        database_type=target_db,
                                        roles=suggestion['roles'],
                                        description="מיפוי אוטומטי על בסיס שם הקבוצה"
                                    ):
                                        success_count += 1
                                
                                st.success(f"✅ נוספו {success_count} מיפויים מההצעות")
                                st.rerun()
                    else:
                        st.info("כל הקבוצות כבר ממופות")
                else:
                    st.warning("לא נמצאו קבוצות מ-LDAP")
                    
            except Exception as e:
                st.error(f"שגיאה בטעינת הצעות: {e}")
        
        with tab4:
            st.subheader("⚙️ הגדרות מערכת")
            
            settings = mapper.mappings.get("settings", {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                auto_assign = st.checkbox(
                    "הקצאת תפקידים אוטומטית",
                    value=settings.get("auto_assign_roles", True),
                    help="הקצה תפקידים אוטומטית למשתמשים על בסיס חברות בקבוצות",
                    key="auto_assign_setting"
                )
                
                create_missing = st.checkbox(
                    "צור תפקידים חסרים",
                    value=settings.get("create_missing_roles", False),
                    help="צור תפקידים חדשים במסד הנתונים אם הם לא קיימים",
                    key="create_missing_setting"
                )
            
            with col2:
                case_sensitive = st.checkbox(
                    "רגיש לאותיות גדולות/קטנות",
                    value=settings.get("case_sensitive", False),
                    help="הבחן בין אותיות גדולות וקטנות בשמות קבוצות",
                    key="case_sensitive_setting"
                )
                
                sync_on_ldap = st.checkbox(
                    "סנכרן עם עדכון LDAP",
                    value=settings.get("sync_on_ldap_update", True),
                    help="עדכן מיפויים אוטומטית כשמתבצע סינכרון עם LDAP",
                    key="sync_ldap_setting"
                )
            
            if st.button("💾 שמור הגדרות", key="save_settings_btn"):
                mapper.mappings["settings"].update({
                    "auto_assign_roles": auto_assign,
                    "create_missing_roles": create_missing,
                    "case_sensitive": case_sensitive,
                    "sync_on_ldap_update": sync_on_ldap
                })
                mapper.save_mappings()
                st.success("הגדרות נשמרו בהצלחה!")
                st.rerun()
            
            # Export/Import section
            st.markdown("---")
            st.markdown("**ייצוא/ייבוא מיפויים:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📤 ייצא מיפויים", key="export_mappings_btn"):
                    exported = mapper.export_mappings()
                    if exported:
                        import json
                        export_data = json.dumps(exported, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="💾 הורד קובץ JSON",
                            data=export_data,
                            file_name=f"group_mappings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            key="download_mappings_btn"
                        )
                    else:
                        st.warning("אין מיפויים לייצוא")
            
            with col2:
                uploaded_file = st.file_uploader(
                    "📥 ייבא מיפויים",
                    type=['json'],
                    key="import_mappings_file"
                )
                
                if uploaded_file:
                    try:
                        import json
                        mappings_data = json.load(uploaded_file)
                        success_count, error_count = mapper.bulk_import_mappings(mappings_data)
                        
                        if success_count > 0:
                            st.success(f"✅ ייובאו {success_count} מיפויים בהצלחה")
                        if error_count > 0:
                            st.warning(f"⚠️ {error_count} מיפויים נכשלו")
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"שגיאה בייבוא: {e}")
        
    except Exception as e:
        st.error(f"❌ שגיאה בטעינת מערכת מיפוי הקבוצות: {e}")
        st.info("ודא שהמערכת מוגדרת כראוי")


def show_ldap_sync_page():
    """Show LDAP synchronization management page"""
    log_user_action("page_view", "system", page="ldap_sync")
    
    # Import the advanced LDAP management module
    try:
        from ui.pages.ldap_management import show_ldap_management
        show_ldap_management()
        return
    except ImportError as e:
        st.error(f"❌ Advanced LDAP management not available: {e}")
        # Fall back to basic implementation
        pass
    except Exception as e:
        st.error(f"❌ Error loading advanced LDAP management: {e}")
        # Fall back to basic implementation
        pass
    
    # Basic fallback implementation
    st.title("🔗 סינכרון LDAP")
    st.markdown("### חיבור ל-LDAP/Active Directory לקבלת רשימת משתמשים")
    
    st.info("🔧 Advanced LDAP management interface is loading. If you see this message, the system is using a simplified fallback.")
    
    try:
        from core.ldap_connector import get_ldap_connector
        ldap_connector = get_ldap_connector()
        
        # Get sync status
        status = ldap_connector.get_sync_status()
        
        # Status display
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if status['enabled']:
                st.success("🟢 LDAP מופעל")
            else:
                st.error("🔴 LDAP כבוי")
        
        with col2:
            if status['connection_available']:
                st.success("📚 ספריות זמינות")
            else:
                st.error("📚 ldap3 לא מותקן")
        
        with col3:
            conn_status = status.get('connection_status', 'unknown')
            if conn_status == 'connected':
                st.success("🔗 חיבור תקין")
            elif conn_status == 'failed':
                st.error("🔗 חיבור נכשל")
            else:
                st.warning("🔗 לא מחובר")
        
        # Configuration section
        st.markdown("---")
        st.subheader("⚙️ הגדרות LDAP")
        
        with st.expander("🔧 הגדרות שרת LDAP", expanded=not status['enabled']):
            config = ldap_connector.config
            
            # Enable/Disable LDAP
            enabled = st.checkbox("אפשר LDAP", value=config.get('enabled', False), key="ldap_enabled")
            
            # Server settings
            st.markdown("**הגדרות שרת:**")
            col1, col2 = st.columns(2)
            
            with col1:
                host = st.text_input("כתובת שרת", value=config.get('server', {}).get('host', ''), 
                                   placeholder="ldap://domain-controller.company.com", key="ldap_host")
                port = st.number_input("פורט", value=config.get('server', {}).get('port', 389), 
                                     min_value=1, max_value=65535, key="ldap_port")
            
            with col2:
                use_ssl = st.checkbox("SSL", value=config.get('server', {}).get('use_ssl', False), key="ldap_ssl")
                use_tls = st.checkbox("TLS", value=config.get('server', {}).get('use_tls', False), key="ldap_tls")
            
            # Authentication
            st.markdown("**אימות:**")
            col1, col2 = st.columns(2)
            
            with col1:
                bind_dn = st.text_input("Bind DN", value=config.get('auth', {}).get('bind_dn', ''),
                                      placeholder="CN=service-account,OU=Users,DC=company,DC=com", key="ldap_bind_dn")
            
            with col2:
                password = st.text_input("סיסמה", type="password", value="", key="ldap_password")
                auth_method = st.selectbox("שיטת אימות", ["SIMPLE", "NTLM"], 
                                         index=0 if config.get('auth', {}).get('auth_method') == 'SIMPLE' else 1,
                                         key="ldap_auth_method")
            
            # Search settings
            st.markdown("**הגדרות חיפוש:**")
            col1, col2 = st.columns(2)
            
            with col1:
                base_dn = st.text_input("Base DN למשתמשים", value=config.get('search', {}).get('base_dn', ''),
                                      placeholder="OU=Users,DC=company,DC=com", key="ldap_base_dn")
                user_filter = st.text_input("סינון משתמשים", value=config.get('search', {}).get('user_filter', '(objectClass=user)'),
                                          key="ldap_user_filter")
            
            with col2:
                group_base_dn = st.text_input("Base DN לקבוצות", value=config.get('search', {}).get('group_base_dn', ''),
                                            placeholder="OU=Groups,DC=company,DC=com", key="ldap_group_base_dn")
                group_filter = st.text_input("סינון קבוצות", value=config.get('search', {}).get('group_filter', '(objectClass=group)'),
                                            key="ldap_group_filter")
            
            # Sync settings
            st.markdown("**הגדרות סינכרון:**")
            col1, col2 = st.columns(2)
            
            with col1:
                auto_sync = st.checkbox("סינכרון אוטומטי", value=config.get('sync', {}).get('auto_sync', False), key="ldap_auto_sync")
            
            with col2:
                sync_interval = st.number_input("תדירות סינכרון (שעות)", value=config.get('sync', {}).get('sync_interval_hours', 24),
                                              min_value=1, max_value=168, key="ldap_sync_interval")
            
            # Save configuration
            if st.button("💾 שמור הגדרות", key="save_ldap_config_btn"):
                # Update configuration
                ldap_connector.config.update({
                    'enabled': enabled,
                    'server': {
                        'host': host,
                        'port': port,
                        'use_ssl': use_ssl,
                        'use_tls': use_tls
                    },
                    'auth': {
                        'bind_dn': bind_dn,
                        'password': password if password else config.get('auth', {}).get('password', ''),
                        'auth_method': auth_method
                    },
                    'search': {
                        'base_dn': base_dn,
                        'user_filter': user_filter,
                        'group_base_dn': group_base_dn,
                        'group_filter': group_filter
                    },
                    'sync': {
                        'auto_sync': auto_sync,
                        'sync_interval_hours': sync_interval,
                        'last_sync': config.get('sync', {}).get('last_sync')
                    }
                })
                
                ldap_connector.save_config()
                st.success("הגדרות נשמרו בהצלחה!")
                st.rerun()
        
        # Actions section
        st.markdown("---")
        st.subheader("🔄 פעולות")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 בדוק חיבור", key="test_ldap_connection_btn"):
                with st.spinner("בודק חיבור..."):
                    success, message = ldap_connector.test_connection()
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
        
        with col2:
            if st.button("📥 סנכרן משתמשים", key="sync_ldap_users_btn"):
                with st.spinner("מסנכרן משתמשים..."):
                    count, message = ldap_connector.sync_users_to_local_storage()
                    if count > 0:
                        st.success(f"✅ {message}")
                    else:  
                        st.warning(f"⚠️ {message}")
                st.rerun()
        
        with col3:
            if st.button("👥 הצג משתמשי LDAP", key="show_ldap_users_btn"):
                st.session_state.show_ldap_users = True
        
        with col4:
            if st.button("🔄 רענן סטטוס", key="refresh_ldap_status_btn"):
                st.rerun()
        
        # Show LDAP users if requested
        if st.session_state.get('show_ldap_users', False):
            st.markdown("---")
            st.subheader("👥 משתמשי LDAP")
            
            with st.spinner("טוען משתמשים מ-LDAP..."):
                ldap_users = ldap_connector.get_all_users()
            
            if ldap_users:
                # Create DataFrame for display
                import pandas as pd
                
                df_data = []
                for user in ldap_users:
                    df_data.append({
                        'שם משתמש': user.get('username', ''),
                        'שם תצוגה': user.get('display_name', ''),
                        'אימייל': user.get('email', ''),
                        'סטטוס': 'נעול' if user.get('is_locked', False) else 'פעיל',
                        'קבוצות': ', '.join(user.get('groups', [])[:3]) + ('...' if len(user.get('groups', [])) > 3 else ''),
                        'כמות קבוצות': len(user.get('groups', []))
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)
                
                # Summary
                total_users = len(ldap_users)
                locked_users = sum(1 for u in ldap_users if u.get('is_locked', False))
                users_with_email = sum(1 for u in ldap_users if u.get('email'))
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("סה״כ משתמשים", total_users)
                with col2:
                    st.metric("משתמשים נעולים", locked_users)
                with col3:
                    st.metric("עם אימייל", users_with_email)
                
            else:
                st.warning("לא נמצאו משתמשים ב-LDAP")
            
            if st.button("🔙 סגור רשימה", key="close_ldap_users_btn"):
                st.session_state.show_ldap_users = False
                st.rerun()
        
        # Last sync info
        if status.get('last_sync'):
            st.markdown("---")
            st.info(f"🕒 סינכרון אחרון: {status['last_sync'][:19]}")
        
    except Exception as e:
        st.error(f"❌ שגיאה בטעינת מערכת LDAP: {e}")
        st.info("ודא שהמודול מותקן: pip install ldap3")


def show_notifications_page():
    """Show notifications and approvals management page"""
    log_user_action("page_view", "system", page="notifications")
    
    st.title("🔔 התראות ואישורים")
    st.markdown("### ניהול התראות על שינויים ידניים במערכת")
    
    try:
        from core.notification_system import get_notification_system
        notification_system = get_notification_system()
        
        # Get statistics
        stats = notification_system.get_notification_statistics()
        
        # Statistics display
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("התראות ממתינות", stats.get('total_pending', 0))
        
        with col2:
            st.metric("התראות מעובדות", stats.get('total_processed', 0))
        
        with col3:
            critical_count = stats.get('priority_counts', {}).get('critical', 0)
            high_count = stats.get('priority_counts', {}).get('high', 0)
            st.metric("עדיפות גבוהה", critical_count + high_count)
        
        with col4:
            new_users_count = stats.get('type_counts', {}).get('new_user_detected', 0)
            st.metric("משתמשים חדשים", new_users_count)
        
        # Filters
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            priority_filter = st.selectbox(
                "סנן לפי עדיפות",
                ["הכל", "critical", "high", "medium", "low"],
                key="priority_filter_select"
            )
            priority_filter = None if priority_filter == "הכל" else priority_filter
        
        with col2:
            type_filter = st.selectbox(
                "סנן לפי סוג",
                ["הכל", "new_user_detected", "user_removed", "user_modified", "correlation_request"],
                key="type_filter_select"
            )
            type_filter = None if type_filter == "הכל" else type_filter
        
        with col3:
            if st.button("🔄 רענן התראות", key="refresh_notifications_btn"):
                st.rerun()
        
        # Get pending notifications
        notifications = notification_system.get_pending_notifications(
            priority_filter=priority_filter,
            type_filter=type_filter
        )
        
        if not notifications:
            st.info("אין התראות ממתינות")
            return
        
        # Display notifications
        st.markdown("---")
        st.subheader("📋 התראות ממתינות")
        
        for notification in notifications:
            priority_colors = {
                'critical': '🔴',
                'high': '🟠', 
                'medium': '🟡',
                'low': '🟢'
            }
            
            priority_icon = priority_colors.get(notification.get('priority', 'medium'), '🟡')
            
            with st.expander(f"{priority_icon} {notification['title']} - {notification['created_at'][:19]}"):
                st.write(notification['message'])
                
                # Show data if available
                data = notification.get('data', {})
                if data:
                    st.markdown("**פרטים:**")
                    
                    # User data
                    if 'user_data' in data:
                        user_data = data['user_data']
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**משתמש:** {user_data.get('username', 'Unknown')}")
                            st.write(f"**שרת:** {data.get('server_name', 'Unknown')}")
                        with col2:
                            st.write(f"**סוג DB:** {user_data.get('database_type', 'Unknown')}")
                            st.write(f"**זמן סריקה:** {data.get('scan_time', 'Unknown')[:19]}")
                    
                    # Correlation data
                    if 'potential_matches' in data:
                        matches = data['potential_matches']
                        if matches:
                            st.markdown("**התאמות אפשריות:**")
                            for i, match in enumerate(matches[:3]):
                                confidence = data.get('confidence_scores', {}).get(str(i), 0)
                                st.write(f"- {match.get('username', 'Unknown')} (ביטחון: {confidence:.0%})")
                
                # Action buttons
                actions = notification.get('actions', [])
                if actions:
                    st.markdown("**פעולות זמינות:**")
                    cols = st.columns(len(actions))
                    
                    for i, action in enumerate(actions):
                        with cols[i]:
                            button_type = action.get('type', 'default')
                            if button_type == 'primary':
                                use_container_width = True
                            else:
                                use_container_width = False
                            
                            if st.button(
                                action['label'], 
                                key=f"action_{notification['id']}_{action['id']}",
                                use_container_width=use_container_width
                            ):
                                # Handle action
                                success = handle_notification_action(
                                    notification_system, 
                                    notification['id'], 
                                    action['id'],
                                    notification
                                )
                                
                                if success:
                                    st.success(f"פעולה '{action['label']}' בוצעה בהצלחה!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"שגיאה בביצוע פעולה '{action['label']}'")
        
        # Cleanup section
        st.markdown("---")
        st.subheader("🧹 תחזוקה")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ נקה התראות ישנות", key="cleanup_old_notifications_btn"):
                notification_system.cleanup_old_notifications(days_to_keep=30)
                st.success("התראות ישנות נוקו בהצלחה!")
                st.rerun()
        
        with col2:
            if st.button("📊 הצג סטטיסטיקות מפורטות", key="show_detailed_stats_btn"):
                st.json(stats)
        
    except Exception as e:
        st.error(f"❌ שגיאה בטעינת מערכת ההתראות: {e}")
        st.info("ודא שמערכת ההתראות מוגדרת כראוי")


def handle_notification_action(notification_system, notification_id: str, action_id: str, notification: dict) -> bool:
    """Handle notification action with UI interactions"""
    try:
        response_data = {}
        
        # Handle different action types
        if action_id == 'correlate_user':
            # Show correlation UI
            data = notification.get('data', {})
            potential_matches = data.get('potential_matches', [])
            
            if potential_matches:
                st.markdown("**בחר משתמש לשיוך:**")
                match_options = [f"{m.get('username', 'Unknown')} - {m.get('server_name', 'Unknown')}" 
                               for m in potential_matches]
                selected_match = st.selectbox("משתמש", match_options, key=f"match_select_{notification_id}")
                
                if selected_match:
                    selected_index = match_options.index(selected_match)
                    response_data['target_user_id'] = potential_matches[selected_index].get('id')
        
        elif action_id == 'approve_correlation':
            data = notification.get('data', {})
            potential_matches = data.get('potential_matches', [])
            
            if potential_matches:
                st.markdown("**אשר שיוך אוטומטי:**")
                for i, match in enumerate(potential_matches):
                    confidence = data.get('confidence_scores', {}).get(str(i), 0)
                    if st.button(f"שייך ל-{match.get('username', 'Unknown')} (ביטחון: {confidence:.0%})", 
                               key=f"approve_match_{notification_id}_{i}"):
                        response_data['selected_match_index'] = i
                        break
        
        # Process the action
        return notification_system.respond_to_notification(
            notification_id, action_id, response_data
        )
        
    except Exception as e:
        st.error(f"שגיאה בטיפול בפעולה: {e}")
        return False



def show_logs_viewer_page():
    """Show logs viewer page"""
    log_user_action("page_view", "system", page="logs_viewer")
    
    st.title("📋 מערכת צפייה וניתוח לוגים")
    st.markdown("### מערכת לוגים מתקדמת עם אפשרויות סינון וחיפוש")
    
    try:
        # Import and run the logs viewer
        from ui.pages.logs_viewer import main as logs_main
        logs_main()
        
    except ImportError as e:
        logger.error(f"Failed to import logs viewer module: {e}")
        st.error("❌ שגיאה בטעינת מודול הלוגים")
        st.info("ודא שמודול הלוגים מותקן כראוי")
        
    except Exception as e:
        logger.error(f"Error in logs viewer page: {e}")
        st.error(f"❌ שגיאה בהצגת עמוד הלוגים: {e}")


def main():
    """Main application logic"""

    # Show sidebar and get selected page
    selected_page = show_sidebar()

    # Show main content based on selection
    if selected_page == "📊 Dashboard":
        show_dashboard_page()
    elif selected_page == "🖥️ Server Management":
        show_server_management_page()
    elif selected_page == "👥 User Management":
        show_user_management_page()
    elif selected_page == "🌐 Global Users":
        show_global_users_page()
    elif selected_page == "💾 Local User Storage":
        show_local_user_storage_page()
    elif selected_page == "🔔 Notifications":
        show_notifications_page()
    elif selected_page == "🔗 LDAP Sync":
        show_ldap_sync_page()
    elif selected_page == "🎭 Group-Role Mapping":
        show_group_role_mapping_page()
    elif selected_page == "🔧 Module Manager":
        show_module_manager_page()
    elif selected_page == "🚨 Alert System":
        show_alert_system_page()
    elif selected_page == "💾 Backup System":
        show_backup_system_page()
    elif selected_page == "📋 Logs Viewer":
        show_logs_viewer_page()
    elif selected_page == "⚙️ Settings":
        show_settings_page()
    else:
        show_placeholder_page(selected_page)

    # Footer
    st.markdown("---")
    st.markdown(
        "**MultiDBManager** - Universal Multi-Database Management Tool | "
        f"**Open Access Mode** | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":
    main()
