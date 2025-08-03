"""
Database Management API Router
Enhanced database operations with SQLite integration
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

router = APIRouter(prefix="/database", tags=["database"])
logger = RedshiftLogger()

# Pydantic models
class DatabaseConnectionTest(BaseModel):
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: str = "postgresql"
    ssl_mode: Optional[str] = "prefer"

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    server_id: int
    limit: Optional[int] = Field(default=1000, ge=1, le=10000)

class QueryResult(BaseModel):
    success: bool
    columns: List[str] = []
    rows: List[List[Any]] = []
    row_count: int
    execution_time_ms: float
    message: str

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

@router.post("/test-connection")
async def test_database_connection(connection_test: DatabaseConnectionTest):
    """
    Test database connection without saving
    """
    try:
        logger.log_system_event("Testing database connection via API", "INFO")
        
        # Use database manager for connection testing
        db_manager = get_database_manager()
        
        # Create temporary server config for testing
        server_config = {
            'name': f'test_connection_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'host': connection_test.host,
            'port': connection_test.port,
            'database': connection_test.database,
            'username': connection_test.username,
            'password': connection_test.password,
            'database_type': connection_test.db_type,
            'environment': 'Test'
        }
        
        import time
        start_time = time.time()
        
        try:
            # Try to add server temporarily (this tests connection)
            test_server_id = db_manager.add_server(server_config)
            
            # Remove test server immediately
            db_manager.delete_server(test_server_id)
            
            execution_time = time.time() - start_time
            
            result = {
                'success': True,
                'message': 'Connection successful',
                'details': {
                    'connection_time_ms': round(execution_time * 1000, 2),
                    'database_type': connection_test.db_type,
                    'host': connection_test.host,
                    'port': connection_test.port
                }
            }
            
        except Exception as e:
            result = {
                'success': False,
                'message': f'Connection failed: {str(e)}',
                'details': {'error': str(e)}
            }
        
        logger.log_system_event("Database connection test completed via API", "INFO")
        
        return APIResponse(
            success=result['success'],
            message=result['message'],
            data=result.get('details', {})
        )
        
    except Exception as e:
        logger.log_system_event(f"Database connection test failed: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Connection test failed")

@router.get("/servers")
async def get_database_servers():
    """
    Get all registered database servers
    """
    try:
        db_manager = get_database_manager()
        servers = db_manager.get_servers()
        
        logger.log_system_event("Database servers retrieved via API", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(servers)} database servers",
            data=servers
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get database servers: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to retrieve database servers")

@router.get("/servers/{server_id}/users")
async def get_server_users(server_id: int):
    """
    Get all users for a specific server
    """
    try:
        db_manager = get_database_manager()
        users = db_manager.get_users_by_server(server_id)
        
        logger.log_system_event(f"Users retrieved for server {server_id} via API", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(users)} users for server {server_id}",
            data=users
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get users for server {server_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users for server {server_id}")

@router.get("/servers/{server_id}/scan-results")
async def get_server_scan_results(server_id: int):
    """
    Get latest scan results for a server
    """
    try:
        db_manager = get_database_manager()
        scan_results = db_manager.get_latest_scan_results(server_id)
        
        logger.log_system_event(f"Scan results retrieved for server {server_id} via API", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved scan results for server {server_id}",
            data=scan_results
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get scan results for server {server_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scan results for server {server_id}")

@router.get("/global-users")
async def get_global_users():
    """
    Get unified global users across all servers
    """
    try:
        db_manager = get_database_manager()
        global_users = db_manager.get_global_users()
        
        logger.log_system_event("Global users retrieved via API", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(global_users)} global users",
            data=global_users
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get global users: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to retrieve global users")

@router.get("/statistics")
async def get_database_statistics():
    """
    Get system statistics
    """
    try:
        db_manager = get_database_manager()
        stats = db_manager.get_statistics()
        
        logger.log_system_event("Database statistics retrieved via API", "INFO")
        return APIResponse(
            success=True,
            message="Database statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get database statistics: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to retrieve database statistics")

@router.get("/scan-history")
async def get_scan_history(server_id: Optional[int] = None, limit: int = 50):
    """
    Get scan history for all servers or specific server
    """
    try:
        db_manager = get_database_manager()
        history = db_manager.get_scan_history(server_id=server_id, limit=limit)
        
        logger.log_system_event("Scan history retrieved via API", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(history)} scan history records",
            data=history
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get scan history: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to retrieve scan history")

@router.get("/security-events")
async def get_security_events(resolved: Optional[bool] = None, severity: Optional[str] = None):
    """
    Get security events
    """
    try:
        db_manager = get_database_manager()
        events = db_manager.get_security_events(resolved=resolved, severity=severity)
        
        logger.log_system_event("Security events retrieved via API", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(events)} security events",
            data=events
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get security events: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to retrieve security events")

@router.post("/backup")
async def create_database_backup():
    """
    Create database backup
    """
    try:
        db_manager = get_database_manager()
        backup_path = db_manager.backup_database()
        
        logger.log_system_event("Database backup created via API", "INFO")
        return APIResponse(
            success=True,
            message="Database backup created successfully",
            data={"backup_path": backup_path}
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to create database backup: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to create database backup")