#!/usr/bin/env python3
"""
MySQL Helper Utilities for RedshiftManager
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

def test_mysql_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test MySQL database connection.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import pymysql
        
        # Extract connection parameters
        host = config.get('host', 'localhost')
        port = config.get('port', 3306)
        database = config.get('database', 'mysql')
        username = config.get('username', 'root')
        password = config.get('password', '')
        charset = config.get('charset', 'utf8mb4')
        
        # Test connection
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset=charset,
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        # Test basic query
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version")
            version_info = cursor.fetchone()
            
        connection.close()
        
        return True, f"✅ Connection successful! MySQL {version_info['version']}"
        
    except ImportError:
        return False, "❌ PyMySQL not installed. Run: pip install PyMySQL"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"

def create_database_if_not_exists(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Create MySQL database if it doesn't exist.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import pymysql
        
        # Connect to MySQL server without specifying database
        host = config.get('host', 'localhost')
        port = config.get('port', 3306)
        username = config.get('username', 'root')
        password = config.get('password', '')
        target_db = config.get('database', 'redshift_manager')
        charset = config.get('charset', 'utf8mb4')
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            charset=charset,
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Check if database exists
            cursor.execute("SHOW DATABASES LIKE %s", (target_db,))
            result = cursor.fetchone()
            
            if result:
                connection.close()
                return True, f"✅ Database '{target_db}' already exists"
            
            # Create database with UTF8MB4 charset
            cursor.execute(f"""
                CREATE DATABASE `{target_db}` 
                CHARACTER SET utf8mb4 
                COLLATE utf8mb4_unicode_ci
            """)
            
            # Create user if specified and different from root
            if username != 'root' and username != config.get('username', 'root'):
                try:
                    cursor.execute(f"""
                        CREATE USER IF NOT EXISTS '{username}'@'localhost' 
                        IDENTIFIED BY '{password}'
                    """)
                    cursor.execute(f"""
                        GRANT ALL PRIVILEGES ON `{target_db}`.* 
                        TO '{username}'@'localhost'
                    """)
                    cursor.execute("FLUSH PRIVILEGES")
                except Exception as e:
                    logger.warning(f"Failed to create user: {e}")
            
        connection.close()
        
        return True, f"✅ Database '{target_db}' created successfully"
        
    except ImportError:
        return False, "❌ PyMySQL not installed. Run: pip install PyMySQL"
    except Exception as e:
        return False, f"❌ Failed to create database: {str(e)}"

def get_database_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get MySQL database information.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Dictionary with database information
    """
    try:
        import pymysql
        
        host = config.get('host', 'localhost')
        port = config.get('port', 3306)
        database = config.get('database', 'redshift_manager')
        username = config.get('username', 'root')
        password = config.get('password', '')
        charset = config.get('charset', 'utf8mb4')
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset=charset,
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Get MySQL version
            cursor.execute("SELECT VERSION() as version")
            version_info = cursor.fetchone()
            
            # Get database size
            cursor.execute("""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'size_mb'
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, (database,))
            size_info = cursor.fetchone()
            
            # Get table count
            cursor.execute("""
                SELECT COUNT(*) as table_count 
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, (database,))
            table_info = cursor.fetchone()
            
            # Get connection info
            cursor.execute("""
                SELECT COUNT(*) as active_connections
                FROM information_schema.processlist 
                WHERE db = %s
            """, (database,))
            conn_info = cursor.fetchone()
            
            # Get engine info
            cursor.execute("""
                SELECT engine, COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = %s
                GROUP BY engine
            """, (database,))
            engines = cursor.fetchall()
            
        connection.close()
        
        return {
            "version": version_info['version'],
            "database_size_mb": size_info['size_mb'] or 0,
            "table_count": table_info['table_count'],
            "active_connections": conn_info['active_connections'] or 0,
            "storage_engines": {engine['engine']: engine['count'] for engine in engines if engine['engine']},
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "charset": charset
        }
        
    except Exception as e:
        return {"error": str(e)}

def optimize_mysql_tables(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Optimize MySQL tables for better performance.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import pymysql
        
        host = config.get('host', 'localhost')
        port = config.get('port', 3306)
        database = config.get('database', 'redshift_manager')
        username = config.get('username', 'root')
        password = config.get('password', '')
        charset = config.get('charset', 'utf8mb4')
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset=charset,
            connect_timeout=10
        )
        
        with connection.cursor() as cursor:
            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            optimized_count = 0
            for table in tables:
                table_name = list(table.values())[0]
                try:
                    cursor.execute(f"OPTIMIZE TABLE `{table_name}`")
                    optimized_count += 1
                except Exception as e:
                    logger.warning(f"Failed to optimize table {table_name}: {e}")
            
        connection.close()
        
        return True, f"✅ Optimized {optimized_count} tables successfully"
        
    except Exception as e:
        return False, f"❌ Failed to optimize tables: {str(e)}"

def main():
    """Main function for command line testing."""
    print("🔧 MySQL Connection Tester")
    print("=" * 40)
    
    # Load configuration
    try:
        config_path = project_root / "config" / "system.json"
        with open(config_path) as f:
            config = json.load(f)
        
        db_config = config.get('database', {})
        print(f"📋 Testing connection to: {db_config.get('host')}:{db_config.get('port')}")
        
        # Test connection
        success, message = test_mysql_connection(db_config)
        print(message)
        
        if success:
            # Create database if needed
            success, message = create_database_if_not_exists(db_config)
            print(message)
            
            if success:
                # Get database info
                info = get_database_info(db_config)
                if 'error' not in info:
                    print("\n📊 Database Information:")
                    print(f"   Database: {info['database']}")
                    print(f"   Size: {info['database_size_mb']} MB")
                    print(f"   Tables: {info['table_count']}")
                    print(f"   Active Connections: {info['active_connections']}")
                    print(f"   Storage Engines: {info['storage_engines']}")
                    
                    # Ask for optimization
                    if info['table_count'] > 0:
                        try:
                            response = input("\n🔧 Optimize tables? (y/N): ").lower()
                            if response == 'y':
                                success, message = optimize_mysql_tables(db_config)
                                print(message)
                        except KeyboardInterrupt:
                            print("\n👋 Cancelled by user")
                else:
                    print(f"❌ Failed to get database info: {info['error']}")
        
    except FileNotFoundError:
        print("❌ Configuration file not found: config/system.json")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()