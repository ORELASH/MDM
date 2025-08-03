#!/usr/bin/env python3
"""
PostgreSQL Helper Utilities for RedshiftManager
Database connection testing and management tools.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

logger = logging.getLogger(__name__)

def test_postgresql_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test PostgreSQL database connection.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Extract connection parameters
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        database = config.get('database', 'postgres')
        username = config.get('username', 'postgres')
        password = config.get('password', '')
        
        # Test connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            connect_timeout=10,
            cursor_factory=RealDictCursor
        )
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return True, f"✅ Connection successful! PostgreSQL {version['version']}"
        
    except ImportError:
        return False, "❌ psycopg2 not installed. Run: pip install psycopg2-binary"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"

def create_database_if_not_exists(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Create database if it doesn't exist.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Connect to default postgres database first
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        username = config.get('username', 'postgres')
        password = config.get('password', '')
        target_db = config.get('database', 'redshift_manager')
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database='postgres',
            user=username,
            password=password,
            connect_timeout=10
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
            (target_db,)
        )
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return True, f"✅ Database '{target_db}' already exists"
        
        # Create database
        cursor.execute(f'CREATE DATABASE "{target_db}"')
        cursor.close()
        conn.close()
        
        return True, f"✅ Database '{target_db}' created successfully"
        
    except ImportError:
        return False, "❌ psycopg2 not installed. Run: pip install psycopg2-binary"
    except Exception as e:
        return False, f"❌ Failed to create database: {str(e)}"

def get_database_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get PostgreSQL database information.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Dictionary with database information
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        database = config.get('database', 'redshift_manager')
        username = config.get('username', 'postgres')
        password = config.get('password', '')
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            connect_timeout=10,
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # Get version
        cursor.execute("SELECT version();")
        version_info = cursor.fetchone()
        
        # Get database size
        cursor.execute("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as size
        """)
        size_info = cursor.fetchone()
        
        # Get table count
        cursor.execute("""
            SELECT COUNT(*) as table_count 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_info = cursor.fetchone()
        
        # Get connection info
        cursor.execute("""
            SELECT count(*) as active_connections
            FROM pg_stat_activity 
            WHERE datname = current_database()
        """)
        conn_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            "version": version_info['version'],
            "database_size": size_info['size'],
            "table_count": table_info['table_count'],
            "active_connections": conn_info['active_connections'],
            "host": host,
            "port": port,
            "database": database,
            "username": username
        }
        
    except Exception as e:
        return {"error": str(e)}

def main():
    """Main function for command line testing."""
    print("🔧 PostgreSQL Connection Tester")
    print("=" * 40)
    
    # Load configuration
    try:
        config_path = project_root / "config" / "system.json"
        with open(config_path) as f:
            config = json.load(f)
        
        db_config = config.get('database', {})
        print(f"📋 Testing connection to: {db_config.get('host')}:{db_config.get('port')}")
        
        # Test connection
        success, message = test_postgresql_connection(db_config)
        print(message)
        
        if success:
            # Create database if needed
            success, message = create_database_if_not_exists(db_config)
            print(message)
            
            # Get database info
            info = get_database_info(db_config)
            if 'error' not in info:
                print("\n📊 Database Information:")
                print(f"   Database: {info['database']}")
                print(f"   Size: {info['database_size']}")
                print(f"   Tables: {info['table_count']}")
                print(f"   Active Connections: {info['active_connections']}")
            else:
                print(f"❌ Failed to get database info: {info['error']}")
        
    except FileNotFoundError:
        print("❌ Configuration file not found: config/system.json")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()