#!/usr/bin/env python3
"""
User Synchronization Manager
Handles bi-directional sync between local storage and remote databases
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from models.local_user_storage import LocalUserStorage
import json
import hashlib

class UserSyncManager:
    """Manages synchronization between local storage and remote databases"""
    
    def __init__(self, local_storage: LocalUserStorage = None):
        self.local_storage = local_storage or LocalUserStorage()
    
    def import_user_from_database(self, server_info: Dict, username: str, 
                                create_if_not_exists: bool = True) -> Tuple[bool, str]:
        """Import a user from remote database to local storage"""
        start_time = time.time()
        
        try:
            # Get user info from remote database
            success, user_data = self._get_remote_user_info(server_info, username)
            if not success:
                return False, f"Failed to get user info: {user_data}"
            
            # Create or update user in local storage
            local_user = self.local_storage.get_user(username)
            if not local_user and create_if_not_exists:
                user_id = self.local_storage.create_user(
                    username=username,
                    display_name=user_data.get('display_name', username),
                    description=f"Imported from {server_info['Name']}",
                    metadata={
                        'imported_from': server_info['Name'],
                        'import_date': datetime.now().isoformat(),
                        'user_type': user_data.get('type', 'unknown')
                    }
                )
            elif local_user:
                user_id = local_user['id']
            else:
                return False, "User not found in local storage and create_if_not_exists is False"
            
            # Add database connection
            self.local_storage.add_database_connection(
                user_id=user_id,
                database_name=server_info['Name'],
                database_type=self._get_database_type(server_info),
                connection_info={
                    'host': server_info['Host'],
                    'port': server_info['Port'],
                    'database': server_info['Database'],
                    'last_import': datetime.now().isoformat()
                }
            )
            
            # Generate and save CREATE USER command
            create_sql = self._generate_create_user_sql(server_info, username, user_data)
            self.local_storage.save_user_creation_command(
                user_id=user_id,
                database_name=server_info['Name'],
                database_type=self._get_database_type(server_info),
                create_sql=create_sql
            )
            
            # Import permissions
            permissions_imported = self._import_user_permissions(server_info, user_id, username)
            
            # Log success
            duration_ms = int((time.time() - start_time) * 1000)
            self.local_storage.log_sync_event(
                user_id=user_id,
                database_name=server_info['Name'],
                sync_type="user_import",
                sync_direction="from_remote",
                status="success",
                changes_made=1 + len(permissions_imported),
                sync_duration_ms=duration_ms
            )
            
            return True, f"User '{username}' imported successfully with {len(permissions_imported)} permissions"
            
        except Exception as e:
            # Log error
            if 'user_id' in locals():
                duration_ms = int((time.time() - start_time) * 1000)
                self.local_storage.log_sync_event(
                    user_id=user_id,
                    database_name=server_info['Name'],
                    sync_type="user_import",
                    sync_direction="from_remote",
                    status="error",
                    error_message=str(e),
                    sync_duration_ms=duration_ms
                )
            
            return False, f"Import failed: {str(e)}"
    
    def export_user_to_database(self, server_info: Dict, username: str, 
                               password: str = None, execute: bool = False) -> Tuple[bool, str]:
        """Export a user from local storage to remote database"""
        start_time = time.time()
        
        try:
            # Get user from local storage
            local_user = self.local_storage.get_user(username)
            if not local_user:
                return False, f"User '{username}' not found in local storage"
            
            user_id = local_user['id']
            database_name = server_info['Name']
            
            # Get CREATE USER command
            create_commands = self.local_storage.get_user_creation_commands(user_id, database_name)
            if not create_commands:
                return False, f"No CREATE USER command found for user '{username}' on database '{database_name}'"
            
            create_sql = create_commands[0]['create_user_sql']
            
            # Replace password if provided
            if password:
                create_sql = self._update_password_in_sql(create_sql, password, self._get_database_type(server_info))
            
            # Get permissions to apply
            permissions = self.local_storage.get_user_permissions(user_id, database_name)
            permission_sqls = self._generate_permission_sqls(permissions, username, self._get_database_type(server_info))
            
            all_commands = [create_sql] + permission_sqls
            
            if execute:
                # Execute commands on remote database
                success_count = 0
                errors = []
                
                for cmd in all_commands:
                    try:
                        from ui.open_dashboard import execute_sql_command
                        success, result = execute_sql_command(server_info, cmd, fetch_results=False)
                        if success:
                            success_count += 1
                        else:
                            errors.append(f"Command failed: {cmd[:50]}... - {result}")
                    except Exception as e:
                        errors.append(f"Execution error: {str(e)}")
                
                # Log result
                duration_ms = int((time.time() - start_time) * 1000)
                status = "success" if success_count == len(all_commands) else ("partial" if success_count > 0 else "error")
                
                self.local_storage.log_sync_event(
                    user_id=user_id,
                    database_name=database_name,
                    sync_type="user_export",
                    sync_direction="to_remote",
                    status=status,
                    changes_made=success_count,
                    error_message="; ".join(errors) if errors else None,
                    sync_duration_ms=duration_ms
                )
                
                if errors:
                    return success_count > 0, f"Export partially successful: {success_count}/{len(all_commands)} commands executed. Errors: {'; '.join(errors)}"
                else:
                    return True, f"User '{username}' exported successfully ({success_count} commands executed)"
            else:
                # Just return the commands for preview
                return True, {
                    "create_command": create_sql,
                    "permission_commands": permission_sqls,
                    "total_commands": len(all_commands)
                }
                
        except Exception as e:
            # Log error
            if 'user_id' in locals():
                duration_ms = int((time.time() - start_time) * 1000)
                self.local_storage.log_sync_event(
                    user_id=user_id,
                    database_name=server_info['Name'],
                    sync_type="user_export",
                    sync_direction="to_remote",
                    status="error",
                    error_message=str(e),
                    sync_duration_ms=duration_ms
                )
            
            return False, f"Export failed: {str(e)}"
    
    def sync_all_users_from_database(self, server_info: Dict) -> Tuple[bool, Dict]:
        """Sync all users from a remote database"""
        start_time = time.time()
        results = {
            "users_imported": 0,
            "users_updated": 0,
            "permissions_synced": 0,
            "errors": []
        }
        
        try:
            # Get all users from remote database
            success, remote_users = self._get_all_remote_users(server_info)
            if not success:
                return False, {"error": f"Failed to get remote users: {remote_users}"}
            
            for user_data in remote_users:
                username = user_data.get('name')
                if not username or username == 'Connection failed':
                    continue
                
                try:
                    success, message = self.import_user_from_database(server_info, username, create_if_not_exists=True)
                    if success:
                        if "imported successfully" in message:
                            results["users_imported"] += 1
                        else:
                            results["users_updated"] += 1
                        
                        # Count permissions synced
                        local_user = self.local_storage.get_user(username)
                        if local_user:
                            perms = self.local_storage.get_user_permissions(local_user['id'], server_info['Name'])
                            results["permissions_synced"] += len(perms)
                    else:
                        results["errors"].append(f"{username}: {message}")
                        
                except Exception as e:
                    results["errors"].append(f"{username}: {str(e)}")
            
            # Log overall sync
            duration_ms = int((time.time() - start_time) * 1000)
            self.local_storage.log_sync_event(
                user_id=None,
                database_name=server_info['Name'],
                sync_type="full_sync",
                sync_direction="from_remote",
                status="success" if len(results["errors"]) == 0 else "partial",
                changes_made=results["users_imported"] + results["users_updated"],
                error_message="; ".join(results["errors"][:5]) if results["errors"] else None,
                sync_duration_ms=duration_ms
            )
            
            return True, results
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def _get_remote_user_info(self, server_info: Dict, username: str) -> Tuple[bool, Dict]:
        """Get user information from remote database"""
        try:
            from ui.open_dashboard import get_user_permissions
            
            success, permissions_data = get_user_permissions(server_info, username)
            if success:
                return True, {
                    'display_name': username,
                    'type': permissions_data.get('user_properties', {}).get('type', 'normal'),
                    'active': permissions_data.get('user_properties', {}).get('active', True),
                    'permissions': permissions_data
                }
            else:
                return False, permissions_data
                
        except Exception as e:
            return False, str(e)
    
    def _get_all_remote_users(self, server_info: Dict) -> Tuple[bool, List]:
        """Get all users from remote database"""
        try:
            # Check if server has scan results
            if 'scan_results' in server_info and 'users' in server_info['scan_results']:
                users = server_info['scan_results']['users']
                valid_users = [u for u in users if isinstance(u, dict) and 
                             u.get('name') != 'Connection failed' and u.get('type') != 'error']
                return True, valid_users
            else:
                # Try to load from session files
                from ui.open_dashboard import GlobalUserManager
                gum = GlobalUserManager()
                users = gum._load_users_from_session_files(server_info['Name'])
                return True, users
                
        except Exception as e:
            return False, str(e)
    
    def _import_user_permissions(self, server_info: Dict, user_id: int, username: str) -> List[Dict]:
        """Import user permissions from remote database"""
        try:
            from ui.open_dashboard import get_user_permissions
            
            success, permissions_data = get_user_permissions(server_info, username)
            if not success:
                return []
            
            permissions = []
            database_name = server_info['Name']
            
            # Process roles
            for role in permissions_data.get('roles', []):
                permissions.append({
                    'permission_type': 'role',
                    'resource_name': role,
                    'privilege': 'MEMBER',
                    'grant_option': False,
                    'metadata': {'source': 'role_membership'}
                })
            
            # Process table permissions
            for perm in permissions_data.get('table_permissions', []):
                permissions.append({
                    'permission_type': 'table',
                    'resource_name': perm.get('full_name', ''),
                    'privilege': perm.get('privilege', ''),
                    'grant_option': perm.get('grantable', False),
                    'metadata': {'source': 'table_permission', 'schema': perm.get('schema', '')}
                })
            
            # Process schema permissions
            for perm in permissions_data.get('schema_permissions', []):
                permissions.append({
                    'permission_type': 'schema',
                    'resource_name': perm.get('schema', ''),
                    'privilege': perm.get('privilege', ''),
                    'grant_option': perm.get('grantable', False),
                    'metadata': {'source': 'schema_permission'}
                })
            
            # Process column permissions
            for perm in permissions_data.get('column_permissions', []):
                permissions.append({
                    'permission_type': 'column',
                    'resource_name': f"{perm.get('schema', '')}.{perm.get('table', '')}.{perm.get('column', '')}",
                    'privilege': perm.get('privilege', ''),
                    'grant_option': perm.get('grantable', False),
                    'metadata': {
                        'source': 'column_permission',
                        'schema': perm.get('schema', ''),
                        'table': perm.get('table', ''),
                        'column': perm.get('column', '')
                    }
                })
            
            # Save permissions to local storage
            self.local_storage.save_user_permissions(user_id, database_name, permissions)
            
            return permissions
            
        except Exception as e:
            print(f"Error importing permissions for user {username}: {e}")
            return []
    
    def _generate_create_user_sql(self, server_info: Dict, username: str, user_data: Dict) -> str:
        """Generate CREATE USER SQL command"""
        db_type = self._get_database_type(server_info)
        user_type = user_data.get('type', 'normal')
        
        if db_type in ['postgresql', 'redshift']:
            sql = f'CREATE ROLE "{username}" WITH LOGIN'
            
            if user_type == 'superuser':
                sql += ' SUPERUSER'
            
            # Add placeholder for password
            sql += " PASSWORD '[PASSWORD_PLACEHOLDER]';"
            
        elif db_type == 'mysql':
            sql = f"CREATE USER '{username}'@'%' IDENTIFIED BY '[PASSWORD_PLACEHOLDER]';"
            
        else:
            sql = f"-- Unsupported database type: {db_type}\n-- CREATE USER '{username}' [PASSWORD_PLACEHOLDER];"
        
        return sql
    
    def _generate_permission_sqls(self, permissions: List[Dict], username: str, db_type: str) -> List[str]:
        """Generate SQL commands for permissions"""
        sqls = []
        
        for perm in permissions:
            try:
                if perm['permission_type'] == 'role':
                    if db_type in ['postgresql', 'redshift']:
                        sqls.append(f'GRANT "{perm["resource_name"]}" TO "{username}";')
                    elif db_type == 'mysql':
                        sqls.append(f"GRANT {perm['resource_name']} TO '{username}'@'%';")
                
                elif perm['permission_type'] == 'table':
                    if db_type in ['postgresql', 'redshift']:
                        sqls.append(f'GRANT {perm["privilege"]} ON {perm["resource_name"]} TO "{username}";')
                    elif db_type == 'mysql':
                        sqls.append(f"GRANT {perm['privilege']} ON {perm['resource_name']} TO '{username}'@'%';")
                
                elif perm['permission_type'] == 'schema':
                    if db_type in ['postgresql', 'redshift']:
                        sqls.append(f'GRANT {perm["privilege"]} ON SCHEMA "{perm["resource_name"]}" TO "{username}";')
                
                elif perm['permission_type'] == 'column':
                    metadata = perm.get('metadata', {})
                    if metadata.get('schema') and metadata.get('table') and metadata.get('column'):
                        table_name = f'"{metadata["schema"]}"."{metadata["table"]}"'
                        column_name = f'"{metadata["column"]}"'
                        if db_type in ['postgresql', 'redshift']:
                            sqls.append(f'GRANT {perm["privilege"]} ({column_name}) ON {table_name} TO "{username}";')
                
            except Exception as e:
                sqls.append(f"-- Error generating permission SQL: {str(e)}")
        
        return sqls
    
    def _update_password_in_sql(self, sql: str, password: str, db_type: str) -> str:
        """Update password placeholder in SQL command"""
        return sql.replace('[PASSWORD_PLACEHOLDER]', password)
    
    def _get_database_type(self, server_info: Dict) -> str:
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
    
    def get_user_sync_status(self, username: str) -> Dict:
        """Get synchronization status for a user"""
        local_user = self.local_storage.get_user(username)
        if not local_user:
            return {"status": "not_found", "message": "User not found in local storage"}
        
        user_id = local_user['id']
        databases = self.local_storage.get_user_databases(user_id)
        sync_history = self.local_storage.get_sync_history(user_id=user_id, limit=10)
        
        return {
            "status": "found",
            "user_info": local_user,
            "databases": databases,
            "recent_sync_events": sync_history,
            "last_sync": sync_history[0] if sync_history else None
        }
    
    def cleanup_old_sync_data(self, days_to_keep: int = 30) -> Tuple[bool, str]:
        """Clean up old synchronization data"""
        try:
            import sqlite3
            
            with sqlite3.connect(self.local_storage.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old sync history
                cursor.execute('''
                    DELETE FROM sync_history 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days_to_keep))
                
                deleted_count = cursor.rowcount
                
                return True, f"Cleaned up {deleted_count} old sync records"
                
        except Exception as e:
            return False, f"Cleanup failed: {str(e)}"