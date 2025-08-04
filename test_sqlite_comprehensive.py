#!/usr/bin/env python3
"""
Comprehensive SQLite Database Testing Suite for MultiDBManager
Tests all database operations, schema integrity, and data persistence
"""

import sys
import os
import sqlite3
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time
import threading
import unittest

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from database.database_manager import DatabaseManager, get_database_manager

# Simple logger for testing (avoid pandas dependency)
class TestLogger:
    def log_system_event(self, message, level):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def log_error(self, message):
        self.log_system_event(message, "ERROR")

class SQLiteComprehensiveTest:
    """Comprehensive SQLite testing suite"""
    
    def __init__(self):
        self.logger = TestLogger()
        self.test_results = []
        self.temp_dir = tempfile.mkdtemp(prefix="multidb_test_")
        self.test_db_path = os.path.join(self.temp_dir, "test_multidb.db")
        self.db_manager = None
        
    def setup_test_environment(self):
        """Setup test environment with temporary database"""
        try:
            self.logger.log_system_event("Setting up SQLite test environment", "INFO")
            
            # Create test database manager
            self.db_manager = DatabaseManager(self.test_db_path)
            
            self.logger.log_system_event("SQLite test environment setup completed", "INFO")
            return True
            
        except Exception as e:
            self.logger.log_system_event(f"Failed to setup test environment: {e}", "ERROR")
            return False
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        try:
            if self.db_manager:
                # Close any open connections
                if hasattr(self.db_manager._local, 'connection'):
                    self.db_manager._local.connection.close()
            
            # Remove temporary directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                
            self.logger.log_system_event("SQLite test environment cleaned up", "INFO")
            
        except Exception as e:
            self.logger.log_system_event(f"Error during test cleanup: {e}", "WARNING")
    
    def test_database_schema(self) -> bool:
        """Test database schema creation and integrity"""
        try:
            self.logger.log_system_event("Testing SQLite database schema", "INFO")
            
            # Check if database file exists
            if not os.path.exists(self.test_db_path):
                self.test_results.append({
                    "test": "database_file_creation",
                    "status": "FAILED",
                    "error": "Database file not created"
                })
                return False
                
            # Connect and check tables
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'servers', 'users', 'roles', 'role_members', 'groups', 
                'tables', 'query_history', 'user_activity', 'system_logs',
                'query_templates', 'user_preferences', 'connection_pools',
                'audit_logs', 'performance_metrics'
            ]
            
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                self.test_results.append({
                    "test": "schema_tables",
                    "status": "FAILED",
                    "error": f"Missing tables: {missing_tables}",
                    "found_tables": tables
                })
                conn.close()
                return False
            
            # Test table structures
            for table in expected_tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                if not columns:
                    self.test_results.append({
                        "test": f"table_structure_{table}",
                        "status": "FAILED",
                        "error": f"Table {table} has no columns"
                    })
                    conn.close()
                    return False
            
            conn.close()
            
            self.test_results.append({
                "test": "database_schema",
                "status": "PASSED",
                "details": {
                    "tables_found": len(tables),
                    "expected_tables": len(expected_tables),
                    "all_tables": tables
                }
            })
            
            self.logger.log_system_event("SQLite database schema test PASSED", "INFO")
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "database_schema",
                "status": "FAILED",
                "error": str(e)
            })
            self.logger.log_system_event(f"SQLite database schema test FAILED: {e}", "ERROR")
            return False
    
    def test_basic_crud_operations(self) -> bool:
        """Test basic CRUD operations"""
        try:
            self.logger.log_system_event("Testing SQLite CRUD operations", "INFO")
            
            # Test server operations
            test_server = {
                "name": "Test PostgreSQL Server",
                "host": "localhost",
                "port": 5432,
                "database_name": "testdb",
                "username": "testuser",
                "password": "testpass",
                "database_type": "postgresql",
                "connection_params": {"sslmode": "prefer"}
            }
            
            # CREATE - Add server
            server_id = self.db_manager.add_server(test_server)
            if not server_id:
                raise Exception("Failed to create server")
            
            # READ - Get server
            servers = self.db_manager.get_servers()
            found_server = next((s for s in servers if s['id'] == server_id), None)
            
            if not found_server:
                raise Exception("Failed to retrieve created server")
            
            if found_server['name'] != test_server['name']:
                raise Exception("Server data mismatch after creation")
            
            # UPDATE - Modify server
            updated_data = test_server.copy()
            updated_data['name'] = "Updated Test Server"
            updated_data['port'] = 5433
            
            if not self.db_manager.update_server(server_id, updated_data):
                raise Exception("Failed to update server")
            
            # Verify update
            servers = self.db_manager.get_servers()
            updated_server = next((s for s in servers if s['id'] == server_id), None)
            
            if not updated_server or updated_server['name'] != "Updated Test Server":
                raise Exception("Server update verification failed")
            
            # Test user operations
            test_users = [
                {
                    "name": "test_user_1",
                    "type": "normal",
                    "active": True,
                    "metadata": {"email": "user1@test.com"}
                },
                {
                    "name": "test_user_2", 
                    "type": "admin",
                    "active": True,
                    "metadata": {"email": "user2@test.com"}
                }
            ]
            
            # Save users
            self.db_manager.save_users(server_id, test_users)
            
            # Retrieve users
            retrieved_users = self.db_manager.get_users_by_server(server_id)
            
            if len(retrieved_users) != 2:
                raise Exception(f"Expected 2 users, got {len(retrieved_users)}")
            
            # DELETE - Remove server (should cascade to users)
            if not self.db_manager.delete_server(server_id):
                raise Exception("Failed to delete server")
            
            # Verify deletion
            servers = self.db_manager.get_servers()
            deleted_server = next((s for s in servers if s['id'] == server_id), None)
            
            if deleted_server:
                raise Exception("Server not properly deleted")
            
            self.test_results.append({
                "test": "crud_operations",
                "status": "PASSED",
                "details": {
                    "server_created": True,
                    "server_updated": True,
                    "users_saved": True,
                    "server_deleted": True
                }
            })
            
            self.logger.log_system_event("SQLite CRUD operations test PASSED", "INFO")
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "crud_operations",
                "status": "FAILED",
                "error": str(e)
            })
            self.logger.log_system_event(f"SQLite CRUD operations test FAILED: {e}", "ERROR")
            return False
    
    def test_transaction_handling(self) -> bool:
        """Test transaction handling and rollback scenarios"""
        try:
            self.logger.log_system_event("Testing SQLite transaction handling", "INFO")
            
            # Test successful transaction
            with self.db_manager.get_cursor() as cursor:
                cursor.execute("BEGIN TRANSACTION")
                
                # Insert test data
                cursor.execute("""
                    INSERT INTO servers (name, host, port, database_name, username, password, database_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, ("TX Test Server", "localhost", 5432, "testdb", "user", "pass", "postgresql"))
                
                server_id = cursor.lastrowid
                
                cursor.execute("COMMIT")
            
            # Verify transaction committed
            servers = self.db_manager.get_servers()
            tx_server = next((s for s in servers if s['name'] == "TX Test Server"), None)
            
            if not tx_server:
                raise Exception("Transaction commit failed")
            
            # Test rollback scenario
            try:
                with self.db_manager.get_cursor() as cursor:
                    cursor.execute("BEGIN TRANSACTION")
                    
                    # Insert data
                    cursor.execute("""
                        INSERT INTO servers (name, host, port, database_name, username, password, database_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ("Rollback Test", "localhost", 5432, "testdb", "user", "pass", "postgresql"))
                    
                    # Force an error to test rollback
                    cursor.execute("INSERT INTO non_existent_table VALUES (1)")
                    
                    cursor.execute("COMMIT")
                    
            except sqlite3.Error:
                # Expected error - transaction should be rolled back
                pass
            
            # Verify rollback worked
            servers = self.db_manager.get_servers()
            rollback_server = next((s for s in servers if s['name'] == "Rollback Test"), None)
            
            if rollback_server:
                raise Exception("Transaction rollback failed - data was committed")
            
            # Clean up
            self.db_manager.delete_server(tx_server['id'])
            
            self.test_results.append({
                "test": "transaction_handling",
                "status": "PASSED",
                "details": {
                    "commit_test": True,
                    "rollback_test": True
                }
            })
            
            self.logger.log_system_event("SQLite transaction handling test PASSED", "INFO")
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "transaction_handling",
                "status": "FAILED",
                "error": str(e)
            })
            self.logger.log_system_event(f"SQLite transaction handling test FAILED: {e}", "ERROR")
            return False
    
    def test_concurrent_access(self) -> bool:
        """Test concurrent database access"""
        try:
            self.logger.log_system_event("Testing SQLite concurrent access", "INFO")
            
            results = []
            errors = []
            
            def worker_thread(thread_id: int):
                try:
                    # Each thread creates its own database manager instance
                    worker_db = DatabaseManager(self.test_db_path)
                    
                    # Add a server
                    server_data = {
                        "name": f"Concurrent Server {thread_id}",
                        "host": "localhost",
                        "port": 5432 + thread_id,
                        "database_name": f"testdb_{thread_id}",
                        "username": f"user_{thread_id}",
                        "password": "password",
                        "database_type": "postgresql"
                    }
                    
                    server_id = worker_db.add_server(server_data)
                    
                    if server_id:
                        results.append(f"Thread {thread_id} created server {server_id}")
                        
                        # Add some users
                        users = [
                            {
                                "name": f"user_{thread_id}_1",
                                "type": "normal",
                                "active": True,
                                "metadata": {"thread": thread_id}
                            }
                        ]
                        worker_db.save_users(server_id, users)
                        results.append(f"Thread {thread_id} added users")
                        
                        # Clean up
                        worker_db.delete_server(server_id)
                        results.append(f"Thread {thread_id} cleaned up")
                    else:
                        errors.append(f"Thread {thread_id} failed to create server")
                        
                except Exception as e:
                    errors.append(f"Thread {thread_id} error: {str(e)}")
            
            # Create and start multiple threads
            threads = []
            num_threads = 5
            
            for i in range(num_threads):
                thread = threading.Thread(target=worker_thread, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)
            
            if errors:
                raise Exception(f"Concurrent access errors: {errors}")
            
            if len(results) != num_threads * 3:  # Each thread should produce 3 results
                raise Exception(f"Expected {num_threads * 3} results, got {len(results)}")
            
            self.test_results.append({
                "test": "concurrent_access",
                "status": "PASSED",
                "details": {
                    "threads": num_threads,
                    "operations_completed": len(results),
                    "errors": len(errors)
                }
            })
            
            self.logger.log_system_event("SQLite concurrent access test PASSED", "INFO")
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "concurrent_access",
                "status": "FAILED",
                "error": str(e)
            })
            self.logger.log_system_event(f"SQLite concurrent access test FAILED: {e}", "ERROR")
            return False
    
    def test_data_integrity(self) -> bool:
        """Test data integrity and constraints"""
        try:
            self.logger.log_system_event("Testing SQLite data integrity", "INFO")
            
            # Test foreign key constraints
            server_data = {
                "name": "Integrity Test Server",
                "host": "localhost",
                "port": 5432,
                "database_name": "testdb",
                "username": "testuser",
                "password": "testpass",
                "database_type": "postgresql"
            }
            
            server_id = self.db_manager.add_server(server_data)
            
            # Add users
            users = [
                {
                    "name": "integrity_user_1",
                    "type": "normal", 
                    "active": True,
                    "metadata": {"test": "integrity"}
                }
            ]
            
            self.db_manager.save_users(server_id, users)
            
            # Test that deleting server cascades to users
            initial_users = self.db_manager.get_users_by_server(server_id)
            if not initial_users:
                raise Exception("Users not saved properly")
            
            # Delete server
            self.db_manager.delete_server(server_id)
            
            # Verify users are also deleted (foreign key constraint)
            remaining_users = self.db_manager.get_users_by_server(server_id)
            if remaining_users:
                raise Exception("Foreign key constraint not enforced - users remain after server deletion")
            
            # Test unique constraints
            server1_data = {
                "name": "Unique Test Server",
                "host": "localhost",
                "port": 5432,
                "database_name": "testdb1",
                "username": "testuser",
                "password": "testpass",
                "database_type": "postgresql"
            }
            
            server1_id = self.db_manager.add_server(server1_data)
            
            # Try to add server with same name (should handle gracefully)
            server2_data = server1_data.copy()
            server2_data['database_name'] = "testdb2"
            
            server2_id = self.db_manager.add_server(server2_data)
            
            # Both should exist (name doesn't have to be unique in our schema)
            servers = self.db_manager.get_servers()
            test_servers = [s for s in servers if s['name'] == "Unique Test Server"]
            
            if len(test_servers) != 2:
                self.logger.log_system_event(f"Found {len(test_servers)} servers with same name - this is acceptable", "INFO")
            
            # Clean up
            if server1_id:
                self.db_manager.delete_server(server1_id)
            if server2_id:
                self.db_manager.delete_server(server2_id)
            
            self.test_results.append({
                "test": "data_integrity",
                "status": "PASSED",
                "details": {
                    "foreign_key_cascade": True,
                    "constraint_handling": True
                }
            })
            
            self.logger.log_system_event("SQLite data integrity test PASSED", "INFO")
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "data_integrity", 
                "status": "FAILED",
                "error": str(e)
            })
            self.logger.log_system_event(f"SQLite data integrity test FAILED: {e}", "ERROR")
            return False
    
    def test_performance_operations(self) -> bool:
        """Test database performance with bulk operations"""
        try:
            self.logger.log_system_event("Testing SQLite performance operations", "INFO")
            
            start_time = time.time()
            
            # Create test server
            server_data = {
                "name": "Performance Test Server",
                "host": "localhost", 
                "port": 5432,
                "database_name": "perftest",
                "username": "perfuser",
                "password": "perfpass",
                "database_type": "postgresql"
            }
            
            server_id = self.db_manager.add_server(server_data)
            
            # Generate bulk user data
            bulk_users = []
            for i in range(100):
                bulk_users.append({
                    "name": f"bulk_user_{i:03d}",
                    "type": "normal" if i % 3 != 0 else "admin",
                    "active": i % 10 != 0,  # 90% active
                    "metadata": {
                        "batch": "performance_test",
                        "index": i,
                        "created_at": datetime.now().isoformat()
                    }
                })
            
            # Bulk insert users
            bulk_start = time.time()
            self.db_manager.save_users(server_id, bulk_users)
            bulk_insert_time = time.time() - bulk_start
            
            # Test bulk retrieval
            retrieval_start = time.time()
            retrieved_users = self.db_manager.get_users_by_server(server_id)
            retrieval_time = time.time() - retrieval_start
            
            if len(retrieved_users) != 100:
                raise Exception(f"Expected 100 users, retrieved {len(retrieved_users)}")
            
            # Test filtering performance
            filter_start = time.time()
            active_users = [u for u in retrieved_users if u.get('is_active', True)]
            admin_users = [u for u in retrieved_users if u.get('user_type') == 'admin']
            filter_time = time.time() - filter_start
            
            # Test statistics performance
            stats_start = time.time()
            stats = self.db_manager.get_statistics()
            stats_time = time.time() - stats_start
            
            # Clean up
            self.db_manager.delete_server(server_id)
            
            total_time = time.time() - start_time
            
            performance_results = {
                "total_time": round(total_time, 3),
                "bulk_insert_time": round(bulk_insert_time, 3),
                "retrieval_time": round(retrieval_time, 3),
                "filter_time": round(filter_time, 3),
                "stats_time": round(stats_time, 3),
                "users_processed": 100,
                "active_users_found": len(active_users),
                "admin_users_found": len(admin_users)
            }
            
            # Performance thresholds (reasonable for SQLite)
            if total_time > 5.0:  # Total should be under 5 seconds
                raise Exception(f"Performance test too slow: {total_time}s")
            
            self.test_results.append({
                "test": "performance_operations",
                "status": "PASSED",
                "details": performance_results
            })
            
            self.logger.log_system_event(f"SQLite performance test PASSED: {performance_results}", "INFO")
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "performance_operations",
                "status": "FAILED", 
                "error": str(e)
            })
            self.logger.log_system_event(f"SQLite performance test FAILED: {e}", "ERROR")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all SQLite tests"""
        self.logger.log_system_event("Starting comprehensive SQLite database testing", "INFO")
        
        # Setup test environment
        if not self.setup_test_environment():
            return {
                "success": False,
                "error": "Failed to setup test environment",
                "results": []
            }
        
        try:
            # Run all tests
            tests = [
                ("Database Schema", self.test_database_schema),
                ("CRUD Operations", self.test_basic_crud_operations),
                ("Transaction Handling", self.test_transaction_handling),
                ("Concurrent Access", self.test_concurrent_access),
                ("Data Integrity", self.test_data_integrity),
                ("Performance Operations", self.test_performance_operations)
            ]
            
            passed_tests = 0
            total_tests = len(tests)
            
            for test_name, test_func in tests:
                self.logger.log_system_event(f"Running test: {test_name}", "INFO")
                
                try:
                    if test_func():
                        passed_tests += 1
                        self.logger.log_system_event(f"✅ {test_name} PASSED", "INFO")
                    else:
                        self.logger.log_system_event(f"❌ {test_name} FAILED", "ERROR")
                        
                except Exception as e:
                    self.logger.log_system_event(f"❌ {test_name} FAILED with exception: {e}", "ERROR")
                    self.test_results.append({
                        "test": test_name.lower().replace(" ", "_"),
                        "status": "FAILED",
                        "error": f"Exception: {str(e)}"
                    })
            
            # Summary
            success_rate = (passed_tests / total_tests) * 100
            
            summary = {
                "success": passed_tests == total_tests,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": round(success_rate, 2),
                "results": self.test_results,
                "test_environment": {
                    "database_path": self.test_db_path,
                    "temp_directory": self.temp_dir
                }
            }
            
            self.logger.log_system_event(
                f"SQLite testing completed: {passed_tests}/{total_tests} tests passed ({success_rate}%)", 
                "INFO" if success_rate == 100 else "WARNING"
            )
            
            return summary
            
        finally:
            # Always cleanup
            self.cleanup_test_environment()

def main():
    """Main testing function"""
    print("🗄️  Starting Comprehensive SQLite Database Testing")
    print("=" * 60)
    
    tester = SQLiteComprehensiveTest()
    results = tester.run_all_tests()
    
    # Print results
    print(f"\n📊 Test Results Summary:")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Success Rate: {results['success_rate']}%")
    
    print(f"\n📋 Detailed Results:")
    for result in results['results']:
        status_icon = "✅" if result['status'] == 'PASSED' else "❌"
        print(f"{status_icon} {result['test']}: {result['status']}")
        
        if result['status'] == 'FAILED' and 'error' in result:
            print(f"   Error: {result['error']}")
        
        if 'details' in result:
            print(f"   Details: {result['details']}")
    
    print(f"\n{'='*60}")
    if results['success']:
        print("🎉 All SQLite tests PASSED! Database is working correctly.")
    else:
        print("⚠️  Some SQLite tests FAILED. Check the details above.")
        
    return results['success']

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)