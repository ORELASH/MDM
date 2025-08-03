#!/usr/bin/env python3
"""
Unit Tests for Core Components
Comprehensive testing of MultiDBManager core functionality
"""

import unittest
import sys
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class TestDatabaseManager(unittest.TestCase):
    """Test Database Manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.test_db.close()
        
    def tearDown(self):
        """Clean up test environment"""
        try:
            os.unlink(self.test_db.name)
        except:
            pass
    
    def test_database_manager_initialization(self):
        """Test database manager can be initialized"""
        from database.database_manager import DatabaseManager
        
        db_manager = DatabaseManager(self.test_db.name)
        self.assertIsNotNone(db_manager)
        self.assertEqual(db_manager.db_path, self.test_db.name)
    
    def test_database_connection(self):
        """Test database connection works"""
        from database.database_manager import DatabaseManager
        
        db_manager = DatabaseManager(self.test_db.name)
        
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
    
    def test_database_schema_creation(self):
        """Test database schema is created correctly"""
        from database.database_manager import DatabaseManager
        
        db_manager = DatabaseManager(self.test_db.name)
        
        # Add LDAP schema
        import subprocess
        subprocess.run([
            'python3', '-c', 
            f'''
import sqlite3
with sqlite3.connect("{self.test_db.name}") as conn:
    with open("database/ldap_schema.sql", "r") as f:
        conn.executescript(f.read())
'''
        ], cwd=str(project_root))
        
        # Check that essential tables exist
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['servers', 'users', 'roles', 'ldap_users']
            for table in expected_tables:
                self.assertIn(table, tables, f"Table {table} should exist")


class TestLDAPIntegration(unittest.TestCase):
    """Test LDAP Integration functionality"""
    
    def test_ldap_import(self):
        """Test LDAP integration can be imported"""
        from core.ldap_integration import get_ldap_manager, LDAPManager, TEST_CONFIGS, LDAP_AVAILABLE
        
        self.assertTrue(LDAP_AVAILABLE, "LDAP should be available")
        self.assertIsInstance(TEST_CONFIGS, dict)
        self.assertIn('forumsys', TEST_CONFIGS)
    
    def test_ldap_manager_creation(self):
        """Test LDAP manager can be created"""
        from core.ldap_integration import LDAPManager, TEST_CONFIGS
        
        ldap_manager = LDAPManager(TEST_CONFIGS['forumsys'])
        self.assertIsNotNone(ldap_manager)
        self.assertEqual(ldap_manager.config['server'], 'ldap.forumsys.com')
    
    @patch('core.ldap_integration.Connection')
    @patch('core.ldap_integration.Server')
    def test_ldap_connection_test(self, mock_server, mock_connection):
        """Test LDAP connection testing (mocked)"""
        from core.ldap_integration import LDAPManager, TEST_CONFIGS
        
        # Mock successful connection
        mock_conn_instance = Mock()
        mock_connection.return_value = mock_conn_instance
        mock_conn_instance.search.return_value = True
        
        ldap_manager = LDAPManager(TEST_CONFIGS['forumsys'])
        success, message = ldap_manager.test_connection()
        
        self.assertTrue(success)
        self.assertIn("successful", message.lower())


class TestAuthManager(unittest.TestCase):
    """Test Authentication Manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.test_db.close()
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            os.unlink(self.test_db.name)
        except:
            pass
    
    @patch('core.auth_manager.get_database_manager')
    def test_auth_manager_initialization(self, mock_get_db):
        """Test auth manager can be initialized"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        from core.auth_manager import AuthManager
        
        auth_manager = AuthManager()
        self.assertIsNotNone(auth_manager)
        self.assertIsInstance(auth_manager.config, dict)
    
    def test_password_hashing(self):
        """Test password hashing functionality"""
        from core.auth_manager import AuthManager
        
        with patch('core.auth_manager.get_database_manager'):
            auth_manager = AuthManager()
            
            password = "test123"
            salt = "salt123"
            
            hash1 = auth_manager._hash_password(password, salt)
            hash2 = auth_manager._hash_password(password, salt)
            
            # Same password and salt should produce same hash
            self.assertEqual(hash1, hash2)
            
            # Different salt should produce different hash
            hash3 = auth_manager._hash_password(password, "different_salt")
            self.assertNotEqual(hash1, hash3)
    
    def test_password_strength_validation(self):
        """Test password strength validation"""
        from core.auth_manager import AuthManager
        
        with patch('core.auth_manager.get_database_manager'):
            auth_manager = AuthManager()
            
            # Strong password
            self.assertTrue(auth_manager._is_password_strong("StrongPass123"))
            
            # Weak passwords
            self.assertFalse(auth_manager._is_password_strong("weak"))  # Too short
            self.assertFalse(auth_manager._is_password_strong("alllowercase"))  # No upper/digits
            self.assertFalse(auth_manager._is_password_strong("ALLUPPERCASE"))  # No lower/digits


class TestUserManagement(unittest.TestCase):
    """Test User Management functionality"""
    
    def test_user_management_files_exist(self):
        """Test that user management files exist"""
        user_mgmt_path = project_root / "ui" / "pages" / "advanced_user_management.py"
        self.assertTrue(user_mgmt_path.exists(), "User management file should exist")
        
        # Check file contains expected functions
        with open(user_mgmt_path, 'r') as f:
            content = f.read()
            self.assertIn('show_advanced_user_management', content)
            self.assertIn('show_users_management', content)
    
    def test_ldap_management_files_exist(self):
        """Test that LDAP management files exist"""
        ldap_mgmt_path = project_root / "ui" / "pages" / "ldap_management.py"
        self.assertTrue(ldap_mgmt_path.exists(), "LDAP management file should exist")
        
        # Check file contains expected functions
        with open(ldap_mgmt_path, 'r') as f:
            content = f.read()
            self.assertIn('show_ldap_management', content)
            self.assertIn('show_ldap_configuration', content)


class TestConfigurationManagement(unittest.TestCase):
    """Test Configuration Management"""
    
    def test_test_configs_validity(self):
        """Test that all test configurations are valid"""
        from core.ldap_integration import TEST_CONFIGS
        
        required_keys = ['server', 'port', 'base_dn', 'bind_dn', 'bind_password']
        
        for config_name, config in TEST_CONFIGS.items():
            with self.subTest(config=config_name):
                for key in required_keys:
                    self.assertIn(key, config, f"Config {config_name} missing {key}")
                
                # Validate port is number
                self.assertIsInstance(config['port'], int)
                self.assertTrue(1 <= config['port'] <= 65535)
    
    def test_requirements_file_exists(self):
        """Test that requirements.txt exists and contains LDAP dependency"""
        requirements_path = project_root / "requirements.txt"
        self.assertTrue(requirements_path.exists(), "requirements.txt should exist")
        
        with open(requirements_path, 'r') as f:
            content = f.read()
            self.assertIn('ldap3', content, "requirements.txt should contain ldap3")


class TestErrorHandling(unittest.TestCase):
    """Test Error Handling"""
    
    def test_ldap_unavailable_graceful_handling(self):
        """Test system handles LDAP unavailability gracefully"""
        # Mock LDAP as unavailable
        with patch('core.ldap_integration.LDAP_AVAILABLE', False):
            from core.ldap_integration import LDAPManager
            
            ldap_manager = LDAPManager({})
            success, message = ldap_manager.test_connection()
            
            self.assertFalse(success)
            self.assertIn("not installed", message.lower())
    
    def test_database_error_handling(self):
        """Test database error handling"""
        from database.database_manager import DatabaseManager
        
        # Try to connect to invalid database path
        with self.assertRaises(Exception):
            db_manager = DatabaseManager("/invalid/path/database.db")


class TestIntegrationScenarios(unittest.TestCase):
    """Test Integration Scenarios"""
    
    def test_full_authentication_flow(self):
        """Test complete authentication flow"""
        # This would test the full flow from LDAP to local fallback
        # For now, just test that components can work together
        
        try:
            from core.ldap_integration import get_ldap_manager, TEST_CONFIGS
            from core.auth_manager import get_auth_manager
            
            # Should not raise exceptions
            ldap_manager = get_ldap_manager(TEST_CONFIGS['forumsys'])
            
            with patch('core.auth_manager.get_database_manager'):
                auth_manager = get_auth_manager()
            
            self.assertIsNotNone(ldap_manager)
            self.assertIsNotNone(auth_manager)
            
        except Exception as e:
            self.fail(f"Integration test failed: {e}")


if __name__ == '__main__':
    # Configure test runner
    print("🧪 MultiDBManager Core Components Unit Tests")
    print("=" * 50)
    
    # Run tests with detailed output
    unittest.main(
        verbosity=2,
        failfast=False,
        buffer=True
    )