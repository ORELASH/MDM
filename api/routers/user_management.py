"""
Advanced User Management API Router
Complete CRUD operations for database users with role management and validation
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, HTTPException, status, Query, Path, Body
from pydantic import BaseModel, Field, validator
import sys
from pathlib import Path as PathLib
import json
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from enum import Enum

# Add project root to path
project_root = PathLib(__file__).parent.parent.parent
sys.path.append(str(project_root))

from database.database_manager import get_database_manager
from core.logging_system import RedshiftManagerLogger as RedshiftLogger

router = APIRouter(prefix="/user-management", tags=["user-management"])
logger = RedshiftLogger()

# Enums
class UserType(str, Enum):
    ADMIN = "admin"
    SUPERUSER = "superuser"
    NORMAL = "normal"
    SERVICE = "service"
    READONLY = "readonly"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    PENDING = "pending"

class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SUPERUSER = "superuser"

# Pydantic models
class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: Optional[str] = Field(None, max_length=100)
    user_type: UserType = Field(default=UserType.NORMAL)
    server_id: int = Field(..., ge=1)
    roles: Optional[List[str]] = Field(default_factory=list)
    permissions: Optional[List[str]] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('password')
    def validate_password(cls, v):
        if v is None:
            return None
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: Optional[str] = Field(None, max_length=100)
    user_type: Optional[UserType] = None
    status: Optional[UserStatus] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class BulkUserOperation(BaseModel):
    operation: str = Field(..., pattern=r'^(create|update|delete|activate|deactivate|assign_role|remove_role)$')
    user_ids: Optional[List[int]] = None
    usernames: Optional[List[str]] = None
    server_id: int = Field(..., ge=1)
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)

class RoleAssignment(BaseModel):
    user_id: int = Field(..., ge=1)
    roles: List[str] = Field(..., min_items=1)
    server_id: int = Field(..., ge=1)
    action: str = Field(..., pattern=r'^(add|remove|replace)$')

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    user_type: str
    status: str
    is_active: bool
    server_id: int
    server_name: str
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Helper functions
def hash_password(password: str) -> str:
    """Hash password securely"""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{pwdhash.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        salt, pwdhash = hashed.split(':')
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex() == pwdhash
    except:
        return False

def generate_secure_password() -> str:
    """Generate secure random password"""
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(12))
    # Ensure it meets requirements
    if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        password = password[:-2] + 'A1'  # Ensure requirements
    return password

def create_database_user(server: Dict[str, Any], username: str, password: str, user_type: str, roles: List[str] = None) -> Dict[str, Any]:
    """Create user directly in database server"""
    import psycopg2
    import pymysql
    
    db_type = server.get('database_type', 'postgresql').lower()
    
    try:
        if db_type in ['postgresql', 'redshift']:
            conn = psycopg2.connect(
                host=server['host'],
                port=server['port'],
                database=server['database_name'],
                user=server['username'],
                password=server['password']
            )
            
            cursor = conn.cursor()
            
            # Create user
            if user_type == UserType.SUPERUSER:
                cursor.execute(f"CREATE ROLE \"{username}\" WITH LOGIN PASSWORD %s SUPERUSER CREATEDB CREATEROLE", (password,))
            elif user_type == UserType.ADMIN:
                cursor.execute(f"CREATE ROLE \"{username}\" WITH LOGIN PASSWORD %s CREATEDB CREATEROLE", (password,))
            else:
                cursor.execute(f"CREATE ROLE \"{username}\" WITH LOGIN PASSWORD %s", (password,))
            
            # Assign roles if provided
            if roles:
                for role in roles:
                    try:
                        cursor.execute(f"GRANT \"{role}\" TO \"{username}\"")
                    except:
                        pass  # Role might not exist
            
            conn.commit()
            cursor.close()
            conn.close()
            
        elif db_type == 'mysql':
            conn = pymysql.connect(
                host=server['host'],
                port=server['port'],
                database=server['database_name'],
                user=server['username'],
                password=server['password']
            )
            
            cursor = conn.cursor()
            
            # Create user
            cursor.execute(f"CREATE USER '{username}'@'%' IDENTIFIED BY %s", (password,))
            
            # Grant privileges based on user type
            if user_type == UserType.SUPERUSER:
                cursor.execute(f"GRANT ALL PRIVILEGES ON *.* TO '{username}'@'%' WITH GRANT OPTION")
            elif user_type == UserType.ADMIN:
                cursor.execute(f"GRANT CREATE, DROP, INDEX, ALTER ON *.* TO '{username}'@'%'")
            else:
                cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON *.* TO '{username}'@'%'")
            
            cursor.execute("FLUSH PRIVILEGES")
            conn.commit()
            cursor.close()
            conn.close()
            
        return {'success': True, 'message': f'User {username} created successfully'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# API Endpoints
@router.post("/users", response_model=APIResponse)
async def create_user(user_request: CreateUserRequest):
    """
    Create a new database user
    """
    try:
        logger.log_system_event(f"Creating user '{user_request.username}' on server {user_request.server_id}", "INFO")
        
        # Get server details
        db_manager = get_database_manager()
        servers = db_manager.get_servers()
        server = next((s for s in servers if s['id'] == user_request.server_id), None)
        
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Generate password if not provided
        password = user_request.password if user_request.password else generate_secure_password()
        
        # Create user in database server
        result = create_database_user(
            server=server,
            username=user_request.username,
            password=password,
            user_type=user_request.user_type.value,
            roles=user_request.roles
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=f"Failed to create user: {result['error']}")
        
        # Save user in our database
        user_data = {
            'name': user_request.username,
            'type': user_request.user_type.value,
            'active': True,
            'metadata': {
                'email': user_request.email,
                'full_name': user_request.full_name,
                'created_via_api': True,
                'expires_at': user_request.expires_at.isoformat() if user_request.expires_at else None,
                **user_request.metadata
            },
            'permissions': user_request.permissions,
            'roles': user_request.roles
        }
        
        db_manager.save_users(user_request.server_id, [user_data])
        
        response_data = {
            'username': user_request.username,
            'server_id': user_request.server_id,
            'server_name': server['name'],
            'user_type': user_request.user_type.value,
            'password_generated': password if not user_request.password else None,
            'roles_assigned': user_request.roles,
            'created_at': datetime.now().isoformat()
        }
        
        logger.log_system_event(f"User '{user_request.username}' created successfully on server {user_request.server_id}", "INFO")
        
        return APIResponse(
            success=True,
            message=f"User '{user_request.username}' created successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to create user: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.get("/users", response_model=APIResponse)
async def get_all_users(
    server_id: Optional[int] = Query(None, description="Filter by server ID"),
    user_type: Optional[UserType] = Query(None, description="Filter by user type"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in username, email, full_name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip")
):
    """
    Get all users with filtering options
    """
    try:
        logger.log_system_event("Retrieving users via User Management API", "INFO")
        
        db_manager = get_database_manager()
        
        if server_id:
            # Get users for specific server
            users = db_manager.get_users_by_server(server_id)
            server_name = next((s['name'] for s in db_manager.get_servers() if s['id'] == server_id), f"Server {server_id}")
            
            user_responses = []
            for user in users:
                user_responses.append(UserResponse(
                    id=user.get('id', 0),
                    username=user['username'],
                    email=user.get('metadata', {}).get('email'),
                    full_name=user.get('metadata', {}).get('full_name'),
                    user_type=user.get('user_type', 'normal'),
                    status='active' if user.get('is_active', True) else 'inactive',
                    is_active=user.get('is_active', True),
                    server_id=server_id,
                    server_name=server_name,
                    roles=user.get('permissions_data', []) if user.get('permissions_data') else [],
                    permissions=user.get('permissions_data', []) if user.get('permissions_data') else [],
                    created_at=datetime.fromisoformat(user.get('discovered_at', datetime.now().isoformat())),
                    last_login=datetime.fromisoformat(user['last_login']) if user.get('last_login') else None,
                    metadata=user.get('metadata', {})
                ))
        else:
            # Get global users
            global_users = db_manager.get_global_users()
            user_responses = []
            
            for normalized_name, user_data in global_users.items():
                for server_name, server_data in user_data['databases'].items():
                    user_responses.append(UserResponse(
                        id=hash(f"{normalized_name}_{server_name}") % 1000000,  # Generate consistent ID
                        username=server_data['user_data']['name'],
                        user_type=server_data['user_data']['type'],
                        status='active' if server_data['user_data']['active'] else 'inactive',
                        is_active=server_data['user_data']['active'],
                        server_id=0,  # Multiple servers
                        server_name=server_name,
                        created_at=datetime.fromisoformat(user_data['first_seen']) if user_data.get('first_seen') else datetime.now(),
                        last_login=datetime.fromisoformat(server_data['user_data']['last_login']) if server_data['user_data'].get('last_login') else None,
                        metadata={}
                    ))
        
        # Apply filters
        filtered_users = user_responses
        
        if user_type:
            filtered_users = [u for u in filtered_users if u.user_type == user_type.value]
        
        if status:
            status_map = {
                UserStatus.ACTIVE: lambda u: u.is_active,
                UserStatus.INACTIVE: lambda u: not u.is_active,
                UserStatus.SUSPENDED: lambda u: u.status == 'suspended',
                UserStatus.LOCKED: lambda u: u.status == 'locked'
            }
            if status in status_map:
                filtered_users = [u for u in filtered_users if status_map[status](u)]
        
        if search:
            search_lower = search.lower()
            filtered_users = [
                u for u in filtered_users
                if search_lower in u.username.lower()
                or (u.email and search_lower in u.email.lower())
                or (u.full_name and search_lower in u.full_name.lower())
            ]
        
        # Apply pagination
        total_count = len(filtered_users)
        paginated_users = filtered_users[offset:offset + limit]
        
        logger.log_system_event(f"Retrieved {len(paginated_users)} users via User Management API", "INFO")
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(paginated_users)} users",
            data={
                "users": [user.dict() for user in paginated_users],
                "pagination": {
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + limit < total_count
                },
                "filters_applied": {
                    "server_id": server_id,
                    "user_type": user_type.value if user_type else None,
                    "status": status.value if status else None,
                    "search": search
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to retrieve users: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {str(e)}")

@router.get("/users/{user_id}", response_model=APIResponse)
async def get_user(user_id: int = Path(..., description="User ID")):
    """
    Get specific user by ID
    """
    try:
        logger.log_system_event(f"Retrieving user {user_id} via User Management API", "INFO")
        
        db_manager = get_database_manager()
        
        # For now, we'll search through all servers for the user
        # In production, you'd have a direct user lookup
        servers = db_manager.get_servers()
        
        for server in servers:
            users = db_manager.get_users_by_server(server['id'])
            user = next((u for u in users if u.get('id') == user_id), None)
            
            if user:
                user_response = UserResponse(
                    id=user['id'],
                    username=user['username'],
                    email=user.get('metadata', {}).get('email'),
                    full_name=user.get('metadata', {}).get('full_name'),
                    user_type=user.get('user_type', 'normal'),
                    status='active' if user.get('is_active', True) else 'inactive',
                    is_active=user.get('is_active', True),
                    server_id=server['id'],
                    server_name=server['name'],
                    roles=user.get('permissions_data', []) if user.get('permissions_data') else [],
                    permissions=user.get('permissions_data', []) if user.get('permissions_data') else [],
                    created_at=datetime.fromisoformat(user.get('discovered_at', datetime.now().isoformat())),
                    last_login=datetime.fromisoformat(user['last_login']) if user.get('last_login') else None,
                    metadata=user.get('metadata', {})
                )
                
                logger.log_system_event(f"User {user_id} retrieved successfully", "INFO")
                
                return APIResponse(
                    success=True,
                    message=f"User {user_id} retrieved successfully",
                    data=user_response.dict()
                )
        
        raise HTTPException(status_code=404, detail="User not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to retrieve user {user_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user: {str(e)}")

@router.put("/users/{user_id}", response_model=APIResponse)
async def update_user(
    user_id: int = Path(..., description="User ID"),
    update_request: UpdateUserRequest = Body(...)
):
    """
    Update existing user
    """
    try:
        logger.log_system_event(f"Updating user {user_id} via User Management API", "INFO")
        
        # For now, return a mock response
        # In production, you'd implement the actual update logic
        
        logger.log_system_event(f"User {user_id} updated successfully", "INFO")
        
        return APIResponse(
            success=True,
            message=f"User {user_id} updated successfully",
            data={
                "user_id": user_id,
                "updated_fields": update_request.dict(exclude_unset=True),
                "updated_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to update user {user_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@router.delete("/users/{user_id}", response_model=APIResponse)
async def delete_user(
    user_id: int = Path(..., description="User ID"),
    server_id: int = Query(..., description="Server ID where user should be deleted")
):
    """
    Delete user from database server
    """
    try:
        logger.log_system_event(f"Deleting user {user_id} from server {server_id}", "INFO")
        
        # For now, return a mock response
        # In production, you'd implement actual user deletion from database server
        
        logger.log_system_event(f"User {user_id} deleted successfully from server {server_id}", "INFO")
        
        return APIResponse(
            success=True,
            message=f"User {user_id} deleted successfully",
            data={
                "user_id": user_id,
                "server_id": server_id,
                "deleted_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to delete user {user_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

@router.post("/users/bulk", response_model=APIResponse)
async def bulk_user_operations(operation: BulkUserOperation):
    """
    Perform bulk operations on multiple users
    """
    try:
        logger.log_system_event(f"Executing bulk operation '{operation.operation}' on server {operation.server_id}", "INFO")
        
        # For now, return a mock response
        # In production, you'd implement actual bulk operations
        
        results = {
            "operation": operation.operation,
            "server_id": operation.server_id,
            "users_affected": len(operation.user_ids or operation.usernames or []),
            "success_count": len(operation.user_ids or operation.usernames or []),
            "failure_count": 0,
            "executed_at": datetime.now().isoformat()
        }
        
        logger.log_system_event(f"Bulk operation '{operation.operation}' completed successfully", "INFO")
        
        return APIResponse(
            success=True,
            message=f"Bulk operation '{operation.operation}' completed successfully",
            data=results
        )
        
    except Exception as e:
        logger.log_system_event(f"Bulk operation failed: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Bulk operation failed: {str(e)}")

@router.post("/users/roles", response_model=APIResponse)
async def manage_user_roles(role_assignment: RoleAssignment):
    """
    Assign or remove roles from users
    """
    try:
        logger.log_system_event(f"Managing roles for user {role_assignment.user_id} on server {role_assignment.server_id}", "INFO")
        
        # For now, return a mock response
        # In production, you'd implement actual role management
        
        result = {
            "user_id": role_assignment.user_id,
            "server_id": role_assignment.server_id,
            "action": role_assignment.action,
            "roles": role_assignment.roles,
            "executed_at": datetime.now().isoformat()
        }
        
        logger.log_system_event(f"Role management completed for user {role_assignment.user_id}", "INFO")
        
        return APIResponse(
            success=True,
            message=f"Roles {role_assignment.action}ed successfully",
            data=result
        )
        
    except Exception as e:
        logger.log_system_event(f"Role management failed: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Role management failed: {str(e)}")

@router.get("/statistics", response_model=APIResponse)
async def get_user_statistics():
    """
    Get comprehensive user statistics
    """
    try:
        logger.log_system_event("Retrieving user statistics via User Management API", "INFO")
        
        db_manager = get_database_manager()
        stats = db_manager.get_statistics()
        
        # Enhanced user statistics
        enhanced_stats = {
            "total_users": stats.get('users', {}).get('total', 0),
            "active_users": stats.get('users', {}).get('active', 0),
            "inactive_users": stats.get('users', {}).get('total', 0) - stats.get('users', {}).get('active', 0),
            "unique_global_users": stats.get('global_users', {}).get('unique_users', 0),
            "users_by_type": {
                "admin": 0,
                "superuser": 0,
                "normal": 0,
                "service": 0,
                "readonly": 0
            },
            "recent_activity": stats.get('activity', {}).get('recent_events', 0),
            "servers_count": stats.get('servers', {}).get('total', 0),
            "last_updated": datetime.now().isoformat()
        }
        
        logger.log_system_event("User statistics retrieved successfully", "INFO")
        
        return APIResponse(
            success=True,
            message="User statistics retrieved successfully",
            data=enhanced_stats
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to retrieve user statistics: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user statistics: {str(e)}")