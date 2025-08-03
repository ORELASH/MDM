"""
Security Manager for RedshiftManager Modular System
Handles permissions, authentication, and authorization.
"""

from typing import Dict, List, Set, Optional, Any
import logging
from enum import Enum


class PermissionLevel(Enum):
    """Permission levels"""
    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3
    SUPER_ADMIN = 4


class SecurityManager:
    """
    Basic security manager for the modular system.
    In production, this would integrate with a real authentication system.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("core.security")
        
        # Default permissions for development/testing
        self.default_permissions = {
            "query.read", "query.execute", "analytics.view", "analytics.basic",
            "cluster.read", "user.read", "module.load", "module.activate"
        }
        
        # User permissions (in production, this would come from database)
        self.user_permissions: Dict[str, Set[str]] = {
            "admin": {"admin.all", "system.import"}  # Super admin
        }
        
        # Role-based permissions
        self.role_permissions: Dict[str, Set[str]] = {
            "viewer": {"query.read", "analytics.view"},
            "analyst": {"query.read", "query.execute", "analytics.view", "analytics.basic"},
            "admin": {"admin.all", "system.import"},
            "module_developer": {"module.load", "module.activate", "module.create"}
        }
        
        # User roles (in production, this would come from database)
        self.user_roles: Dict[str, Set[str]] = {
            "admin": {"admin"}
        }
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        try:
            # Check for super admin permission
            user_perms = self.user_permissions.get(user_id, set())
            if "admin.all" in user_perms:
                return True
            
            # Check direct user permissions
            if permission in user_perms:
                return True
            
            # Check role-based permissions
            user_roles = self.user_roles.get(user_id, set())
            for role in user_roles:
                role_perms = self.role_permissions.get(role, set())
                if permission in role_perms:
                    return True
                if "admin.all" in role_perms:
                    return True
            
            # Log permission check for audit
            self.logger.debug(f"Permission check: user={user_id}, permission={permission}, result=False")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking permission for user {user_id}: {e}")
            return False
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user"""
        permissions = set()
        
        # Add direct permissions
        permissions.update(self.user_permissions.get(user_id, set()))
        
        # Add role-based permissions
        user_roles = self.user_roles.get(user_id, set())
        for role in user_roles:
            permissions.update(self.role_permissions.get(role, set()))
        
        return permissions
    
    def add_user_permission(self, user_id: str, permission: str):
        """Add permission to user"""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = set()
        
        self.user_permissions[user_id].add(permission)
        self.logger.info(f"Added permission '{permission}' to user '{user_id}'")
    
    def remove_user_permission(self, user_id: str, permission: str):
        """Remove permission from user"""
        if user_id in self.user_permissions:
            self.user_permissions[user_id].discard(permission)
            self.logger.info(f"Removed permission '{permission}' from user '{user_id}'")
    
    def assign_role(self, user_id: str, role: str):
        """Assign role to user"""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        
        self.user_roles[user_id].add(role)
        self.logger.info(f"Assigned role '{role}' to user '{user_id}'")
    
    def remove_role(self, user_id: str, role: str):
        """Remove role from user"""
        if user_id in self.user_roles:
            self.user_roles[user_id].discard(role)
            self.logger.info(f"Removed role '{role}' from user '{user_id}'")
    
    def create_role(self, role_name: str, permissions: Set[str]):
        """Create a new role with permissions"""
        self.role_permissions[role_name] = permissions.copy()
        self.logger.info(f"Created role '{role_name}' with {len(permissions)} permissions")
    
    def get_role_permissions(self, role: str) -> Set[str]:
        """Get permissions for a role"""
        return self.role_permissions.get(role, set()).copy()
    
    def list_users(self) -> List[str]:
        """List all users"""
        users = set()
        users.update(self.user_permissions.keys())
        users.update(self.user_roles.keys())
        return list(users)
    
    def list_roles(self) -> List[str]:
        """List all roles"""
        return list(self.role_permissions.keys())
    
    def validate_permission_string(self, permission: str) -> bool:
        """Validate permission string format"""
        # Basic validation - should be in format "resource.action"
        parts = permission.split('.')
        if len(parts) != 2:
            return False
        
        resource, action = parts
        if not resource or not action:
            return False
        
        # Check for valid characters
        valid_chars = set('abcdefghijklmnopqrstuvwxyz0123456789_')
        if not all(c in valid_chars for c in resource.lower()):
            return False
        if not all(c in valid_chars for c in action.lower()):
            return False
        
        return True
    
    def get_security_report(self) -> Dict[str, Any]:
        """Get security configuration report"""
        return {
            "total_users": len(self.list_users()),
            "total_roles": len(self.list_roles()),
            "total_permissions": len(set().union(*self.role_permissions.values(), *self.user_permissions.values())),
            "users_with_admin": len([
                user for user in self.list_users() 
                if self.has_permission(user, "admin.all")
            ]),
            "roles": {
                role: len(perms) for role, perms in self.role_permissions.items()
            }
        }
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export security configuration"""
        return {
            "user_permissions": {
                user: list(perms) for user, perms in self.user_permissions.items()
            },
            "role_permissions": {
                role: list(perms) for role, perms in self.role_permissions.items()
            },
            "user_roles": {
                user: list(roles) for user, roles in self.user_roles.items()
            }
        }
    
    def import_configuration(self, config: Dict[str, Any]):
        """Import security configuration"""
        try:
            if "user_permissions" in config:
                self.user_permissions = {
                    user: set(perms) for user, perms in config["user_permissions"].items()
                }
            
            if "role_permissions" in config:
                self.role_permissions = {
                    role: set(perms) for role, perms in config["role_permissions"].items()
                }
            
            if "user_roles" in config:
                self.user_roles = {
                    user: set(roles) for user, roles in config["user_roles"].items()
                }
            
            self.logger.info("Security configuration imported successfully")
            
        except Exception as e:
            self.logger.error(f"Error importing security configuration: {e}")
            raise


# Default permission definitions
class Permissions:
    """Standard permission definitions"""
    
    # Query permissions
    QUERY_READ = "query.read"
    QUERY_EXECUTE = "query.execute"
    QUERY_MODIFY = "query.modify"
    QUERY_DELETE = "query.delete"
    
    # Analytics permissions
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_BASIC = "analytics.basic"
    ANALYTICS_ADVANCED = "analytics.advanced"
    
    # Cluster permissions
    CLUSTER_READ = "cluster.read"
    CLUSTER_WRITE = "cluster.write"
    CLUSTER_DELETE = "cluster.delete"
    CLUSTER_MANAGE = "cluster.manage"
    
    # User permissions
    USER_READ = "user.read"
    USER_WRITE = "user.write"
    USER_DELETE = "user.delete"
    USER_MANAGE = "user.manage"
    
    # Module permissions
    MODULE_LOAD = "module.load"
    MODULE_ACTIVATE = "module.activate"
    MODULE_CREATE = "module.create"
    MODULE_DELETE = "module.delete"
    
    # System permissions
    SYSTEM_ADMIN = "system.admin"
    SYSTEM_IMPORT = "system.import"
    ADMIN_ALL = "admin.all"


def create_default_security_manager() -> SecurityManager:
    """Create a security manager with sensible defaults"""
    manager = SecurityManager()
    return manager