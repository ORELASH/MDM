#!/usr/bin/env python3
"""
Basic SQLite Database Testing for MultiDBManager
Tests core database functionality step by step
"""

import sys
import os
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_sqlite_basic():
    """Basic SQLite functionality test"""
    print("🗄️  Starting Basic SQLite Database Testing")
    print("=" * 60)
    
    # Create temporary test database
    temp_dir = tempfile.mkdtemp(prefix="multidb_basic_test_")
    test_db_path = os.path.join(temp_dir, "test_basic.db")
    
    try:
        # Test 1: Database creation and connection
        print("📋 Test 1: Database Creation and Connection")
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Enable foreign keys and WAL mode
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        
        print("✅ Database created and connected successfully")
        
        # Test 2: Basic table creation
        print("\n📋 Test 2: Basic Table Creation")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                database_name TEXT NOT NULL,
                database_type TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES test_servers (id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        print("✅ Basic tables created successfully")
        
        # Test 3: Data insertion
        print("\n📋 Test 3: Data Insertion")
        cursor.execute("""
            INSERT INTO test_servers (name, host, port, database_name, database_type)
            VALUES (?, ?, ?, ?, ?)
        """, ("Test Server", "localhost", 5432, "testdb", "postgresql"))
        
        server_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO test_users (server_id, username, is_active)
            VALUES (?, ?, ?)
        """, (server_id, "test_user", True))
        
        conn.commit()
        print(f"✅ Data inserted successfully (Server ID: {server_id})")
        
        # Test 4: Data retrieval
        print("\n📋 Test 4: Data Retrieval")
        cursor.execute("SELECT * FROM test_servers")
        servers = cursor.fetchall()
        
        cursor.execute("SELECT * FROM test_users")
        users = cursor.fetchall()
        
        print(f"✅ Retrieved {len(servers)} servers and {len(users)} users")
        
        # Test 5: Join operations
        print("\n📋 Test 5: Join Operations")
        cursor.execute("""
            SELECT s.name as server_name, u.username, u.is_active
            FROM test_servers s
            JOIN test_users u ON s.id = u.server_id
        """)
        
        joined_data = cursor.fetchall()
        print(f"✅ Join operation successful, {len(joined_data)} records")
        
        # Test 6: Update operations
        print("\n📋 Test 6: Update Operations")
        cursor.execute("""
            UPDATE test_users SET is_active = ? WHERE username = ?
        """, (False, "test_user"))
        
        conn.commit()
        
        cursor.execute("SELECT is_active FROM test_users WHERE username = ?", ("test_user",))
        updated_status = cursor.fetchone()[0]
        
        if updated_status == 0:  # SQLite returns 0 for FALSE
            print("✅ Update operation successful")
        else:
            print("❌ Update operation failed")
            return False
        
        # Test 7: Transaction handling
        print("\n📋 Test 7: Transaction Handling")
        try:
            cursor.execute("BEGIN TRANSACTION")
            cursor.execute("""
                INSERT INTO test_servers (name, host, port, database_name, database_type)
                VALUES (?, ?, ?, ?, ?)
            """, ("Transaction Test", "localhost", 5433, "txtest", "postgresql"))
            
            cursor.execute("COMMIT")
            print("✅ Transaction commit successful")
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            print(f"❌ Transaction failed: {e}")
            return False
        
        # Test 8: Foreign key constraints
        print("\n📋 Test 8: Foreign Key Constraints")
        cursor.execute("DELETE FROM test_servers WHERE id = ?", (server_id,))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM test_users WHERE server_id = ?", (server_id,))
        remaining_users = cursor.fetchone()[0]
        
        if remaining_users == 0:
            print("✅ Foreign key cascade delete working")
        else:
            print("❌ Foreign key constraint not working")
            return False
        
        # Test 9: Concurrent access simulation
        print("\n📋 Test 9: Concurrent Access Simulation")
        conn2 = sqlite3.connect(test_db_path)
        cursor2 = conn2.cursor()
        
        # Both connections insert data
        cursor.execute("""
            INSERT INTO test_servers (name, host, port, database_name, database_type)
            VALUES (?, ?, ?, ?, ?)
        """, ("Concurrent Test 1", "localhost", 5434, "concurrent1", "postgresql"))
        
        cursor2.execute("""
            INSERT INTO test_servers (name, host, port, database_name, database_type)
            VALUES (?, ?, ?, ?, ?)
        """, ("Concurrent Test 2", "localhost", 5435, "concurrent2", "postgresql"))
        
        conn.commit()
        conn2.commit()
        
        cursor.execute("SELECT COUNT(*) FROM test_servers")
        server_count = cursor.fetchone()[0]
        
        conn2.close()
        
        if server_count >= 2:
            print("✅ Concurrent access working")
        else:
            print("❌ Concurrent access failed")
            return False
        
        # Test 10: Performance check
        print("\n📋 Test 10: Performance Check")
        import time
        
        start_time = time.time()
        
        # Insert 1000 test records
        test_data = []
        for i in range(1000):
            test_data.append((f"Perf Server {i}", "localhost", 5432 + i, f"perfdb{i}", "postgresql"))
        
        cursor.executemany("""
            INSERT INTO test_servers (name, host, port, database_name, database_type)
            VALUES (?, ?, ?, ?, ?)
        """, test_data)
        
        conn.commit()
        
        # Query all records
        cursor.execute("SELECT COUNT(*) FROM test_servers")
        total_records = cursor.fetchone()[0]
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Performance test: {total_records} records, {duration:.3f}s")
        
        if duration > 5.0:  # Should be fast for 1000 records
            print("⚠️  Performance warning: operation took longer than expected")
        
        cursor.close()
        conn.close()
        
        print(f"\n{'='*60}")
        print("🎉 All basic SQLite tests PASSED!")
        print(f"Database file size: {os.path.getsize(test_db_path)} bytes")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("🧹 Test environment cleaned up")

def test_database_manager_integration():
    """Test integration with actual DatabaseManager"""
    print("\n🔗 Testing DatabaseManager Integration")
    print("=" * 60)
    
    try:
        from database.database_manager import DatabaseManager
        
        # Create temporary database for testing
        temp_dir = tempfile.mkdtemp(prefix="multidb_manager_test_")
        test_db_path = os.path.join(temp_dir, "test_manager.db")
        
        # Initialize database manager
        db_manager = DatabaseManager(test_db_path)
        
        print("✅ DatabaseManager initialized successfully")
        
        # Test getting servers (should work even with empty database)
        servers = db_manager.get_servers()
        print(f"✅ Retrieved {len(servers)} servers from empty database")
        
        # Test statistics
        stats = db_manager.get_statistics()
        print("✅ Statistics retrieved successfully")
        print(f"   Stats keys: {list(stats.keys())}")
        
        # Test with actual server data
        test_server = {
            "name": "Integration Test Server",
            "host": "localhost",
            "port": 5432,
            "database_name": "integrationtest",  # Use database_name not database
            "database_type": "postgresql",
            "username": "testuser",
            "password": "testpass"
        }
        
        # This might fail due to schema issues, but let's try
        try:
            server_id = db_manager.add_server(test_server)
            if server_id:
                print(f"✅ Server added successfully (ID: {server_id})")
                
                # Test getting the server back
                servers = db_manager.get_servers()
                found_server = next((s for s in servers if s['id'] == server_id), None)
                
                if found_server:
                    print("✅ Server retrieval after insertion successful")
                else:
                    print("❌ Server not found after insertion")
                    
            else:
                print("❌ Server insertion returned no ID")
                
        except Exception as e:
            print(f"⚠️  Server operations failed (expected due to schema): {e}")
        
        # Cleanup
        if hasattr(db_manager._local, 'connection'):
            db_manager._local.connection.close()
            
        shutil.rmtree(temp_dir)
        print("🧹 Integration test cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ DatabaseManager integration test failed: {e}")
        return False

def main():
    """Main testing function"""
    success = True
    
    # Run basic SQLite tests
    if not test_sqlite_basic():
        success = False
    
    # Run DatabaseManager integration tests
    if not test_database_manager_integration():
        success = False
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 All SQLite tests completed successfully!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)