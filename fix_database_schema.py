#!/usr/bin/env python3
"""
Database Schema Fix - Add missing columns to existing tables
"""

import sqlite3
import os
from pathlib import Path

def fix_database_schema():
    """Fix database schema by adding missing columns"""
    
    db_path = "data/multidb_manager.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    print(f"🔧 Fixing database schema: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get existing table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Found tables: {', '.join(tables)}")
        
        # List of columns to add to each table
        schema_fixes = {
            'servers': [
                ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ],
            'users': [
                ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ],
            'roles': [
                ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ],
            'groups': [
                ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ],
            'tables': [
                ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ]
        }
        
        for table_name, columns_to_add in schema_fixes.items():
            if table_name in tables:
                print(f"\n🔍 Checking table: {table_name}")
                
                # Get existing columns
                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_columns = [row[1] for row in cursor.fetchall()]
                
                for column_name, column_def in columns_to_add:
                    if column_name not in existing_columns:
                        try:
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
                            cursor.execute(sql)
                            print(f"  ✅ Added column: {column_name}")
                        except sqlite3.Error as e:
                            print(f"  ⚠️  Failed to add {column_name}: {e}")
                    else:
                        print(f"  ✓ Column {column_name} already exists")
            else:
                print(f"  ⚠️  Table {table_name} not found")
        
        # Create missing tables if needed
        missing_tables = {
            'query_history': '''
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    query_text TEXT NOT NULL,
                    execution_time REAL,
                    rows_affected INTEGER,
                    status TEXT DEFAULT 'completed',
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                )
            ''',
            'system_logs': '''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT,
                    function TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                )
            ''',
            'query_templates': '''
                CREATE TABLE IF NOT EXISTS query_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    query_template TEXT NOT NULL,
                    parameters JSON,
                    database_type TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'user_preferences': '''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    preferences JSON NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'connection_pools': '''
                CREATE TABLE IF NOT EXISTS connection_pools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    pool_size INTEGER DEFAULT 5,
                    active_connections INTEGER DEFAULT 0,
                    max_connections INTEGER DEFAULT 10,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                )
            ''',
            'audit_logs': '''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    details JSON,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'performance_metrics': '''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_type TEXT DEFAULT 'gauge',
                    tags JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                )
            '''
        }
        
        print(f"\n🏗️  Creating missing tables:")
        for table_name, create_sql in missing_tables.items():
            if table_name not in tables:
                try:
                    cursor.execute(create_sql)
                    print(f"  ✅ Created table: {table_name}")
                except sqlite3.Error as e:
                    print(f"  ⚠️  Failed to create {table_name}: {e}")
            else:
                print(f"  ✓ Table {table_name} already exists")
        
        # Commit all changes
        conn.commit()
        
        # Verify the fixes
        print(f"\n🔍 Verification:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        final_tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Final tables count: {len(final_tables)}")
        
        # Test a query that was failing
        try:
            cursor.execute("SELECT created_at FROM servers LIMIT 1")
            print("✅ Test query successful - created_at column accessible")
        except sqlite3.Error as e:
            print(f"❌ Test query failed: {e}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 Database schema fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False

if __name__ == "__main__":
    fix_database_schema()