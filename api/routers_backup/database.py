"""
Database Management API Router
Database connection, query execution, and management endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.logging_system import RedshiftLogger
from api.dependencies import get_current_api_user, require_role
from utils.auth_manager import UserRole

router = APIRouter(prefix="/database", tags=["database"])
logger = RedshiftLogger()

# Pydantic models
class DatabaseConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    db_type: str = Field(..., pattern=r'^(redshift|postgresql|mysql|oracle|sqlite)$')
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    ssl_mode: Optional[str] = "prefer"
    additional_params: Dict[str, Any] = {}

class DatabaseConnectionTest(BaseModel):
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: str = "redshift"
    ssl_mode: Optional[str] = "prefer"

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    connection_name: str
    limit: Optional[int] = Field(default=1000, ge=1, le=10000)

class QueryResult(BaseModel):
    success: bool
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float
    message: str

@router.post("/test-connection")
async def test_database_connection(
    connection_test: DatabaseConnectionTest,
    current_user: dict = Depends(require_role(UserRole.ANALYST))
):
    """
    Test database connection without saving
    """
    try:
        logger.log_action_start(f"Testing database connection by {current_user['username']}")
        
        # Import database utilities
        try:
            from models.redshift_connection_model import test_connection
        except ImportError:
            # Fallback implementation
            import psycopg2
            import time
            
            start_time = time.time()
            
            try:
                # Build connection string based on db_type
                if connection_test.db_type in ['redshift', 'postgresql']:
                    conn = psycopg2.connect(
                        host=connection_test.host,
                        port=connection_test.port,
                        database=connection_test.database,
                        user=connection_test.username,
                        password=connection_test.password,
                        sslmode=connection_test.ssl_mode or 'prefer'
                    )
                    conn.close()
                    
                    execution_time = time.time() - start_time
                    result = {
                        'success': True,
                        'message': 'Connection successful',
                        'details': {
                            'connection_time_ms': round(execution_time * 1000, 2),
                            'database_type': connection_test.db_type
                        }
                    }
                else:
                    result = {
                        'success': False,
                        'message': f'Database type {connection_test.db_type} not supported in test mode',
                        'details': {}
                    }
                    
            except Exception as e:
                result = {
                    'success': False,
                    'message': f'Connection failed: {str(e)}',
                    'details': {'error': str(e)}
                }
        
        logger.log_action_end(f"Database connection test completed by {current_user['username']}")
        
        return {
            "success": result['success'],
            "message": result['message'],
            "data": result.get('details', {}),
            "timestamp": logger._get_timestamp()
        }
        
    except Exception as e:
        logger.log_error(f"Database connection test failed: {e}")
        raise HTTPException(status_code=500, detail="Connection test failed")

@router.get("/connections")
async def get_database_connections(
    current_user: dict = Depends(require_role(UserRole.ANALYST))
):
    """
    Get saved database connections for current user
    """
    try:
        # Load user connections from preferences or configuration
        from utils.user_preferences import UserPreferencesManager
        
        prefs_manager = UserPreferencesManager()
        user_prefs = prefs_manager.get_user_preferences(current_user['username'])
        
        connections = user_prefs.get('database_connections', [])
        
        # Remove sensitive information (passwords) from response
        safe_connections = []
        for conn in connections:
            safe_conn = {k: v for k, v in conn.items() if k != 'password'}
            safe_conn['has_password'] = 'password' in conn and bool(conn['password'])
            safe_connections.append(safe_conn)
        
        logger.log_action_end(f"Database connections retrieved by {current_user['username']}")
        return safe_connections
        
    except Exception as e:
        logger.log_error(f"Failed to get database connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve database connections")

@router.post("/connections")
async def save_database_connection(
    connection: DatabaseConfig,
    current_user: dict = Depends(require_role(UserRole.ANALYST))
):
    """
    Save a new database connection
    """
    try:
        from utils.user_preferences import UserPreferencesManager
        
        prefs_manager = UserPreferencesManager()
        user_prefs = prefs_manager.get_user_preferences(current_user['username'])
        
        if 'database_connections' not in user_prefs:
            user_prefs['database_connections'] = []
        
        # Check if connection name already exists
        existing_names = [conn['name'] for conn in user_prefs['database_connections']]
        if connection.name in existing_names:
            raise HTTPException(status_code=400, detail="Connection name already exists")
        
        # Add connection
        connection_dict = connection.dict()
        user_prefs['database_connections'].append(connection_dict)
        
        success = prefs_manager.update_preferences(current_user['username'], user_prefs)
        
        if success:
            logger.log_action_end(f"Database connection '{connection.name}' saved by {current_user['username']}")
            return {"success": True, "message": f"Connection '{connection.name}' saved successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to save connection")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(f"Failed to save database connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to save database connection")

@router.put("/connections/{connection_name}")
async def update_database_connection(
    connection_name: str,
    connection: DatabaseConfig,
    current_user: dict = Depends(require_role(UserRole.ANALYST))
):
    """
    Update an existing database connection
    """
    try:
        from utils.user_preferences import UserPreferencesManager
        
        prefs_manager = UserPreferencesManager()
        user_prefs = prefs_manager.get_user_preferences(current_user['username'])
        
        connections = user_prefs.get('database_connections', [])
        
        # Find and update connection
        updated = False
        for i, conn in enumerate(connections):
            if conn['name'] == connection_name:
                connections[i] = connection.dict()
                updated = True
                break
        
        if not updated:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        user_prefs['database_connections'] = connections
        success = prefs_manager.update_preferences(current_user['username'], user_prefs)
        
        if success:
            logger.log_action_end(f"Database connection '{connection_name}' updated by {current_user['username']}")
            return {"success": True, "message": f"Connection '{connection_name}' updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update connection")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(f"Failed to update database connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to update database connection")

@router.delete("/connections/{connection_name}")
async def delete_database_connection(
    connection_name: str,
    current_user: dict = Depends(require_role(UserRole.ANALYST))
):
    """
    Delete a database connection
    """
    try:
        from utils.user_preferences import UserPreferencesManager
        
        prefs_manager = UserPreferencesManager()
        user_prefs = prefs_manager.get_user_preferences(current_user['username'])
        
        connections = user_prefs.get('database_connections', [])
        
        # Find and remove connection
        updated_connections = [conn for conn in connections if conn['name'] != connection_name]
        
        if len(updated_connections) == len(connections):
            raise HTTPException(status_code=404, detail="Connection not found")
        
        user_prefs['database_connections'] = updated_connections
        success = prefs_manager.update_preferences(current_user['username'], user_prefs)
        
        if success:
            logger.log_action_end(f"Database connection '{connection_name}' deleted by {current_user['username']}")
            return {"success": True, "message": f"Connection '{connection_name}' deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete connection")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(f"Failed to delete database connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete database connection")

@router.post("/query", response_model=QueryResult)
async def execute_query(
    query_request: QueryRequest,
    current_user: dict = Depends(require_role(UserRole.ANALYST))
):
    """
    Execute a database query
    """
    try:
        logger.log_action_start(f"Query execution started by {current_user['username']}")
        
        # Get connection details
        from utils.user_preferences import UserPreferencesManager
        
        prefs_manager = UserPreferencesManager()
        user_prefs = prefs_manager.get_user_preferences(current_user['username'])
        
        connections = user_prefs.get('database_connections', [])
        connection = None
        
        for conn in connections:
            if conn['name'] == query_request.connection_name:
                connection = conn
                break
        
        if not connection:
            raise HTTPException(status_code=404, detail="Database connection not found")
        
        # Execute query (simplified implementation)
        import psycopg2
        import time
        
        start_time = time.time()
        
        try:
            conn = psycopg2.connect(
                host=connection['host'],
                port=connection['port'],
                database=connection['database'],
                user=connection['username'],
                password=connection['password'],
                sslmode=connection.get('ssl_mode', 'prefer')
            )
            
            cursor = conn.cursor()
            cursor.execute(query_request.query)
            
            # Fetch results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchmany(query_request.limit)
            else:
                columns = []
                rows = []
            
            execution_time = time.time() - start_time
            
            cursor.close()
            conn.close()
            
            result = QueryResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=round(execution_time * 1000, 2),
                message="Query executed successfully"
            )
            
            logger.log_action_end(f"Query executed successfully by {current_user['username']}")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.log_error(f"Query execution failed: {e}")
            
            return QueryResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=round(execution_time * 1000, 2),
                message=f"Query failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail="Query execution failed")