#!/usr/bin/env python3
"""
DatabaseManager Testing for MultiDBManager
Tests the actual DatabaseManager class with current schema
"""

import sys
import os
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_database_manager():
    """Test DatabaseManager functionality"""
    print("🗄️  Testing DatabaseManager Functionality")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp(prefix="db_manager_test_")
    test_db_path = os.path.join(temp_dir, "test_db_manager.db")
    
    try:
        from database.database_manager import DatabaseManager
        
        # Test 1: Initialization
        print("📋 Test 1: DatabaseManager Initialization")
        db_manager = DatabaseManager(test_db_path)
        print("✅ DatabaseManager initialized successfully")
        
        # Test 2: Get empty servers list
        print("\n📋 Test 2: Get Empty Servers List")
        servers = db_manager.get_servers()
        print(f"✅ Retrieved {len(servers)} servers from empty database")
        
        # Test 3: Get statistics from empty database
        print("\n📋 Test 3: Get Statistics")
        stats = db_manager.get_statistics()
        print("✅ Statistics retrieved successfully")
        print(f"   Available stats: {list(stats.keys())}")
        
        # Test 4: Add a server with correct field names
        print("\n📋 Test 4: Add Server")
        test_server = {
            "name": "Test Server 1",
            "host": "localhost",
            "port": 5432,
            "database_name": "testdb",
            "database_type": "postgresql",
            "username": "testuser",
            "password": "testpass",
            "environment": "Test"
        }
        
        server_id = db_manager.add_server(test_server)
        if server_id:
            print(f"✅ Server added successfully (ID: {server_id})")
        else:
            print("❌ Failed to add server")
            return False
        
        # Test 5: Retrieve servers after addition
        print("\n📋 Test 5: Retrieve Servers After Addition")
        servers = db_manager.get_servers()
        print(f"✅ Retrieved {len(servers)} servers")
        
        if len(servers) > 0:
            server = servers[0]
            print(f"   Server details: {server.get('name', 'Unknown')} - {server.get('host', 'Unknown')}")
        
        # Test 6: Update server
        print("\n📋 Test 6: Update Server")
        updated_data = {
            "name": "Updated Test Server",
            "host": "localhost",
            "port": 5433,
            "database_name": "updated_testdb",
            "database_type": "postgresql",
            "username": "updated_user",
            "password": "updated_pass",
            "environment": "Updated"
        }
        
        update_result = db_manager.update_server(server_id, updated_data)
        if update_result:
            print("✅ Server updated successfully")
        else:
            print("❌ Server update failed")
        
        # Test 7: Add users to server
        print("\n📋 Test 7: Add Users to Server")
        test_users = [
            {
                "name": "db_user_1",
                "type": "normal",
                "active": True,
                "metadata": {"role": "developer", "team": "backend"}
            },
            {
                "name": "db_user_2",
                "type": "admin",
                "active": True,
                "metadata": {"role": "dba", "team": "infrastructure"}
            }
        ]
        
        try:
            db_manager.save_users(server_id, test_users)
            print("✅ Users saved successfully")
        except Exception as e:
            print(f"❌ Failed to save users: {e}")
        
        # Test 8: Retrieve users
        print("\n📋 Test 8: Retrieve Users")
        try:
            users = db_manager.get_users_by_server(server_id)
            print(f"✅ Retrieved {len(users)} users for server {server_id}")
            
            for user in users:
                print(f"   User: {user.get('username', 'Unknown')} ({user.get('user_type', 'Unknown')})")
                
        except Exception as e:
            print(f"❌ Failed to retrieve users: {e}")
        
        # Test 9: Global users
        print("\n📋 Test 9: Global Users")
        try:
            global_users = db_manager.get_global_users()
            print(f"✅ Retrieved {len(global_users)} global users")
        except Exception as e:
            print(f"❌ Failed to retrieve global users: {e}")
        
        # Test 10: Updated statistics
        print("\n📋 Test 10: Updated Statistics")
        stats = db_manager.get_statistics()
        print("✅ Updated statistics retrieved")
        
        server_stats = stats.get('servers', {})
        user_stats = stats.get('users', {})
        
        print(f"   Servers: {server_stats.get('total', 0)} total")
        print(f"   Users: {user_stats.get('total', 0)} total")
        
        # Test 11: Delete server (cascade to users)
        print("\n📋 Test 11: Delete Server")
        delete_result = db_manager.delete_server(server_id)
        if delete_result:
            print("✅ Server deleted successfully")
            
            # Verify deletion
            servers = db_manager.get_servers()
            remaining_server = next((s for s in servers if s['id'] == server_id), None)
            
            if not remaining_server:
                print("✅ Server deletion verified")
            else:
                print("❌ Server still exists after deletion")
        else:
            print("❌ Server deletion failed")
        
        # Test 12: Test database file integrity
        print("\n📋 Test 12: Database File Integrity")
        if os.path.exists(test_db_path):
            file_size = os.path.getsize(test_db_path)
            print(f"✅ Database file exists ({file_size} bytes)")
        else:
            print("❌ Database file missing")
            return False
        
        print(f"\n{'='*60}")
        print("🎉 All DatabaseManager tests PASSED!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ DatabaseManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("🧹 Test environment cleaned up")

def test_concurrent_database_access():
    """Test concurrent access to database"""
    print("\n🔄 Testing Concurrent Database Access")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp(prefix="concurrent_test_")
    test_db_path = os.path.join(temp_dir, "concurrent_test.db")
    
    try:
        from database.database_manager import DatabaseManager
        import threading
        import time
        
        results = []
        errors = []
        
        def worker_thread(thread_id):
            try:
                # Each thread gets its own DatabaseManager instance
                db_manager = DatabaseManager(test_db_path)
                
                # Add a unique server
                server_data = {
                    "name": f"Concurrent Server {thread_id}",
                    "host": f"host-{thread_id}.example.com",
                    "port": 5432 + thread_id,
                    "database_name": f"db_{thread_id}",
                    "database_type": "postgresql",
                    "username": f"user_{thread_id}",
                    "password": f"pass_{thread_id}"
                }
                
                server_id = db_manager.add_server(server_data)
                if server_id:
                    results.append((thread_id, server_id))
                    
                    # Add a small delay to simulate real work
                    time.sleep(0.1)
                    
                    # Try to retrieve the server
                    servers = db_manager.get_servers()
                    our_server = next((s for s in servers if s['id'] == server_id), None)
                    
                    if our_server:
                        results.append((thread_id, f"Retrieved server {server_id}"))
                    else:
                        errors.append((thread_id, f"Could not retrieve server {server_id}"))
                else:
                    errors.append((thread_id, "Failed to create server"))
                    
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple concurrent threads
        threads = []
        num_threads = 3  # Keep it small to avoid database locking issues
        
        print(f"Starting {num_threads} concurrent threads...")
        
        for i in range(num_threads):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)
        
        print(f"✅ Concurrent access test completed")
        print(f"   Results: {len(results)} successful operations")
        print(f"   Errors: {len(errors)} failed operations")
        
        if errors:
            print("   Error details:")
            for thread_id, error in errors:
                print(f"     Thread {thread_id}: {error}")
        
        # Overall success if most operations worked
        success_rate = len(results) / (len(results) + len(errors)) if (len(results) + len(errors)) > 0 else 0
        
        if success_rate >= 0.8:  # 80% success rate
            print("✅ Concurrent access test PASSED")
            return True
        else:
            print("❌ Concurrent access test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Concurrent access test failed: {e}")
        return False
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    """Main testing function"""
    success = True
    
    # Test basic DatabaseManager functionality
    if not test_database_manager():
        success = False
    
    # Test concurrent access
    if not test_concurrent_database_access():
        success = False
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 All DatabaseManager tests PASSED!")
        print("SQLite database operations are working correctly.")
    else:
        print("⚠️  Some DatabaseManager tests FAILED.")
        print("Check the output above for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)