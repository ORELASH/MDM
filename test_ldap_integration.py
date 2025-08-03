#!/usr/bin/env python3
"""
LDAP Integration Test Script for MultiDBManager
Tests LDAP connectivity and functionality without Streamlit dependencies
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_ldap_import():
    """Test if LDAP integration can be imported"""
    print("🧪 Testing LDAP integration imports...")
    
    try:
        from core.ldap_integration import get_ldap_manager, LDAPManager, TEST_CONFIGS, LDAP_AVAILABLE
        print("✅ LDAP integration module imported successfully")
        
        if LDAP_AVAILABLE:
            print("✅ LDAP3 library is available")
        else:
            print("❌ LDAP3 library not available")
            return False
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import LDAP integration: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing LDAP integration: {e}")
        return False

def test_database_tables():
    """Test if LDAP database tables exist"""
    print("\n🧪 Testing LDAP database tables...")
    
    try:
        from database.database_manager import get_database_manager
        db_manager = get_database_manager()
        
        # Check if LDAP tables exist
        with db_manager.get_cursor() as cursor:
            # Test each LDAP table
            tables = ['ldap_users', 'ldap_auth_log', 'ldap_sync_log', 'ldap_config', 'ldap_user_servers']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"✅ Table {table}: {count} records")
                except Exception as e:
                    print(f"❌ Table {table}: {e}")
                    return False
        
        print("✅ All LDAP database tables are present")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_forumsys_connection():
    """Test connection to ForumSys public LDAP server"""
    print("\n🧪 Testing ForumSys LDAP connection...")
    
    try:
        from core.ldap_integration import LDAPManager, TEST_CONFIGS
        
        # Use ForumSys test configuration
        ldap_manager = LDAPManager(TEST_CONFIGS['forumsys'])
        
        # Test connection
        success, message = ldap_manager.test_connection()
        
        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_user_search():
    """Test user search functionality"""
    print("\n🧪 Testing LDAP user search...")
    
    try:
        from core.ldap_integration import LDAPManager, TEST_CONFIGS
        
        ldap_manager = LDAPManager(TEST_CONFIGS['forumsys'])
        
        # Test getting all users
        users = ldap_manager.get_all_users()
        
        if users:
            print(f"✅ Found {len(users)} users")
            
            # Display first few users
            for i, user in enumerate(users[:3]):
                print(f"   User {i+1}: {user.get('username', 'N/A')} ({user.get('mail', 'N/A')})")
            
            return True
        else:
            print("❌ No users found")
            return False
            
    except Exception as e:
        print(f"❌ User search test failed: {e}")
        return False

def test_user_authentication():
    """Test user authentication"""
    print("\n🧪 Testing LDAP user authentication...")
    
    try:
        from core.ldap_integration import LDAPManager, TEST_CONFIGS
        
        ldap_manager = LDAPManager(TEST_CONFIGS['forumsys'])
        
        # Test authentication with known test user
        test_users = [
            ('tesla', 'password'),
            ('einstein', 'password'),
            ('newton', 'password')
        ]
        
        for username, password in test_users:
            success, user_info = ldap_manager.authenticate_user(username, password)
            
            if success:
                print(f"✅ Authentication successful for {username}")
                if user_info:
                    print(f"   Display Name: {user_info.get('displayName', 'N/A')}")
                    print(f"   Email: {user_info.get('mail', 'N/A')}")
                    print(f"   Groups: {', '.join(user_info.get('groups', []))}")
                return True
            else:
                print(f"⚠️ Authentication failed for {username}")
        
        print("❌ Authentication test failed for all test users")
        return False
            
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

def test_user_sync():
    """Test user synchronization to database"""
    print("\n🧪 Testing LDAP user synchronization...")
    
    try:
        from core.ldap_integration import LDAPManager, TEST_CONFIGS
        from database.database_manager import get_database_manager
        
        ldap_manager = LDAPManager(TEST_CONFIGS['forumsys'])
        db_manager = get_database_manager()
        
        # Test sync functionality
        sync_result = ldap_manager.sync_users()
        
        if sync_result.get('success'):
            print(f"✅ Sync successful: {sync_result.get('synced_users', 0)} users synced")
            
            # Check if users were actually saved to database
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM ldap_users")
                count = cursor.fetchone()[0]
                print(f"✅ Database now contains {count} LDAP users")
            
            return True
        else:
            print(f"❌ Sync failed: {sync_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Sync test failed: {e}")
        return False

def test_ldap_configuration():
    """Test LDAP configuration management"""
    print("\n🧪 Testing LDAP configuration management...")
    
    try:
        from database.database_manager import get_database_manager
        
        db_manager = get_database_manager()
        
        # Check if test configuration exists
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT * FROM ldap_config WHERE config_name = 'forumsys_test'")
            config = cursor.fetchone()
            
            if config:
                print("✅ Test LDAP configuration found in database")
                print(f"   Server: {config['server']}:{config['port']}")
                print(f"   Base DN: {config['base_dn']}")
                return True
            else:
                print("❌ Test LDAP configuration not found")
                return False
                
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Run all LDAP integration tests"""
    print("🚀 MultiDBManager LDAP Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("LDAP Import", test_ldap_import),
        ("Database Tables", test_database_tables),
        ("LDAP Configuration", test_ldap_configuration),
        ("ForumSys Connection", test_forumsys_connection),
        ("User Search", test_user_search),
        ("User Authentication", test_user_authentication),
        ("User Synchronization", test_user_sync),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
    
    print(f"\n{'=' * 50}")
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! LDAP integration is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the configuration and installation.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)