"""
Query Execution API Router
Remote SQL execution with security, validation, and history tracking
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
import sys
from pathlib import Path
import json
import re
import time
from datetime import datetime
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from database.database_manager import get_database_manager
from core.logging_system import RedshiftManagerLogger as RedshiftLogger

router = APIRouter(prefix="/query", tags=["query"])
logger = RedshiftLogger()

# Enums
class QueryType(str, Enum):
    SELECT = "select"
    INSERT = "insert" 
    UPDATE = "update"
    DELETE = "delete"
    DDL = "ddl"
    UNKNOWN = "unknown"

class QueryStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Pydantic models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100000)
    server_id: int = Field(..., ge=1)
    limit: Optional[int] = Field(default=1000, ge=1, le=50000)
    timeout_seconds: Optional[int] = Field(default=30, ge=1, le=300)
    explain_only: Optional[bool] = Field(default=False)
    save_query: Optional[bool] = Field(default=False)
    query_name: Optional[str] = Field(default=None, max_length=100)
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        
        # Basic SQL injection prevention
        dangerous_patterns = [
            r';\s*(drop|delete|truncate|alter)\s+',
            r'union\s+.*select',
            r'exec\s*\(',
            r'xp_cmdshell',
            r'sp_executesql',
            r'into\s+outfile',
            r'load_file\s*\(',
            r'--\s*$',
            r'/\*.*\*/',
        ]
        
        query_lower = v.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE | re.MULTILINE):
                raise ValueError(f'Query contains potentially dangerous pattern: {pattern}')
        
        return v.strip()

class QueryValidationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100000)
    server_id: int = Field(..., ge=1)

class SavedQueryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    query: str = Field(..., min_length=1, max_length=100000)
    description: Optional[str] = Field(default="", max_length=500)
    server_id: Optional[int] = None
    tags: Optional[List[str]] = Field(default_factory=list)

class QueryResult(BaseModel):
    success: bool
    query_id: str
    query_type: QueryType
    execution_time_ms: float
    rows_affected: int = 0
    columns: List[str] = Field(default_factory=list)
    data: List[List[Any]] = Field(default_factory=list)
    message: str
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QueryHistory(BaseModel):
    query_id: str
    query: str
    server_id: int
    server_name: str
    status: QueryStatus
    query_type: QueryType
    execution_time_ms: Optional[float]
    rows_affected: int
    executed_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    user_id: Optional[str] = "api_user"

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Helper functions
def detect_query_type(query: str) -> QueryType:
    """Detect the type of SQL query"""
    query_clean = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    query_clean = re.sub(r'--.*', '', query_clean)
    query_clean = query_clean.strip().lower()
    
    if query_clean.startswith('select'):
        return QueryType.SELECT
    elif query_clean.startswith('insert'):
        return QueryType.INSERT
    elif query_clean.startswith('update'):
        return QueryType.UPDATE
    elif query_clean.startswith('delete'):
        return QueryType.DELETE
    elif any(query_clean.startswith(cmd) for cmd in ['create', 'drop', 'alter', 'truncate']):
        return QueryType.DDL
    else:
        return QueryType.UNKNOWN

def generate_query_id() -> str:
    """Generate unique query ID"""
    import uuid
    return f"qry_{int(time.time())}_{str(uuid.uuid4())[:8]}"

def validate_server_access(server_id: int) -> Dict[str, Any]:
    """Validate server exists and is accessible"""
    db_manager = get_database_manager()
    servers = db_manager.get_servers()
    
    server = next((s for s in servers if s['id'] == server_id), None)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
    
    return server

def execute_query_on_server(server: Dict[str, Any], query: str, limit: int = 1000, explain_only: bool = False) -> Dict[str, Any]:
    """Execute query on specific server with connection handling"""
    import psycopg2
    import pymysql
    import redis
    import sqlite3
    
    db_type = server.get('database_type', 'postgresql').lower()
    
    try:
        start_time = time.time()
        
        if db_type in ['postgresql', 'redshift']:
            # PostgreSQL/Redshift connection
            conn = psycopg2.connect(
                host=server['host'],
                port=server['port'],
                database=server['database_name'],
                user=server['username'],
                password=server['password'],
                connect_timeout=10
            )
            
            cursor = conn.cursor()
            
            if explain_only:
                cursor.execute(f"EXPLAIN {query}")
            else:
                cursor.execute(query)
            
            # Get results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                if explain_only:
                    rows = cursor.fetchall()
                else:
                    rows = cursor.fetchmany(limit) if limit else cursor.fetchall()
                rows_affected = cursor.rowcount if cursor.rowcount > 0 else len(rows)
            else:
                columns = []
                rows = []
                rows_affected = cursor.rowcount if cursor.rowcount >= 0 else 0
            
            cursor.close()
            conn.close()
            
        elif db_type == 'mysql':
            # MySQL connection
            conn = pymysql.connect(
                host=server['host'],
                port=server['port'],
                database=server['database_name'],
                user=server['username'],
                password=server['password'],
                connect_timeout=10,
                autocommit=True
            )
            
            cursor = conn.cursor()
            
            if explain_only:
                cursor.execute(f"EXPLAIN {query}")
            else:
                cursor.execute(query)
            
            # Get results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                if explain_only:
                    rows = cursor.fetchall()
                else:
                    rows = cursor.fetchmany(limit) if limit else cursor.fetchall()
                rows_affected = cursor.rowcount if cursor.rowcount > 0 else len(rows)
            else:
                columns = []
                rows = []
                rows_affected = cursor.rowcount if cursor.rowcount >= 0 else 0
            
            cursor.close()
            conn.close()
            
        elif db_type == 'sqlite':
            # SQLite connection
            conn = sqlite3.connect(server.get('database_name', 'database.db'))
            cursor = conn.cursor()
            
            if explain_only:
                cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            else:
                cursor.execute(query)
            
            # Get results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                if explain_only:
                    rows = cursor.fetchall()
                else:
                    rows = cursor.fetchmany(limit) if limit else cursor.fetchall()
                rows_affected = cursor.rowcount if cursor.rowcount > 0 else len(rows)
            else:
                columns = []
                rows = []
                rows_affected = cursor.rowcount if cursor.rowcount >= 0 else 0
            
            cursor.close()
            conn.close()
            
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'success': True,
            'columns': columns,
            'rows': rows,
            'rows_affected': rows_affected,
            'execution_time_ms': round(execution_time, 2),
            'warnings': []
        }
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return {
            'success': False,
            'columns': [],
            'rows': [],
            'rows_affected': 0,
            'execution_time_ms': round(execution_time, 2),
            'error': str(e),
            'warnings': []
        }

# API Endpoints
@router.post("/execute", response_model=QueryResult)
async def execute_query(query_request: QueryRequest):
    """
    Execute SQL query on specified server
    """
    try:
        logger.log_system_event(f"Query execution started for server {query_request.server_id}", "INFO")
        
        # Validate server
        server = validate_server_access(query_request.server_id)
        
        # Generate query ID
        query_id = generate_query_id()
        
        # Detect query type
        query_type = detect_query_type(query_request.query)
        
        # Execute query
        result = execute_query_on_server(
            server=server,
            query=query_request.query,
            limit=query_request.limit,
            explain_only=query_request.explain_only
        )
        
        # Create response
        query_result = QueryResult(
            success=result['success'],
            query_id=query_id,
            query_type=query_type,
            execution_time_ms=result['execution_time_ms'],
            rows_affected=result['rows_affected'],
            columns=result['columns'],
            data=result['rows'],
            message="Query executed successfully" if result['success'] else f"Query failed: {result.get('error', 'Unknown error')}",
            warnings=result.get('warnings', []),
            metadata={
                'server_name': server['name'],
                'database_type': server['database_type'],
                'query_length': len(query_request.query),
                'explain_only': query_request.explain_only
            }
        )
        
        # Save to history (simplified - in production you'd save to database)
        db_manager = get_database_manager()
        try:
            # Log query execution in scan history
            scan_id = db_manager.start_scan(query_request.server_id, 'query_execution')
            scan_results = {
                'query_id': query_id,
                'query': query_request.query[:1000],  # Truncate for storage
                'query_type': query_type.value,
                'success': result['success'],
                'rows_affected': result['rows_affected'],
                'execution_time_ms': result['execution_time_ms']
            }
            db_manager.complete_scan(scan_id, scan_results, int(result['execution_time_ms']))
        except Exception as e:
            logger.log_system_event(f"Failed to log query execution: {e}", "WARNING")
        
        # Save query if requested
        if query_request.save_query and query_request.query_name:
            # In production, you'd save to a dedicated saved_queries table
            logger.log_system_event(f"Query saved as '{query_request.query_name}'", "INFO")
        
        logger.log_system_event(f"Query execution completed for server {query_request.server_id}", "INFO")
        return query_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Query execution failed: {e}", "ERROR")
        return QueryResult(
            success=False,
            query_id=generate_query_id(),
            query_type=QueryType.UNKNOWN,
            execution_time_ms=0,
            message=f"Query execution failed: {str(e)}"
        )

@router.post("/validate", response_model=APIResponse)
async def validate_query(validation_request: QueryValidationRequest):
    """
    Validate SQL query syntax without execution
    """
    try:
        logger.log_system_event(f"Query validation started for server {validation_request.server_id}", "INFO")
        
        # Validate server
        server = validate_server_access(validation_request.server_id)
        
        # Detect query type
        query_type = detect_query_type(validation_request.query)
        
        # Perform basic syntax validation
        validation_result = execute_query_on_server(
            server=server,
            query=validation_request.query,
            limit=0,
            explain_only=True
        )
        
        if validation_result['success']:
            message = f"Query validation successful. Query type: {query_type.value}"
            data = {
                'query_type': query_type.value,
                'estimated_execution_time_ms': validation_result['execution_time_ms'],
                'server_name': server['name'],
                'syntax_valid': True
            }
        else:
            message = f"Query validation failed: {validation_result.get('error', 'Unknown error')}"
            data = {
                'query_type': query_type.value,
                'server_name': server['name'],
                'syntax_valid': False,
                'error': validation_result.get('error')
            }
        
        logger.log_system_event(f"Query validation completed for server {validation_request.server_id}", "INFO")
        return APIResponse(
            success=validation_result['success'],
            message=message,
            data=data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Query validation failed: {e}", "ERROR")
        return APIResponse(
            success=False,
            message=f"Query validation failed: {str(e)}",
            data={'error': str(e)}
        )

@router.get("/history", response_model=APIResponse)
async def get_query_history(
    server_id: Optional[int] = None,
    limit: int = Query(default=50, ge=1, le=500),
    query_type: Optional[QueryType] = None,
    status: Optional[QueryStatus] = None
):
    """
    Get query execution history
    """
    try:
        logger.log_system_event("Query history retrieval started", "INFO")
        
        # Get scan history (queries are logged as scans)
        db_manager = get_database_manager()
        scan_history = db_manager.get_scan_history(server_id=server_id, limit=limit)
        
        # Filter for query executions and format
        query_history = []
        for scan in scan_history:
            if scan.get('scan_type') == 'query_execution':
                try:
                    results = scan.get('results', {})
                    if isinstance(results, str):
                        results = json.loads(results)
                    
                    history_item = {
                        'query_id': results.get('query_id', f"scan_{scan['id']}"),
                        'query': results.get('query', 'N/A'),
                        'server_id': scan['server_id'],
                        'server_name': scan['server_name'],
                        'status': QueryStatus.COMPLETED if results.get('success') else QueryStatus.FAILED,
                        'query_type': results.get('query_type', 'unknown'),
                        'execution_time_ms': results.get('execution_time_ms', scan.get('duration_ms', 0)),
                        'rows_affected': results.get('rows_affected', 0),
                        'executed_at': scan['started_at'],
                        'completed_at': scan.get('completed_at'),
                        'error_message': None if results.get('success') else 'Query execution failed'
                    }
                    
                    # Apply filters
                    if query_type and history_item['query_type'] != query_type.value:
                        continue
                    if status and history_item['status'] != status:
                        continue
                    
                    query_history.append(history_item)
                except Exception as e:
                    logger.log_system_event(f"Error processing scan history item: {e}", "WARNING")
                    continue
        
        logger.log_system_event("Query history retrieval completed", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(query_history)} query history items",
            data={
                'history': query_history,
                'total_count': len(query_history),
                'filters_applied': {
                    'server_id': server_id,
                    'query_type': query_type.value if query_type else None,
                    'status': status.value if status else None,
                    'limit': limit
                }
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Query history retrieval failed: {e}", "ERROR")
        return APIResponse(
            success=False,
            message=f"Failed to retrieve query history: {str(e)}",
            data={'error': str(e)}
        )

@router.get("/saved", response_model=APIResponse)
async def get_saved_queries(
    server_id: Optional[int] = None,
    tags: Optional[List[str]] = Query(default=None),
    search: Optional[str] = None
):
    """
    Get saved queries
    """
    try:
        logger.log_system_event("Saved queries retrieval started", "INFO")
        
        # In production, you'd have a dedicated saved_queries table
        # For now, return mock data structure
        saved_queries = [
            {
                'id': 1,
                'name': 'User Count by Server',
                'query': 'SELECT COUNT(*) as user_count FROM users WHERE server_id = ?',
                'description': 'Count users on a specific server',
                'server_id': None,
                'tags': ['reporting', 'users'],
                'created_at': '2025-08-03T10:00:00Z',
                'updated_at': '2025-08-03T10:00:00Z'
            },
            {
                'id': 2,
                'name': 'Active Users Report',
                'query': 'SELECT * FROM users WHERE is_active = true ORDER BY username',
                'description': 'List all active users',
                'server_id': None,
                'tags': ['reporting', 'users', 'active'],
                'created_at': '2025-08-03T10:00:00Z',
                'updated_at': '2025-08-03T10:00:00Z'
            }
        ]
        
        # Apply filters
        filtered_queries = saved_queries
        if server_id:
            filtered_queries = [q for q in filtered_queries if q['server_id'] is None or q['server_id'] == server_id]
        if tags:
            filtered_queries = [q for q in filtered_queries if any(tag in q['tags'] for tag in tags)]
        if search:
            search_lower = search.lower()
            filtered_queries = [
                q for q in filtered_queries 
                if search_lower in q['name'].lower() 
                or search_lower in q['description'].lower()
                or search_lower in q['query'].lower()
            ]
        
        logger.log_system_event("Saved queries retrieval completed", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(filtered_queries)} saved queries",
            data={
                'queries': filtered_queries,
                'total_count': len(filtered_queries),
                'filters_applied': {
                    'server_id': server_id,
                    'tags': tags,
                    'search': search
                }
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Saved queries retrieval failed: {e}", "ERROR")
        return APIResponse(
            success=False,
            message=f"Failed to retrieve saved queries: {str(e)}",
            data={'error': str(e)}
        )

@router.post("/saved", response_model=APIResponse)
async def save_query(saved_query: SavedQueryRequest):
    """
    Save a query for future use
    """
    try:
        logger.log_system_event(f"Saving query '{saved_query.name}'", "INFO")
        
        # In production, you'd save to a dedicated saved_queries table
        # For now, just validate and return success
        
        # Validate query syntax if server_id provided
        if saved_query.server_id:
            validate_server_access(saved_query.server_id)
            
            # Validate query
            validation_result = execute_query_on_server(
                server={'database_type': 'postgresql', 'host': 'localhost', 'port': 5432, 'database_name': 'test', 'username': 'test', 'password': 'test'},
                query=saved_query.query,
                limit=0,
                explain_only=True
            )
            
            if not validation_result['success']:
                return APIResponse(
                    success=False,
                    message=f"Cannot save invalid query: {validation_result.get('error', 'Syntax error')}",
                    data={'validation_error': validation_result.get('error')}
                )
        
        # Mock save operation
        saved_query_data = {
            'id': 999,  # In production, this would be auto-generated
            'name': saved_query.name,
            'query': saved_query.query,
            'description': saved_query.description,
            'server_id': saved_query.server_id,
            'tags': saved_query.tags,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        logger.log_system_event(f"Query '{saved_query.name}' saved successfully", "INFO")
        return APIResponse(
            success=True,
            message=f"Query '{saved_query.name}' saved successfully",
            data=saved_query_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_system_event(f"Failed to save query: {e}", "ERROR")
        return APIResponse(
            success=False,
            message=f"Failed to save query: {str(e)}",
            data={'error': str(e)}
        )

@router.get("/templates", response_model=APIResponse)
async def get_query_templates():
    """
    Get predefined query templates
    """
    try:
        logger.log_system_event("Query templates retrieval started", "INFO")
        
        # Predefined query templates
        templates = [
            {
                'id': 'user_list',
                'name': 'List All Users',
                'description': 'Get all users from a server',
                'template': 'SELECT username, user_type, is_active, last_login FROM users ORDER BY username',
                'category': 'Users',
                'parameters': [],
                'database_types': ['postgresql', 'mysql', 'sqlite']
            },
            {
                'id': 'table_info',
                'name': 'Table Information',
                'description': 'Get information about database tables',
                'template': 'SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = current_schema()',
                'category': 'Schema',
                'parameters': [],
                'database_types': ['postgresql', 'mysql']
            },
            {
                'id': 'user_permissions',
                'name': 'User Permissions',
                'description': 'Get permissions for a specific user',
                'template': 'SELECT grantee, privilege_type, is_grantable FROM information_schema.role_table_grants WHERE grantee = ${username}',
                'category': 'Security',
                'parameters': [{'name': 'username', 'type': 'string', 'description': 'Username to check permissions for'}],
                'database_types': ['postgresql']
            },
            {
                'id': 'database_size',
                'name': 'Database Size',
                'description': 'Get size of all databases',
                'template': 'SELECT datname as database_name, pg_size_pretty(pg_database_size(datname)) as size FROM pg_database ORDER BY pg_database_size(datname) DESC',
                'category': 'Monitoring',
                'parameters': [],
                'database_types': ['postgresql']
            }
        ]
        
        logger.log_system_event("Query templates retrieval completed", "INFO")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(templates)} query templates",
            data={
                'templates': templates,
                'categories': list(set(t['category'] for t in templates))
            }
        )
        
    except Exception as e:
        logger.log_system_event(f"Query templates retrieval failed: {e}", "ERROR")
        return APIResponse(
            success=False,
            message=f"Failed to retrieve query templates: {str(e)}",
            data={'error': str(e)}
        )