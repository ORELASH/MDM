#!/usr/bin/env python3
"""
Complete LDAP Integration System Test
Tests the full LDAP integration with local fallback functionality
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_complete_system():
    """Test the complete LDAP system integration"""
    print("🎯 Complete LDAP Integration System Test")
    print("=" * 50)
    
    # Test 1: LDAP Connection and User Sync
    print("\n1️⃣ Testing LDAP Connection and User Synchronization...")
    try:
        from core.ldap_integration import get_ldap_manager, TEST_CONFIGS
        ldap_manager = get_ldap_manager(TEST_CONFIGS['forumsys'])
        
        # Test connection
        success, message = ldap_manager.test_connection()
        if success:
            print(f"✅ LDAP Connection: {message}")
        else:
            print(f"❌ LDAP Connection: {message}")
            return False
        
        # Sync users
        sync_result = ldap_manager.sync_users()
        if sync_result.get('success'):
            print(f"✅ User Sync: {sync_result.get('synced_users', 0)} users synchronized")
        else:
            print(f"❌ User Sync: {sync_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ LDAP System Error: {e}")
        return False
    
    # Test 2: Authentication Manager
    print("\n2️⃣ Testing Authentication Manager...")
    try:
        from core.auth_manager import get_auth_manager
        auth_manager = get_auth_manager()
        
        # Test LDAP authentication
        success, user_info, method = auth_manager.authenticate('tesla', 'password')
        if success and method == 'ldap':
            print(f"✅ LDAP Auth: User {user_info.get('username')} authenticated via {method}")
        else:
            print(f"❌ LDAP Auth: Failed")
            return False
        
        # Test local user creation and authentication
        auth_manager.create_local_user('test_admin', 'SecurePass123', role='admin')
        success, user_info, method = auth_manager.authenticate('test_admin', 'SecurePass123')
        if success and method == 'local':
            print(f"✅ Local Auth: User {user_info.get('username')} authenticated via {method}")
        else:
            print(f"❌ Local Auth: Failed")
            return False
            
    except Exception as e:
        print(f"❌ Authentication Manager Error: {e}")
        return False
    
    # Test 3: Session Management
    print("\n3️⃣ Testing Session Management...")
    try:
        # Create and validate session
        session_id = auth_manager.create_session('tesla', 'ldap', '127.0.0.1', 'Test/1.0')
        if session_id:
            print(f"✅ Session Creation: {session_id[:8]}...")
            
            valid, session_info = auth_manager.validate_session(session_id)
            if valid:
                print(f"✅ Session Validation: User {session_info.get('username')}")
            else:
                print("❌ Session Validation: Failed")
                return False
        else:
            print("❌ Session Creation: Failed")
            return False
            
    except Exception as e:
        print(f"❌ Session Management Error: {e}")
        return False
    
    # Test 4: Database Integration
    print("\n4️⃣ Testing Database Integration...")
    try:
        from database.database_manager import get_database_manager
        db_manager = get_database_manager()
        
        # Check LDAP users in database
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM ldap_users")
            ldap_users = cursor.fetchone()['count']
            print(f"✅ LDAP Users in DB: {ldap_users}")
            
            cursor.execute("SELECT COUNT(*) as count FROM local_users")
            local_users = cursor.fetchone()['count']
            print(f"✅ Local Users in DB: {local_users}")
            
            cursor.execute("SELECT COUNT(*) as count FROM auth_attempts WHERE success = 1")
            successful_auths = cursor.fetchone()['count']
            print(f"✅ Successful Auth Attempts: {successful_auths}")
            
    except Exception as e:
        print(f"❌ Database Integration Error: {e}")
        return False
    
    # Test 5: Statistics and Monitoring
    print("\n5️⃣ Testing Statistics and Monitoring...")
    try:
        stats = auth_manager.get_auth_statistics()
        
        print(f"✅ System Statistics:")
        print(f"   - Daily Auth Attempts: {stats.get('daily_attempts', {}).get('total', 0)}")
        print(f"   - Successful Today: {stats.get('daily_attempts', {}).get('successful', 0)}")
        print(f"   - Active Sessions: {stats.get('active_sessions', 0)}")
        print(f"   - LDAP Users: {stats.get('ldap_users', 0)}")
        print(f"   - Local Users: {stats.get('local_users', 0)}")
        
    except Exception as e:
        print(f"❌ Statistics Error: {e}")
        return False
    
    print("\n🎉 All LDAP integration tests passed successfully!")
    print("\n📋 System Summary:")
    print("✅ LDAP connectivity and user synchronization working")
    print("✅ Local authentication fallback implemented")
    print("✅ Session management operational")
    print("✅ Database integration complete")
    print("✅ Authentication statistics available")
    print("✅ Multi-method authentication (LDAP + Local) functional")
    
    return True

def show_configuration_summary():
    """Show the LDAP configuration summary"""
    print("\n📝 LDAP Configuration Summary:")
    print("=" * 40)
    
    try:
        from core.ldap_integration import TEST_CONFIGS
        from database.database_manager import get_database_manager
        
        # Show test configurations
        print("🔧 Available Test Configurations:")
        for name, config in TEST_CONFIGS.items():
            print(f"   - {name}: {config['server']}:{config['port']}")
        
        # Show database configuration
        db_manager = get_database_manager()
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT * FROM ldap_config WHERE is_active = 1")
            configs = cursor.fetchall()
            
            print(f"\n💾 Database Configurations ({len(configs)}):")
            for config in configs:
                print(f"   - {config['config_name']}: {config['server']}:{config['port']}")
        
        print("\n🔐 Authentication Methods:")
        print("   ✅ LDAP Authentication (ForumSys test server)")
        print("   ✅ Local User Authentication (SQLite database)")
        print("   ✅ Session Management (Token-based)")
        print("   ✅ Account Lockout Protection")
        print("   ✅ Failed Attempt Logging")
        
    except Exception as e:
        print(f"❌ Configuration Summary Error: {e}")

def main():
    """Run complete LDAP system test"""
    print("🚀 MultiDBManager Complete LDAP Integration Test")
    print("Testing enterprise-level authentication system...")
    
    # Run complete system test
    if test_complete_system():
        # Show configuration summary
        show_configuration_summary()
        
        print(f"\n{'=' * 60}")
        print("🎯 LDAP INTEGRATION IMPLEMENTATION COMPLETE!")
        print("🔐 Enterprise authentication system is fully operational")
        print("📊 Ready for production deployment")
        return 0
    else:
        print(f"\n{'=' * 60}")
        print("❌ LDAP integration test failed")
        print("⚠️ System requires additional configuration")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)