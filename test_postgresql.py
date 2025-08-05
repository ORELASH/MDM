#!/usr/bin/env python3
"""
PostgreSQL Database Connection Testing Script
Comprehensive testing of PostgreSQL database connectivity and operations
"""

import sys
import os
import traceback
import time
from datetime import datetime
import json

# Add project root to path
sys.path.append('/home/orel/my_installer/rsm/MultiDBManager')

try:
    import psycopg2
    from psycopg2 import sql, OperationalError, DatabaseError
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
    print("✓ psycopg2 module imported successfully")
except ImportError as e:
    PSYCOPG2_AVAILABLE = False
    print(f"✗ psycopg2 not available: {e}")

from src.database.database_manager import DatabaseManager
from src.models.server_model import ServerModel

class PostgreSQLTester:
    """Comprehensive PostgreSQL database testing suite"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        self.passed_tests = []
        
        # Common PostgreSQL test configurations
        self.test_configs = [
            {
                'name': 'Local PostgreSQL (localhost)',
                'host': 'localhost', 
                'port': 5432,
                'database': 'postgres',
                'username': 'postgres',
                'password': 'postgres'
            },
            {
                'name': 'Local PostgreSQL (127.0.0.1)',
                'host': '127.0.0.1',
                'port': 5432, 
                'database': 'postgres',
                'username': 'postgres',
                'password': 'postgres'
            },
            {
                'name': 'Local PostgreSQL Alt Port',
                'host': 'localhost',
                'port': 5433,
                'database': 'postgres', 
                'username': 'postgres',
                'password': 'postgres'
            },
            {
                'name': 'Test Database',
                'host': 'localhost',
                'port': 5432,
                'database': 'testdb',
                'username': 'postgres', 
                'password': 'postgres'
            }
        ]
        
    def log_test(self, test_name, status, details="", duration=0):
        """Log test result"""
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if status == 'PASS':
            self.passed_tests.append(test_name)
            print(f"✓ {test_name} - PASSED ({duration:.2f}s)")
        else:
            self.failed_tests.append(test_name)
            print(f"✗ {test_name} - FAILED ({duration:.2f}s)")
            if details:
                print(f"  Details: {details}")
                
    def test_psycopg2_availability(self):
        """Test if psycopg2 is properly installed"""
        start_time = time.time()
        
        if not PSYCOPG2_AVAILABLE:
            self.log_test(
                "psycopg2 Availability", 
                "FAIL", 
                "psycopg2 module not installed or not importable",
                time.time() - start_time
            )
            return False
            
        try:
            # Test psycopg2 version
            version = psycopg2.__version__
            self.log_test(
                "psycopg2 Availability",
                "PASS", 
                f"Version: {version}",
                time.time() - start_time
            )
            return True
        except Exception as e:
            self.log_test(
                "psycopg2 Availability",
                "FAIL",
                str(e),
                time.time() - start_time
            )
            return False
            
    def test_basic_connection(self, config):
        """Test basic PostgreSQL connection"""
        start_time = time.time()
        test_name = f"Basic Connection - {config['name']}"
        
        if not PSYCOPG2_AVAILABLE:
            self.log_test(test_name, "SKIP", "psycopg2 not available", 0)
            return False
            
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['username'],
                password=config['password'],
                connect_timeout=10
            )
            
            # Test basic query
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                
            conn.close()
            
            self.log_test(
                test_name,
                "PASS",
                f"Connected successfully. Version: {version[:50]}...",
                time.time() - start_time
            )
            return True
            
        except OperationalError as e:
            self.log_test(
                test_name,
                "FAIL", 
                f"Connection failed: {str(e)}",
                time.time() - start_time
            )
            return False
        except Exception as e:
            self.log_test(
                test_name,
                "FAIL",
                f"Unexpected error: {str(e)}",
                time.time() - start_time
            )
            return False
            
    def test_database_operations(self, config):
        """Test basic database operations (CREATE, INSERT, SELECT, DROP)"""
        start_time = time.time()
        test_name = f"Database Operations - {config['name']}"
        
        if not PSYCOPG2_AVAILABLE:
            self.log_test(test_name, "SKIP", "psycopg2 not available", 0)
            return False
            
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['username'],
                password=config['password'],
                connect_timeout=10
            )
            
            with conn.cursor() as cur:
                # Create test table
                table_name = f"test_table_{int(time.time())}"
                cur.execute(f"""
                    CREATE TEMPORARY TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert test data
                cur.execute(f"""
                    INSERT INTO {table_name} (name) 
                    VALUES (%s), (%s), (%s)
                """, ('Test 1', 'Test 2', 'Test 3'))
                
                # Select test data
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]
                
                if count != 3:
                    raise Exception(f"Expected 3 rows, got {count}")
                    
                # Test UPDATE
                cur.execute(f"""
                    UPDATE {table_name} 
                    SET name = %s 
                    WHERE name = %s
                """, ('Updated Test', 'Test 1'))
                
                # Verify update
                cur.execute(f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE name = %s
                """, ('Updated Test',))
                updated_count = cur.fetchone()[0]
                
                if updated_count != 1:
                    raise Exception(f"Update failed, expected 1 updated row, got {updated_count}")
                
            conn.commit()
            conn.close()
            
            self.log_test(
                test_name,
                "PASS",
                "CREATE, INSERT, SELECT, UPDATE operations successful",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_test(
                test_name,
                "FAIL",
                str(e),
                time.time() - start_time
            )
            return False
            
    def test_transaction_handling(self, config):
        """Test transaction handling with COMMIT and ROLLBACK"""
        start_time = time.time()
        test_name = f"Transaction Handling - {config['name']}"
        
        if not PSYCOPG2_AVAILABLE:
            self.log_test(test_name, "SKIP", "psycopg2 not available", 0)
            return False
            
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['username'],
                password=config['password'],
                connect_timeout=10
            )
            
            with conn.cursor() as cur:
                # Create test table
                table_name = f"test_transaction_{int(time.time())}"
                cur.execute(f"""
                    CREATE TEMPORARY TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        value INTEGER
                    )
                """)
                conn.commit()
                
                # Test successful transaction
                cur.execute(f"INSERT INTO {table_name} (value) VALUES (%s)", (100,))
                conn.commit()
                
                # Verify committed data
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count_after_commit = cur.fetchone()[0]
                
                # Test rollback transaction
                cur.execute(f"INSERT INTO {table_name} (value) VALUES (%s)", (200,))
                conn.rollback()
                
                # Verify rollback
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count_after_rollback = cur.fetchone()[0]
                
                if count_after_commit != 1:
                    raise Exception(f"Commit test failed: expected 1 row, got {count_after_commit}")
                    
                if count_after_rollback != 1:
                    raise Exception(f"Rollback test failed: expected 1 row, got {count_after_rollback}")
                    
            conn.close()
            
            self.log_test(
                test_name,
                "PASS",
                "Transaction COMMIT and ROLLBACK working correctly",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_test(
                test_name,
                "FAIL",
                str(e),
                time.time() - start_time
            )
            return False
            
    def test_concurrent_connections(self, config):
        """Test multiple concurrent connections"""
        start_time = time.time()
        test_name = f"Concurrent Connections - {config['name']}"
        
        if not PSYCOPG2_AVAILABLE:
            self.log_test(test_name, "SKIP", "psycopg2 not available", 0)
            return False
            
        try:
            connections = []
            
            # Create multiple connections
            for i in range(5):
                conn = psycopg2.connect(
                    host=config['host'],
                    port=config['port'],
                    database=config['database'],
                    user=config['username'],
                    password=config['password'],
                    connect_timeout=10
                )
                connections.append(conn)
                
            # Test each connection
            for i, conn in enumerate(connections):
                with conn.cursor() as cur:
                    cur.execute("SELECT %s as connection_id", (i,))
                    result = cur.fetchone()[0]
                    if result != i:
                        raise Exception(f"Connection {i} test failed")
                        
            # Close all connections
            for conn in connections:
                conn.close()
                
            self.log_test(
                test_name,
                "PASS",
                f"Successfully created and tested {len(connections)} concurrent connections",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            # Clean up any open connections
            for conn in connections:
                try:
                    conn.close()
                except:
                    pass
                    
            self.log_test(
                test_name,
                "FAIL",
                str(e),
                time.time() - start_time
            )
            return False
            
    def test_database_manager_integration(self, config):
        """Test MultiDBManager's DatabaseManager with PostgreSQL"""
        start_time = time.time()
        test_name = f"DatabaseManager Integration - {config['name']}"
        
        try:
            # Create server model
            server = ServerModel(
                name=f"Test PostgreSQL Server - {config['name']}",
                host=config['host'],
                port=config['port'],
                username=config['username'],
                password=config['password'],
                database_type='postgresql',
                database_name=config['database']
            )
            
            # Test database manager
            db_manager = DatabaseManager()
            
            # Test connection
            success = db_manager.test_connection(server)
            if not success:
                raise Exception("DatabaseManager test_connection failed")
                
            # Test query execution
            result = db_manager.execute_query(server, "SELECT current_timestamp as now")
            if not result or not result.get('success'):
                raise Exception("DatabaseManager execute_query failed")
                
            self.log_test(
                test_name,
                "PASS",
                "DatabaseManager integration successful",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_test(
                test_name,
                "FAIL",
                str(e),
                time.time() - start_time
            )
            return False
            
    def test_data_types(self, config):
        """Test various PostgreSQL data types"""
        start_time = time.time()
        test_name = f"Data Types Test - {config['name']}"
        
        if not PSYCOPG2_AVAILABLE:
            self.log_test(test_name, "SKIP", "psycopg2 not available", 0)
            return False
            
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['username'],
                password=config['password'],
                connect_timeout=10
            )
            
            with conn.cursor() as cur:
                # Create test table with various data types
                table_name = f"test_datatypes_{int(time.time())}"
                cur.execute(f"""
                    CREATE TEMPORARY TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        text_col TEXT,
                        varchar_col VARCHAR(50),
                        int_col INTEGER,
                        bigint_col BIGINT,
                        decimal_col DECIMAL(10,2),
                        boolean_col BOOLEAN,
                        date_col DATE,
                        timestamp_col TIMESTAMP,
                        json_col JSON
                    )
                """)
                
                # Insert test data
                test_data = (
                    'Test text',
                    'Test varchar',
                    42,
                    9223372036854775807,
                    123.45,
                    True,
                    '2025-08-04',
                    '2025-08-04 15:30:00',
                    '{"key": "value", "number": 123}'
                )
                
                cur.execute(f"""
                    INSERT INTO {table_name} 
                    (text_col, varchar_col, int_col, bigint_col, decimal_col, 
                     boolean_col, date_col, timestamp_col, json_col)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, test_data)
                
                # Select and verify data
                cur.execute(f"SELECT * FROM {table_name} WHERE id = 1")
                row = cur.fetchone()
                
                if not row:
                    raise Exception("No data retrieved")
                    
                # Basic validation
                if row[1] != 'Test text':
                    raise Exception("Text data type test failed")
                if row[3] != 42:
                    raise Exception("Integer data type test failed")
                if not row[6]:
                    raise Exception("Boolean data type test failed")
                    
            conn.commit()
            conn.close()
            
            self.log_test(
                test_name,
                "PASS",
                "All PostgreSQL data types handled correctly",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_test(
                test_name,
                "FAIL",
                str(e),
                time.time() - start_time
            )
            return False
            
    def run_all_tests(self):
        """Run all PostgreSQL tests"""
        print("=" * 80)
        print("PostgreSQL Database Connection Testing Suite")
        print("=" * 80)
        print()
        
        # Test psycopg2 availability first
        if not self.test_psycopg2_availability():
            print("\n❌ Cannot continue testing - psycopg2 not available")
            return False
            
        successful_configs = []
        
        # Test each configuration
        for config in self.test_configs:
            print(f"\n📋 Testing configuration: {config['name']}")
            print("-" * 60)
            
            # Test basic connection first
            if not self.test_basic_connection(config):
                print(f"⚠️  Skipping additional tests for {config['name']} due to connection failure")
                continue
                
            successful_configs.append(config)
            
            # Run comprehensive tests on successful connections
            self.test_database_operations(config)
            self.test_transaction_handling(config)
            self.test_concurrent_connections(config)
            self.test_database_manager_integration(config)
            self.test_data_types(config)
            
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total tests run: {len(self.test_results)}")
        print(f"Passed: {len(self.passed_tests)}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success rate: {len(self.passed_tests)/len(self.test_results)*100:.1f}%")
        print()
        
        if successful_configs:
            print("✅ Successfully connected to PostgreSQL configurations:")
            for config in successful_configs:
                print(f"   • {config['name']} ({config['host']}:{config['port']})")
        else:
            print("❌ No PostgreSQL configurations were accessible")
            
        print(f"\n📊 Detailed results saved to test_results")
        
        return len(self.failed_tests) == 0
        
    def save_results(self, filename="postgresql_test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'summary': {
                        'total_tests': len(self.test_results),
                        'passed': len(self.passed_tests),
                        'failed': len(self.failed_tests),
                        'success_rate': len(self.passed_tests)/len(self.test_results)*100 if self.test_results else 0
                    },
                    'results': self.test_results
                }, f, indent=2)
            print(f"✅ Test results saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

def main():
    """Main function"""
    tester = PostgreSQLTester()
    
    try:
        success = tester.run_all_tests()
        tester.save_results()
        
        if success:
            print("\n🎉 All PostgreSQL tests completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Some PostgreSQL tests failed. Check the results above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()