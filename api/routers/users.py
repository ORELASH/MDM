"""
User Management API Router
CRUD operations for database users across all servers
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from database.database_manager import get_database_manager
from core.logging_system import RedshiftManagerLogger as RedshiftLogger

router = APIRouter(prefix="/users", tags=["users"])
logger = RedshiftLogger()

# Pydantic models
class UserInfo(BaseModel):
    username: str
    user_type: str = "normal"
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    permissions_data: List[str] = Field(default_factory=list)

class UserFilter(BaseModel):
    server_id: Optional[int] = None
    is_active: Optional[bool] = None
    user_type: Optional[str] = None
    search: Optional[str] = None

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

@router.get("/")
async def get_all_users(
    server_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    user_type: Optional[str] = None,
    search: Optional[str] = None
):
    """
    Get all users across servers with optional filtering
    """
    try:
        db_manager = get_database_manager()
        
        if server_id:
            # Get users for specific server
            users = db_manager.get_users_by_server(server_id)
        else:
            # Get global users
            global_users_dict = db_manager.get_global_users()
            users = []
            
            # Convert global users dict to list format
            for normalized_name, user_data in global_users_dict.items():
                # Flatten the user data for API response
                for server_name, server_data in user_data['databases'].items():
                    user_entry = {
                        'normalized_username': normalized_name,
                        'original_name': user_data['original_name'],
                        'server_name': server_name,
                        'username': server_data['user_data']['name'],
                        'user_type': server_data['user_data']['type'],
                        'is_active': server_data['user_data']['active'],
                        'last_login': server_data['user_data']['last_login'],
                        'database_type': server_data['server_info']['database_type'],
                        'environment': server_data['server_info']['environment'],
                        'total_permissions': user_data['total_permissions'],
                        'appears_on_servers': user_data['appears_on_servers']
                    }
                    users.append(user_entry)
        
        # Apply filters
        filtered_users = users
        
        if is_active is not None:
            filtered_users = [u for u in filtered_users if u.get('is_active') == is_active]
        
        if user_type:
            filtered_users = [u for u in filtered_users if u.get('user_type') == user_type]
        
        if search:
            search_lower = search.lower()
            filtered_users = [
                u for u in filtered_users 
                if search_lower in u.get('username', '').lower() 
                or search_lower in u.get('server_name', '').lower()
            ]
        
        logger.log_system_event("Users retrieved via API")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(filtered_users)} users",
            data={
                "users": filtered_users,
                "total_count": len(filtered_users),
                "filters_applied": {
                    "server_id": server_id,
                    "is_active": is_active,
                    "user_type": user_type,
                    "search": search
                }
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@router.get("/global")
async def get_global_users():
    """
    Get unified global users view across all servers
    """
    try:
        db_manager = get_database_manager()
        global_users = db_manager.get_global_users()
        
        logger.log_system_event("Global users retrieved via API")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(global_users)} global users",
            data=global_users
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get global users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve global users")

@router.get("/servers/{server_id}")
async def get_users_by_server(server_id: int):
    """
    Get all users for a specific server
    """
    try:
        db_manager = get_database_manager()
        users = db_manager.get_users_by_server(server_id)
        
        logger.log_system_event(f"Users retrieved for server {server_id} via API")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(users)} users for server {server_id}",
            data=users
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get users for server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users for server {server_id}")

@router.get("/statistics")
async def get_user_statistics():
    """
    Get user statistics across all servers
    """
    try:
        db_manager = get_database_manager()
        stats = db_manager.get_statistics()
        
        # Extract user-related statistics
        user_stats = {
            "total_users": stats.get('users', {}).get('total', 0),
            "active_users": stats.get('users', {}).get('active', 0),
            "unique_global_users": stats.get('global_users', {}).get('unique_users', 0),
            "recent_activity": stats.get('activity', {}).get('recent_events', 0)
        }
        
        # Add additional user analytics
        global_users = db_manager.get_global_users()
        
        # Count users by type
        user_types = {}
        servers_per_user = {}
        
        for user_data in global_users.values():
            for server_name, server_data in user_data['databases'].items():
                user_type = server_data['user_data']['type']
                user_types[user_type] = user_types.get(user_type, 0) + 1
            
            # Count how many servers each user appears on
            server_count = len(user_data['databases'])
            servers_per_user[server_count] = servers_per_user.get(server_count, 0) + 1
        
        user_stats['user_types_distribution'] = user_types
        user_stats['servers_per_user_distribution'] = servers_per_user
        
        logger.log_system_event("User statistics retrieved via API")
        return APIResponse(
            success=True,
            message="User statistics retrieved successfully",
            data=user_stats
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get user statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user statistics")

@router.post("/servers/{server_id}/save")
async def save_users_for_server(server_id: int, users_data: List[UserInfo]):
    """
    Save users data for a specific server (bulk operation)
    """
    try:
        db_manager = get_database_manager()
        
        # Convert Pydantic models to dict format
        users_dict_list = []
        for user in users_data:
            user_dict = {
                'name': user.username,
                'type': user.user_type,
                'active': user.is_active,
                'metadata': user.metadata,
                'permissions': user.permissions_data
            }
            users_dict_list.append(user_dict)
        
        # Save users using database manager
        db_manager.save_users(server_id, users_dict_list)
        
        logger.log_system_event(f"Saved {len(users_data)} users for server {server_id} via API")
        return APIResponse(
            success=True,
            message=f"Successfully saved {len(users_data)} users for server {server_id}",
            data={
                "server_id": server_id,
                "users_count": len(users_data),
                "users_saved": users_dict_list
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to save users for server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save users for server {server_id}")

@router.get("/search")
async def search_users(
    query: str,
    server_id: Optional[int] = None,
    limit: int = 50
):
    """
    Search for users across servers
    """
    try:
        db_manager = get_database_manager()
        
        if server_id:
            # Search within specific server
            users = db_manager.get_users_by_server(server_id)
            search_results = [
                user for user in users
                if query.lower() in user.get('username', '').lower()
                or query.lower() in user.get('user_type', '').lower()
            ]
        else:
            # Search globally
            global_users = db_manager.get_global_users()
            search_results = []
            
            for normalized_name, user_data in global_users.items():
                # Check if query matches username or original name
                if (query.lower() in normalized_name.lower() or 
                    query.lower() in user_data['original_name'].lower()):
                    
                    search_results.append({
                        'normalized_username': normalized_name,
                        'original_name': user_data['original_name'],
                        'appears_on_servers': user_data['appears_on_servers'],
                        'total_permissions': user_data['total_permissions'],
                        'is_active_somewhere': user_data['is_active_somewhere'],
                        'databases': user_data['databases']
                    })
        
        # Limit results
        limited_results = search_results[:limit]
        
        logger.log_system_event(f"User search completed for query '{query}' via API")
        return APIResponse(
            success=True,
            message=f"Found {len(limited_results)} users matching '{query}'",
            data={
                "query": query,
                "results": limited_results,
                "total_found": len(search_results),
                "limit_applied": limit,
                "server_id": server_id
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to search users: {e}")
        raise HTTPException(status_code=500, detail="Failed to search users")

@router.post("/detect-manual")
async def detect_manual_users(server_id: int, current_users: List[str], baseline_users: List[str]):
    """
    Detect manually created users on a server
    """
    try:
        db_manager = get_database_manager()
        
        # Use database manager to detect manual users
        manual_users = db_manager.detect_manual_users(server_id, current_users, baseline_users)
        
        logger.log_system_event(f"Manual user detection completed for server {server_id} via API")
        return APIResponse(
            success=True,
            message=f"Detected {len(manual_users)} manual users on server {server_id}",
            data={
                "server_id": server_id,
                "manual_users": manual_users,
                "current_users_count": len(current_users),
                "baseline_users_count": len(baseline_users)
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to detect manual users for server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to detect manual users for server {server_id}")