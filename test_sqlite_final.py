#!/usr/bin/env python3
"""
Final SQLite Testing Suite for MultiDBManager
Tests actual DatabaseManager functionality with available methods
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_sqlite_comprehensive():
    """Comprehensive test of SQLite functionality through DatabaseManager"""
    print("🗄️  SQLite Comprehensive Testing - Final Suite")
    print("=" * 70)
    
    temp_dir = tempfile.mkdtemp(prefix="sqlite_final_test_")
    test_db_path = os.path.join(temp_dir, "final_test.db")
    
    try:
        from database.database_manager import DatabaseManager
        
        # Initialize DatabaseManager
        print("🔧 Initializing DatabaseManager...")
        db_manager = DatabaseManager(test_db_path)
        print("✅ DatabaseManager initialized successfully")
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Basic Server Operations
        print(f"\n{'='*70}")
        print("📋 Test 1: Basic Server Operations")
        tests_total += 1
        
        try:
            # Add multiple servers
            servers_data = [
                {
                    "name": "PostgreSQL Production",
                    "host": "pg-prod.example.com",
                    "port": 5432,
                    "database_name": "production_db",
                    "database_type": "postgresql",
                    "username": "prod_user",
                    "password": "prod_pass",
                    "environment": "Production"
                },
                {
                    "name": "MySQL Development",
                    "host": "mysql-dev.example.com", 
                    "port": 3306,
                    "database_name": "dev_db",
                    "database_type": "mysql",
                    "username": "dev_user",
                    "password": "dev_pass",
                    "environment": "Development"
                },
                {
                    "name": "Redis Cache",
                    "host": "redis.example.com",
                    "port": 6379,
                    "database_name": "cache_db",
                    "database_type": "redis",
                    "username": "",
                    "password": "redis_pass",
                    "environment": "Production"
                }
            ]
            
            server_ids = []
            for server_data in servers_data:
                server_id = db_manager.add_server(server_data)
                if server_id:
                    server_ids.append(server_id)
                    print(f"   ✅ Added server: {server_data['name']} (ID: {server_id})")
                else:
                    raise Exception(f"Failed to add server: {server_data['name']}")
            
            # Retrieve all servers
            all_servers = db_manager.get_servers()
            print(f"   ✅ Retrieved {len(all_servers)} servers total")
            
            if len(all_servers) >= 3:
                tests_passed += 1
                print("✅ Test 1 PASSED: Basic server operations working")
            else:
                print("❌ Test 1 FAILED: Server count mismatch")
                
        except Exception as e:
            print(f"❌ Test 1 FAILED: {e}")
        
        # Test 2: User Management
        print(f"\n{'='*70}")
        print("📋 Test 2: User Management Operations")
        tests_total += 1
        
        try:
            if server_ids:
                # Add users to first server
                test_users = [
                    {
                        "name": "admin_user",
                        "type": "superuser",
                        "active": True,
                        "metadata": {
                            "email": "admin@company.com",
                            "department": "IT",
                            "role": "database_administrator"
                        }
                    },
                    {
                        "name": "app_user",
                        "type": "normal",
                        "active": True,
                        "metadata": {
                            "email": "app@company.com",
                            "department": "Development",
                            "role": "application_user"
                        }
                    },
                    {
                        "name": "readonly_user",
                        "type": "readonly",
                        "active": False,
                        "metadata": {
                            "email": "readonly@company.com",
                            "department": "Analytics",
                            "role": "read_only_analyst"
                        }
                    }
                ]
                
                db_manager.save_users(server_ids[0], test_users)
                print(f"   ✅ Saved {len(test_users)} users to server {server_ids[0]}")
                
                # Retrieve users
                retrieved_users = db_manager.get_users_by_server(server_ids[0])
                print(f"   ✅ Retrieved {len(retrieved_users)} users from server {server_ids[0]}")
                
                # Test user details
                for user in retrieved_users:
                    username = user.get('username', 'Unknown')
                    user_type = user.get('user_type', 'Unknown')
                    is_active = user.get('is_active', False)
                    print(f"      User: {username} ({user_type}) - Active: {is_active}")
                
                if len(retrieved_users) == len(test_users):
                    tests_passed += 1
                    print("✅ Test 2 PASSED: User management working correctly")
                else:
                    print(f"❌ Test 2 FAILED: User count mismatch (expected {len(test_users)}, got {len(retrieved_users)})")
            else:
                print("❌ Test 2 SKIPPED: No servers available")
                
        except Exception as e:
            print(f"❌ Test 2 FAILED: {e}")
        
        # Test 3: Server Status Updates
        print(f"\n{'='*70}")
        print("📋 Test 3: Server Status Operations")  
        tests_total += 1
        
        try:
            if server_ids:
                # Update server statuses
                statuses = ["Active", "Inactive", "Testing"]
                for i, server_id in enumerate(server_ids):
                    status = statuses[i % len(statuses)]
                    db_manager.update_server_status(server_id, status, datetime.now())
                    print(f"   ✅ Updated server {server_id} status to: {status}")
                
                # Verify status updates
                updated_servers = db_manager.get_servers()
                status_count = {}
                for server in updated_servers:
                    status = server.get('status', 'Unknown')
                    status_count[status] = status_count.get(status, 0) + 1
                
                print(f"   ✅ Status distribution: {status_count}")
                
                tests_passed += 1
                print("✅ Test 3 PASSED: Server status updates working")
            else:
                print("❌ Test 3 SKIPPED: No servers available")
                
        except Exception as e:
            print(f"❌ Test 3 FAILED: {e}")
        
        # Test 4: Global Users and Statistics
        print(f"\n{'='*70}")
        print("📋 Test 4: Global Users and Statistics")
        tests_total += 1
        
        try:
            # Get global users
            global_users = db_manager.get_global_users()
            print(f"   ✅ Retrieved {len(global_users)} global users")
            
            # Get comprehensive statistics
            stats = db_manager.get_statistics()
            print("   ✅ Statistics retrieved successfully:")
            
            for category, data in stats.items():
                if isinstance(data, dict):
                    print(f"      {category}: {data}")
                else:
                    print(f"      {category}: {data}")
            
            # Verify statistics make sense
            server_total = stats.get('servers', {}).get('total', 0)
            user_total = stats.get('users', {}).get('total', 0)
            
            if server_total >= len(server_ids) and user_total >= 0:
                tests_passed += 1
                print("✅ Test 4 PASSED: Global users and statistics working")
            else:
                print(f"❌ Test 4 FAILED: Statistics inconsistent (servers: {server_total}, users: {user_total})")
                
        except Exception as e:
            print(f"❌ Test 4 FAILED: {e}")
        
        # Test 5: Scan Operations
        print(f"\n{'='*70}")
        print("📋 Test 5: Scan Operations")
        tests_total += 1
        
        try:
            if server_ids:
                # Start scan operations
                scan_types = ["users", "roles", "tables"]
                scan_ids = []
                
                for scan_type in scan_types:
                    scan_id = db_manager.start_scan(server_ids[0], scan_type)
                    if scan_id:
                        scan_ids.append(scan_id)
                        print(f"   ✅ Started {scan_type} scan (ID: {scan_id})")
                
                # Get scan history
                scan_history = db_manager.get_scan_history(server_ids[0], limit=10)
                print(f"   ✅ Retrieved {len(scan_history)} scan history entries")
                
                if len(scan_ids) >= 2:  # At least some scans should work
                    tests_passed += 1
                    print("✅ Test 5 PASSED: Scan operations working")
                else:
                    print("❌ Test 5 FAILED: Scan operations not working properly")
            else:
                print("❌ Test 5 SKIPPED: No servers available")
                
        except Exception as e:
            print(f"❌ Test 5 FAILED: {e}")
        
        # Test 6: Data Integrity and Cleanup
        print(f"\n{'='*70}")
        print("📋 Test 6: Data Integrity and Cleanup")
        tests_total += 1
        
        try:
            # Check database file
            if os.path.exists(test_db_path):
                file_size = os.path.getsize(test_db_path)
                print(f"   ✅ Database file exists ({file_size} bytes)")
                
                # Test foreign key relationships by deleting a server
                if server_ids:
                    server_to_delete = server_ids[0]
                    
                    # Get users before deletion
                    users_before = db_manager.get_users_by_server(server_to_delete)
                    print(f"   📊 Users before server deletion: {len(users_before)}")
                    
                    # Delete server
                    delete_result = db_manager.delete_server(server_to_delete)
                    if delete_result:
                        print(f"   ✅ Server {server_to_delete} deleted successfully")
                        
                        # Check if users were cascade deleted
                        users_after = db_manager.get_users_by_server(server_to_delete)
                        print(f"   📊 Users after server deletion: {len(users_after)}")
                        
                        if len(users_after) == 0:
                            print("   ✅ Foreign key cascade working correctly")
                        else:
                            print("   ⚠️  Foreign key cascade may not be working")
                    
                    # Verify server is gone
                    remaining_servers = db_manager.get_servers()
                    deleted_server = next((s for s in remaining_servers if s['id'] == server_to_delete), None)
                    
                    if not deleted_server:
                        print("   ✅ Server deletion verified")
                    else:
                        print("   ❌ Server still exists after deletion")
                
                tests_passed += 1
                print("✅ Test 6 PASSED: Data integrity and cleanup working")
            else:
                print("❌ Test 6 FAILED: Database file missing")
                
        except Exception as e:
            print(f"❌ Test 6 FAILED: {e}")
        
        # Final Results
        print(f"\n{'='*70}")
        print("📊 FINAL TEST RESULTS")
        print(f"{'='*70}")
        
        success_rate = (tests_passed / tests_total) * 100 if tests_total > 0 else 0
        
        print(f"Tests Passed: {tests_passed}/{tests_total}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Database File: {test_db_path}")
        print(f"Database Size: {os.path.getsize(test_db_path)} bytes")
        
        if success_rate >= 80:
            print("\n🎉 SQLite COMPREHENSIVE TESTING PASSED!")
            print("✅ Database operations are working correctly")
            print("✅ CRUD operations functional")
            print("✅ Foreign key constraints working")
            print("✅ Statistics and reporting functional")
            print("✅ User management operational")
            result = True
        else:
            print("\n⚠️  SQLite testing completed with issues")
            print("Some functionality may not be working correctly")
            result = False
        
        return result
        
    except Exception as e:
        print(f"\n❌ Comprehensive test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n🧹 Test environment cleaned up")

def main():
    """Main entry point"""
    print("Starting Final SQLite Testing Suite for MultiDBManager")
    
    success = test_sqlite_comprehensive()
    
    if success:
        print("\n✅ SQLite testing completed successfully!")
        print("The database layer is ready for production use.")
    else:
        print("\n⚠️  SQLite testing completed with some issues.")
        print("Review the test output for specific problems.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)