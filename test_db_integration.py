#!/usr/bin/env python3
"""
Simple test to verify SQLite integration works
"""

def test_database_integration():
    """Test database connectivity and basic operations"""
    print("🧪 Testing SQLite Database Integration...")
    
    try:
        # Test database manager
        from database.database_manager import DatabaseManager
        db = DatabaseManager()
        print("✅ Database manager initialized successfully")
        
        # Test statistics
        stats = db.get_statistics()
        print(f"📊 Database Statistics:")
        print(f"   - Servers: {stats['servers']['total']}")
        print(f"   - Users: {stats['users']['total']}")
        print(f"   - Global Users: {stats['global_users']['unique_users']}")
        
        # Test global user manager
        from ui.open_dashboard import GlobalUserManager
        global_mgr = GlobalUserManager()
        print("✅ Global User Manager initialized successfully")
        
        # Test getting users (should work even if empty)
        users = global_mgr.get_all_users_from_all_databases()
        print(f"👥 Found {len(users)} global users")
        
        print("🎉 All tests passed! SQLite integration is working.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_integration()
    exit(0 if success else 1)