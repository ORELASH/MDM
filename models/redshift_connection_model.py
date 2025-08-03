"""
RedshiftManager Redshift Connection Model
Advanced Amazon Redshift connectivity and query management system.
"""

import re
import ssl
import time
import threading
from typing import Any, Dict, List, Optional, Tuple, Union, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import json
from contextlib import contextmanager
from urllib.parse import urlparse
import queue
import concurrent.futures

try:
    import psycopg2
    from psycopg2 import sql, extras
    from psycopg2.pool import ThreadedConnectionPool
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    import sqlparse
    from sqlparse import format as sql_format
    import pandas as pd
except ImportError as e:
    logging.error(f"Required database dependencies missing: {e}")
    raise ImportError("Required packages: psycopg2-binary, sqlparse, pandas")

try:
    from .encryption_model import get_encryption_manager
    from .configuration_model import get_configuration_manager
except ImportError:
    # Handle development imports
    get_encryption_manager = None
    get_configuration_manager = None

# Configure logging
logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TIMEOUT = "timeout"


class QueryStatus(Enum):
    """Query execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SSLMode(Enum):
    """SSL connection modes."""
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"


@dataclass
class ConnectionConfig:
    """Redshift connection configuration."""
    host: str
    port: int = 5439
    database: str = "dev"
    username: str = ""
    password: str = ""
    ssl_mode: SSLMode = SSLMode.REQUIRE
    connect_timeout: int = 30
    query_timeout: int = 300
    application_name: str = "RedshiftManager"
    
    # Connection pool settings
    min_connections: int = 1
    max_connections: int = 10
    pool_timeout: int = 30
    
    # Advanced settings
    keepalive: bool = True
    keepalive_idle: int = 600
    keepalive_interval: int = 60
    keepalive_count: int = 3
    
    # Security settings
    verify_ssl: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None
    
    def to_connection_string(self, include_password: bool = True) -> str:
        """Generate PostgreSQL connection string."""
        params = {
            'host': self.host,
            'port': self.port,
            'dbname': self.database,
            'user': self.username,
            'application_name': self.application_name,
            'connect_timeout': self.connect_timeout,
            'sslmode': self.ssl_mode.value
        }
        
        if include_password and self.password:
            params['password'] = self.password
        
        if self.keepalive:
            params.update({
                'keepalives_idle': self.keepalive_idle,
                'keepalives_interval': self.keepalive_interval,
                'keepalives_count': self.keepalive_count
            })
        
        if self.ssl_cert_path:
            params['sslcert'] = self.ssl_cert_path
        if self.ssl_key_path:
            params['sslkey'] = self.ssl_key_path
        if self.ssl_ca_path:
            params['sslrootcert'] = self.ssl_ca_path
        
        return ' '.join([f"{k}={v}" for k, v in params.items()])


class QueryResult(NamedTuple):
    """Query execution result."""
    success: bool
    data: Optional[List[Dict[str, Any]]]
    columns: Optional[List[str]]
    row_count: int
    execution_time: float
    query_id: Optional[str]
    error_message: Optional[str]
    warnings: List[str]


@dataclass
class QueryExecution:
    """Query execution tracking."""
    query_id: str
    sql: str
    status: QueryStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    result: Optional[QueryResult] = None
    connection_id: Optional[str] = None
    user: Optional[str] = None
    cancelled_by: Optional[str] = None


@dataclass
class RedshiftUserInfo:
    """Redshift user information."""
    username: str
    user_id: int
    create_db: bool
    super_user: bool
    connection_limit: int
    valid_until: Optional[datetime]
    groups: List[str] = field(default_factory=list)


@dataclass
class ConnectionStats:
    """Connection statistics."""
    total_connections: int = 0
    active_connections: int = 0
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    last_activity: Optional[datetime] = None
    uptime: timedelta = field(default_factory=lambda: timedelta(0))


class QueryAnalyzer:
    """SQL query analysis and optimization suggestions."""
    
    @staticmethod
    def analyze_query(sql: str) -> Dict[str, Any]:
        """Analyze SQL query for potential issues."""
        try:
            parsed = sqlparse.parse(sql)[0]
            
            analysis = {
                'type': QueryAnalyzer._get_query_type(parsed),
                'tables': QueryAnalyzer._extract_tables(parsed),
                'complexity': QueryAnalyzer._assess_complexity(parsed),
                'suggestions': [],
                'warnings': [],
                'estimated_cost': 'medium'
            }
            
            # Add specific suggestions
            QueryAnalyzer._add_suggestions(analysis, parsed)
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Query analysis failed: {e}")
            return {
                'type': 'unknown',
                'tables': [],
                'complexity': 'unknown',
                'suggestions': [],
                'warnings': [f"Analysis failed: {str(e)}"],
                'estimated_cost': 'unknown'
            }
    
    @staticmethod
    def _get_query_type(parsed) -> str:
        """Determine query type."""
        first_token = next((t for t in parsed.flatten() if t.ttype in (sqlparse.tokens.Keyword, sqlparse.tokens.Keyword.DDL)), None)
        return first_token.value.upper() if first_token else 'UNKNOWN'
    
    @staticmethod
    def _extract_tables(parsed) -> List[str]:
        """Extract table names from query."""
        tables = []
        
        def extract_from_token(token):
            if token.ttype is sqlparse.tokens.Name:
                tables.append(str(token))
            elif hasattr(token, 'tokens'):
                for subtoken in token.tokens:
                    extract_from_token(subtoken)
        
        for token in parsed.tokens:
            extract_from_token(token)
        
        return list(set(tables))
    
    @staticmethod
    def _assess_complexity(parsed) -> str:
        """Assess query complexity."""
        token_count = len(list(parsed.flatten()))
        
        if token_count < 20:
            return 'low'
        elif token_count < 100:
            return 'medium'
        else:
            return 'high'
    
    @staticmethod
    def _add_suggestions(analysis: Dict[str, Any], parsed) -> None:
        """Add optimization suggestions."""
        sql_text = str(parsed).upper()
        
        # Check for common anti-patterns
        if 'SELECT *' in sql_text:
            analysis['suggestions'].append("Avoid SELECT * - specify only needed columns")
        
        if 'WITHOUT' not in sql_text and 'VACUUM' in sql_text:
            analysis['suggestions'].append("Consider using VACUUM DELETE ONLY for faster execution")
        
        if 'LIMIT' not in sql_text and analysis['type'] == 'SELECT':
            analysis['warnings'].append("Consider adding LIMIT clause for large result sets")
        
        if 'DISTKEY' not in sql_text and analysis['type'] in ['CREATE', 'ALTER']:
            analysis['suggestions'].append("Consider specifying DISTKEY for better performance")


class RedshiftConnector:
    """Advanced Redshift connection manager with pooling and monitoring."""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self._connection_pool: Optional[ThreadedConnectionPool] = None
        self._query_history: List[QueryExecution] = []
        self._stats = ConnectionStats()
        self._lock = threading.RLock()
        self._query_counter = 0
        self._connection_start_time = datetime.now()
        
        # Encryption manager for credential storage
        self._encryption_manager = get_encryption_manager() if get_encryption_manager else None
        
        # Query execution tracking
        self._active_queries: Dict[str, QueryExecution] = {}
        self._query_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    
    def connect(self) -> bool:
        """Establish connection to Redshift cluster."""
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"Connecting to Redshift cluster: {self.config.host}:{self.config.port}")
            
            # Create connection pool
            self._connection_pool = ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                dsn=self.config.to_connection_string(),
                connection_factory=None
            )
            
            # Test connection
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    logger.info(f"Connected to Redshift: {version}")
            
            self.status = ConnectionStatus.CONNECTED
            self._stats.total_connections += 1
            self._stats.last_activity = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redshift: {e}")
            self.status = ConnectionStatus.ERROR
            return False
    
    def disconnect(self) -> None:
        """Close all connections."""
        try:
            if self._connection_pool:
                self._connection_pool.closeall()
                self._connection_pool = None
            
            # Cancel active queries
            for query_id in list(self._active_queries.keys()):
                self.cancel_query(query_id)
            
            self.status = ConnectionStatus.DISCONNECTED
            logger.info("Disconnected from Redshift cluster")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    @contextmanager
    def _get_connection(self):
        """Get connection from pool with automatic return."""
        if not self._connection_pool:
            raise RuntimeError("Not connected to database")
        
        conn = None
        try:
            conn = self._connection_pool.getconn()
            yield conn
        finally:
            if conn:
                self._connection_pool.putconn(conn)
    
    def execute_query(self, sql: str, parameters: Optional[Dict[str, Any]] = None,
                     fetch_results: bool = True, timeout: Optional[int] = None) -> QueryResult:
        """Execute SQL query with comprehensive error handling."""
        query_id = f"query_{int(time.time() * 1000)}_{self._query_counter}"
        self._query_counter += 1
        
        # Create query execution record
        execution = QueryExecution(
            query_id=query_id,
            sql=sql,
            status=QueryStatus.PENDING,
            start_time=datetime.now(),
            user=self.config.username
        )
        
        self._active_queries[query_id] = execution
        self._query_history.append(execution)
        
        try:
            execution.status = QueryStatus.RUNNING
            start_time = time.time()
            
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                    # Set query timeout
                    if timeout or self.config.query_timeout:
                        cursor.execute(f"SET statement_timeout = {timeout or self.config.query_timeout * 1000}")
                    
                    # Execute query
                    if parameters:
                        cursor.execute(sql, parameters)
                    else:
                        cursor.execute(sql)
                    
                    # Fetch results if needed
                    data = None
                    columns = None
                    row_count = 0
                    
                    if fetch_results and cursor.description:
                        data = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        row_count = len(data) if data else 0
                        
                        # Convert to list of dicts
                        if data:
                            data = [dict(row) for row in data]
                    else:
                        row_count = cursor.rowcount if cursor.rowcount >= 0 else 0
                    
                    execution_time = time.time() - start_time
                    execution.status = QueryStatus.COMPLETED
                    execution.end_time = datetime.now()
                    execution.execution_time = execution_time
                    
                    # Update statistics
                    self._update_stats(True, execution_time)
                    
                    result = QueryResult(
                        success=True,
                        data=data,
                        columns=columns,
                        row_count=row_count,
                        execution_time=execution_time,
                        query_id=query_id,
                        error_message=None,
                        warnings=[]
                    )
                    
                    execution.result = result
                    return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            execution.status = QueryStatus.FAILED
            execution.end_time = datetime.now()
            execution.execution_time = execution_time
            
            error_msg = str(e)
            logger.error(f"Query execution failed: {error_msg}")
            
            # Update statistics
            self._update_stats(False, execution_time)
            
            result = QueryResult(
                success=False,
                data=None,
                columns=None,
                row_count=0,
                execution_time=execution_time,
                query_id=query_id,
                error_message=error_msg,
                warnings=[]
            )
            
            execution.result = result
            return result
        
        finally:
            # Remove from active queries
            if query_id in self._active_queries:
                del self._active_queries[query_id]
    
    def execute_query_async(self, sql: str, parameters: Optional[Dict[str, Any]] = None,
                           callback: Optional[callable] = None) -> str:
        """Execute query asynchronously."""
        query_id = f"async_query_{int(time.time() * 1000)}_{self._query_counter}"
        
        def run_query():
            result = self.execute_query(sql, parameters)
            if callback:
                callback(result)
            return result
        
        future = self._query_executor.submit(run_query)
        return query_id
    
    def cancel_query(self, query_id: str, cancelled_by: Optional[str] = None) -> bool:
        """Cancel running query."""
        if query_id in self._active_queries:
            execution = self._active_queries[query_id]
            execution.status = QueryStatus.CANCELLED
            execution.cancelled_by = cancelled_by
            execution.end_time = datetime.now()
            
            # In a real implementation, you would send a CANCEL REQUEST
            # to the Redshift cluster using the process ID
            logger.info(f"Query {query_id} cancelled")
            return True
        
        return False
    
    def get_query_history(self, limit: Optional[int] = None) -> List[QueryExecution]:
        """Get query execution history."""
        history = sorted(self._query_history, key=lambda x: x.start_time, reverse=True)
        return history[:limit] if limit else history
    
    def get_active_queries(self) -> List[QueryExecution]:
        """Get currently active queries."""
        return list(self._active_queries.values())
    
    def _update_stats(self, success: bool, execution_time: float) -> None:
        """Update connection statistics."""
        with self._lock:
            self._stats.total_queries += 1
            self._stats.last_activity = datetime.now()
            
            if success:
                self._stats.successful_queries += 1
            else:
                self._stats.failed_queries += 1
            
            # Update average query time
            if self._stats.total_queries > 0:
                current_total = self._stats.avg_query_time * (self._stats.total_queries - 1)
                self._stats.avg_query_time = (current_total + execution_time) / self._stats.total_queries
            
            # Update uptime
            self._stats.uptime = datetime.now() - self._connection_start_time
    
    def get_connection_stats(self) -> ConnectionStats:
        """Get connection statistics."""
        with self._lock:
            stats_copy = ConnectionStats(
                total_connections=self._stats.total_connections,
                active_connections=len(self._active_queries),
                total_queries=self._stats.total_queries,
                successful_queries=self._stats.successful_queries,
                failed_queries=self._stats.failed_queries,
                avg_query_time=self._stats.avg_query_time,
                last_activity=self._stats.last_activity,
                uptime=self._stats.uptime
            )
            return stats_copy
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test database connection."""
        try:
            result = self.execute_query("SELECT 1 as test", fetch_results=True, timeout=10)
            if result.success:
                return True, "Connection successful"
            else:
                return False, result.error_message or "Unknown error"
        except Exception as e:
            return False, str(e)
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get Redshift cluster information."""
        try:
            queries = [
                ("version", "SELECT version()"),
                ("current_user", "SELECT current_user"),
                ("current_database", "SELECT current_database()"),
                ("session_timezone", "SELECT current_setting('timezone')"),
                ("cluster_info", """
                    SELECT 
                        node_type,
                        cluster_create_time,
                        cluster_status,
                        cluster_version,
                        number_of_nodes
                    FROM stv_cluster_summary
                    LIMIT 1
                """)
            ]
            
            info = {}
            for key, query in queries:
                try:
                    result = self.execute_query(query, fetch_results=True, timeout=30)
                    if result.success and result.data:
                        if key == "cluster_info":
                            info[key] = result.data[0] if result.data else {}
                        else:
                            info[key] = result.data[0][list(result.data[0].keys())[0]]
                except Exception as e:
                    info[key] = f"Error: {str(e)}"
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get cluster info: {e}")
            return {"error": str(e)}
    
    def get_user_info(self, username: Optional[str] = None) -> Optional[RedshiftUserInfo]:
        """Get Redshift user information."""
        try:
            user = username or self.config.username
            
            query = """
                SELECT 
                    usename,
                    usesysid,
                    usecreatedb,
                    usesuper,
                    useconnlimit,
                    valuntil,
                    grolist
                FROM pg_user 
                WHERE usename = %s
            """
            
            result = self.execute_query(query, {"usename": user}, fetch_results=True)
            
            if result.success and result.data:
                user_data = result.data[0]
                
                return RedshiftUserInfo(
                    username=user_data['usename'],
                    user_id=user_data['usesysid'],
                    create_db=user_data['usecreatedb'],
                    super_user=user_data['usesuper'],
                    connection_limit=user_data['useconnlimit'],
                    valid_until=user_data['valuntil'],
                    groups=user_data['grolist'] or []
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health = {
            "status": self.status.value,
            "timestamp": datetime.now().isoformat(),
            "connection_test": False,
            "response_time": None,
            "cluster_accessible": False,
            "user_permissions": False,
            "errors": []
        }
        
        try:
            # Test basic connectivity
            start_time = time.time()
            conn_test, conn_msg = self.test_connection()
            health["response_time"] = time.time() - start_time
            health["connection_test"] = conn_test
            
            if not conn_test:
                health["errors"].append(f"Connection test failed: {conn_msg}")
                return health
            
            # Test cluster access
            cluster_info = self.get_cluster_info()
            health["cluster_accessible"] = "error" not in cluster_info
            
            if not health["cluster_accessible"]:
                health["errors"].append("Cannot access cluster information")
            
            # Test user permissions
            user_info = self.get_user_info()
            health["user_permissions"] = user_info is not None
            
            if not health["user_permissions"]:
                health["errors"].append("Cannot retrieve user information")
            
        except Exception as e:
            health["errors"].append(f"Health check failed: {str(e)}")
        
        return health


# Global connector instance
_redshift_connector: Optional[RedshiftConnector] = None


def get_connector(config: Optional[ConnectionConfig] = None) -> RedshiftConnector:
    """Get global Redshift connector instance."""
    global _redshift_connector
    if _redshift_connector is None or config:
        if config:
            _redshift_connector = RedshiftConnector(config)
        else:
            # Create with default configuration
            default_config = ConnectionConfig(
                host=get_configuration_manager().get("redshift.host", "localhost") if get_configuration_manager else "localhost",
                port=get_configuration_manager().get("redshift.port", 5439) if get_configuration_manager else 5439,
                database=get_configuration_manager().get("redshift.database", "dev") if get_configuration_manager else "dev",
                username=get_configuration_manager().get("redshift.username", "") if get_configuration_manager else "",
                password=get_configuration_manager().get("redshift.password", "") if get_configuration_manager else ""
            )
            _redshift_connector = RedshiftConnector(default_config)
    
    return _redshift_connector


if __name__ == "__main__":
    # Example usage
    config = ConnectionConfig(
        host="your-cluster.region.redshift.amazonaws.com",
        database="dev",
        username="your_username",
        password="your_password"
    )
    
    connector = RedshiftConnector(config)
    
    if connector.connect():
        # Test query
        result = connector.execute_query("SELECT current_date, current_user")
        print(f"Query result: {result}")
        
        # Get cluster info
        cluster_info = connector.get_cluster_info()
        print(f"Cluster info: {cluster_info}")
        
        # Health check
        health = connector.health_check()
        print(f"Health check: {health}")
        
        connector.disconnect()
    else:
        print("Failed to connect to Redshift cluster")