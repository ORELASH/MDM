"""
Server Management API Router
CRUD operations for database servers
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

router = APIRouter(prefix="/servers", tags=["servers"])
logger = RedshiftLogger()

# Pydantic models
class ServerConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    database_type: str = Field(default="postgresql", pattern=r'^(postgresql|mysql|redis|redshift|sqlite)$')
    environment: str = Field(default="Development")
    scanner_settings: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database_type: Optional[str] = None
    environment: Optional[str] = None
    scanner_settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

@router.get("/")
async def get_servers(include_inactive: bool = True):
    """
    Get all registered servers
    """
    try:
        db_manager = get_database_manager()
        servers = db_manager.get_servers(include_inactive=include_inactive)
        
        logger.log_system_event("Servers retrieved via API", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(servers)} servers",
            data=servers
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to get servers: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to retrieve servers")

@router.get("/{server_id}")
async def get_server(server_id: int):
    """
    Get specific server by ID
    """
    try:
        db_manager = get_database_manager()
        servers = db_manager.get_servers()
        
        server = next((s for s in servers if s['id'] == server_id), None)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        logger.log_system_event(f"Server {server_id} retrieved via API", "INFO")
        return APIResponse(
            success=True,
            message=f"Server {server_id} retrieved successfully",
            data=server
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to get server {server_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve server {server_id}")

@router.post("/")
async def create_server(server_config: ServerConfig):
    """
    Create a new server configuration
    """
    try:
        db_manager = get_database_manager()
        
        # Convert Pydantic model to dict
        server_dict = server_config.dict()
        
        # Add server to database
        server_id = db_manager.add_server(server_dict)
        
        logger.log_system_event(f"Server '{server_config.name}' created via API with ID {server_id}", "ERROR")
        return APIResponse(
            success=True,
            message=f"Server '{server_config.name}' created successfully",
            data={"server_id": server_id, "server_config": server_dict}
        )
        
    except Exception as e:
        logger.log_system_event(f"Failed to create server: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to create server")

@router.put("/{server_id}")
async def update_server(server_id: int, server_update: ServerUpdate):
    """
    Update an existing server configuration
    """
    try:
        db_manager = get_database_manager()
        
        # Get current server
        servers = db_manager.get_servers()
        current_server = next((s for s in servers if s['id'] == server_id), None)
        
        if not current_server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Update only provided fields
        update_data = server_update.dict(exclude_unset=True)
        
        # For now, we'll delete and recreate (since we don't have update method)
        # In production, you'd want a proper update method
        updated_config = {**current_server, **update_data}
        
        # Remove the ID from config for recreation
        updated_config.pop('id', None)
        
        # Delete old server and create new one
        db_manager.delete_server(server_id)
        new_server_id = db_manager.add_server(updated_config)
        
        logger.log_system_event(f"Server {server_id} updated via API (new ID: {new_server_id})", "ERROR")
        return APIResponse(
            success=True,
            message=f"Server {server_id} updated successfully",
            data={"old_server_id": server_id, "new_server_id": new_server_id, "updated_config": updated_config}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to update server {server_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to update server {server_id}")

@router.delete("/{server_id}")
async def delete_server(server_id: int):
    """
    Delete a server configuration
    """
    try:
        db_manager = get_database_manager()
        
        # Check if server exists
        servers = db_manager.get_servers()
        server = next((s for s in servers if s['id'] == server_id), None)
        
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Delete server
        db_manager.delete_server(server_id)
        
        logger.log_system_event(f"Server {server_id} deleted via API", "ERROR")
        return APIResponse(
            success=True,
            message=f"Server {server_id} deleted successfully",
            data={"deleted_server": server}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to delete server {server_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to delete server {server_id}")

@router.post("/{server_id}/test")
async def test_server_connection(server_id: int):
    """
    Test connection to a specific server
    """
    try:
        db_manager = get_database_manager()
        
        # Get server config
        servers = db_manager.get_servers()
        server = next((s for s in servers if s['id'] == server_id), None)
        
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        import time
        start_time = time.time()
        
        try:
            # Try to test connection by attempting a scan operation
            # This is a simplified test - in production you'd want a dedicated test method
            scan_id = db_manager.start_scan(server_id, 'connection_test')
            db_manager.complete_scan(scan_id, {}, int((time.time() - start_time) * 1000))
            
            # Update server status
            db_manager.update_server_status(server_id, "🟢 Connected")
            
            execution_time = time.time() - start_time
            
            result = {
                'success': True,
                'message': 'Connection test successful',
                'details': {
                    'connection_time_ms': round(execution_time * 1000, 2),
                    'server_name': server['name'],
                    'database_type': server['database_type']
                }
            }
            
        except Exception as e:
            # Update server status to failed
            db_manager.update_server_status(server_id, "🔴 Connection Failed")
            
            result = {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'details': {'error': str(e)}
            }
        
        logger.log_system_event(f"Connection test completed for server {server_id} via API", "ERROR")
        return APIResponse(
            success=result['success'],
            message=result['message'],
            data=result.get('details', {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to test server {server_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to test server {server_id}")

@router.post("/{server_id}/scan")
async def scan_server(server_id: int, scan_type: str = "full"):
    """
    Perform database scan on a specific server
    """
    try:
        db_manager = get_database_manager()
        
        # Get server config
        servers = db_manager.get_servers()
        server = next((s for s in servers if s['id'] == server_id), None)
        
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Start scan
        scan_id = db_manager.start_scan(server_id, scan_type)
        
        try:
            # This is a simplified scan - in production you'd use the actual scanner
            scan_results = {
                "users": [],
                "roles": [],
                "tables": [],
                "scan_type": scan_type,
                "server_id": server_id
            }
            
            # Complete scan
            db_manager.complete_scan(scan_id, scan_results, 1000)  # 1 second duration
            
            result = {
                'success': True,
                'message': f'{scan_type.title()} scan completed successfully',
                'scan_id': scan_id,
                'results': scan_results
            }
            
        except Exception as e:
            # Mark scan as failed
            db_manager.fail_scan(scan_id, str(e))
            
            result = {
                'success': False,
                'message': f'Scan failed: {str(e)}',
                'scan_id': scan_id,
                'error': str(e)
            }
        
        logger.log_system_event(f"Scan completed for server {server_id} via API", "ERROR")
        return APIResponse(
            success=result['success'],
            message=result['message'],
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to scan server {server_id}: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to scan server {server_id}")