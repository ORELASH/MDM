#!/usr/bin/env python3
"""
Authentication Manager Test Script
Tests both LDAP and local authentication functionality
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_auth_manager_import():
    """Test if auth manager can be imported"""
    print("🧪 Testing Auth Manager import...")
    
    try:
        from core.auth_manager import get_auth_manager, AuthManager
        print("✅ Auth Manager imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Auth Manager: {e}")
        return False

def test_local_authentication():
    """Test local authentication"""
    print("\n🧪 Testing Local Authentication...")
    
    try:
        from core.auth_manager import get_auth_manager
        
        auth_manager = get_auth_manager()
        
        # Test default admin authentication
        success, user_info, method = auth_manager.authenticate('admin', 'admin123')
        
        if success:
            print(f"✅ Default admin authentication successful")
            print(f"   Method: {method}")
            print(f"   User: {user_info.get('username', 'N/A')}")
            print(f"   Role: {user_info.get('role', 'N/A')}")
            return True
        else:
            print(f"❌ Default admin authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Local authentication test failed: {e}")
        return False

def test_create_local_user():
    """Test creating local user"""
    print("\n🧪 Testing Local User Creation...")
    
    try:
        from core.auth_manager import get_auth_manager
        
        auth_manager = get_auth_manager()
        
        # Create test user
        success = auth_manager.create_local_user(
            username='testuser',
            password='TestPass123',
            email='test@example.com',
            full_name='Test User',
            role='user'
        )
        
        if success:
            print("✅ Local user created successfully")
            
            # Test authentication
            success, user_info, method = auth_manager.authenticate('testuser', 'TestPass123')
            
            if success:
                print("✅ New user authentication successful")
                return True
            else:
                print("❌ New user authentication failed")
                return False
        else:
            print("❌ Local user creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Local user creation test failed: {e}")
        return False

def test_session_management():
    """Test session management"""
    print("\n🧪 Testing Session Management...")
    
    try:
        from core.auth_manager import get_auth_manager
        
        auth_manager = get_auth_manager()
        
        # Create session
        session_id = auth_manager.create_session('admin', 'local', '127.0.0.1', 'Test Agent')
        
        if session_id:
            print(f"✅ Session created: {session_id[:8]}...")
            
            # Validate session
            valid, session_info = auth_manager.validate_session(session_id)
            
            if valid:
                print("✅ Session validation successful")
                print(f"   Username: {session_info.get('username', 'N/A')}")
                print(f"   Auth Method: {session_info.get('auth_method', 'N/A')}")
                
                # Invalidate session
                if auth_manager.invalidate_session(session_id):
                    print("✅ Session invalidation successful")
                    
                    # Try to validate again (should fail)
                    valid, _ = auth_manager.validate_session(session_id)
                    if not valid:
                        print("✅ Session properly invalidated")
                        return True
                    else:
                        print("❌ Session still valid after invalidation")
                        return False
                else:
                    print("❌ Session invalidation failed")
                    return False
            else:
                print("❌ Session validation failed")
                return False
        else:
            print("❌ Session creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Session management test failed: {e}")
        return False

def test_ldap_fallback():
    """Test LDAP with local fallback"""
    print("\n🧪 Testing LDAP with Local Fallback...")
    
    try:
        from core.auth_manager import get_auth_manager
        
        auth_manager = get_auth_manager()
        
        # Try LDAP user (should work if LDAP is available)
        success, user_info, method = auth_manager.authenticate('tesla', 'password')
        
        if success:
            print(f"✅ LDAP authentication successful")
            print(f"   Method: {method}")
            print(f"   User: {user_info.get('username', 'N/A')}")
            
        # Try local user (should work as fallback)
        success, user_info, method = auth_manager.authenticate('admin', 'admin123')
        
        if success and method == 'local':
            print(f"✅ Local fallback authentication successful")
            return True
        else:
            print(f"❌ Local fallback authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ LDAP fallback test failed: {e}")
        return False

def test_auth_statistics():
    """Test authentication statistics"""
    print("\n🧪 Testing Authentication Statistics...")
    
    try:
        from core.auth_manager import get_auth_manager
        
        auth_manager = get_auth_manager()
        
        # Get statistics
        stats = auth_manager.get_auth_statistics()
        
        print("✅ Auth statistics retrieved:")
        print(f"   Daily attempts: {stats.get('daily_attempts', {}).get('total', 0)}")
        print(f"   Successful today: {stats.get('daily_attempts', {}).get('successful', 0)}")
        print(f"   Active sessions: {stats.get('active_sessions', 0)}")
        print(f"   Local users: {stats.get('local_users', 0)}")
        print(f"   LDAP users: {stats.get('ldap_users', 0)}")
        
        return True
            
    except Exception as e:
        print(f"❌ Auth statistics test failed: {e}")
        return False

def test_failed_auth_lockout():
    """Test failed authentication lockout"""
    print("\n🧪 Testing Failed Authentication Lockout...")
    
    try:
        from core.auth_manager import get_auth_manager
        
        auth_manager = get_auth_manager()
        
        # Create test user for lockout testing
        auth_manager.create_local_user('locktest', 'TestPass123', role='user')
        
        # Try multiple failed attempts
        for i in range(6):  # More than max_failed_attempts (5)
            success, _, _ = auth_manager.authenticate('locktest', 'wrongpassword')
            if not success:
                print(f"   Failed attempt {i+1}")
        
        # Try correct password (should be locked now)
        success, _, method = auth_manager.authenticate('locktest', 'TestPass123')
        
        if not success or method == 'locked':
            print("✅ Account properly locked after failed attempts")
            return True
        else:
            print("❌ Account not locked after failed attempts")
            return False
            
    except Exception as e:
        print(f"❌ Failed auth lockout test failed: {e}")
        return False

def main():
    """Run all authentication tests"""
    print("🚀 MultiDBManager Authentication Test Suite")
    print("=" * 50)
    
    tests = [
        ("Auth Manager Import", test_auth_manager_import),
        ("Local Authentication", test_local_authentication),
        ("Local User Creation", test_create_local_user),
        ("Session Management", test_session_management),
        ("LDAP with Fallback", test_ldap_fallback),
        ("Auth Statistics", test_auth_statistics),
        ("Failed Auth Lockout", test_failed_auth_lockout),
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
        print("🎉 All authentication tests passed!")
        return 0
    else:
        print("⚠️ Some authentication tests failed.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)