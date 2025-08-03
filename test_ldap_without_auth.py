#!/usr/bin/env python3
"""
בדיקת LDAP ללא authentication
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_anonymous_ldap():
    """בדיקת LDAP ללא אימות"""
    print("🔍 בדיקת LDAP ללא אימות...")
    
    try:
        from ldap3 import Server, Connection, ALL, SUBTREE
        
        # יצירת חיבור לשרת מקומי
        server = Server('localhost', port=389, get_info=ALL)
        
        # חיבור אנונימי
        conn = Connection(server, auto_bind=True)
        
        print(f"✅ חיבור אנונימי הצליח")
        print(f"📊 מידע על השרת:")
        print(f"   Schema: {len(server.schema.object_classes) if server.schema else 0} object classes")
        print(f"   Naming contexts: {server.info.naming_contexts if server.info else 'N/A'}")
        
        # חיפוש בסיסי
        if server.info and server.info.naming_contexts:
            for context in server.info.naming_contexts:
                print(f"\n🔍 בודק naming context: {context}")
                
                # חיפוש ברמה הראשונה
                conn.search(
                    search_base=str(context),
                    search_filter='(objectClass=*)',
                    search_scope=SUBTREE,
                    attributes=['*']
                )
                
                print(f"   רשומות נמצאו: {len(conn.entries)}")
                
                for entry in conn.entries[:5]:  # רק 5 ראשונות
                    print(f"   - {entry.entry_dn}")
        
        conn.unbind()
        return True
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False

def find_working_admin():
    """מחפש admin שעובד"""
    print("\n🔍 מחפש admin credentials שעובדים...")
    
    try:
        from ldap3 import Server, Connection, ALL
        
        server = Server('localhost', port=389)
        
        # רשימת אפשרויות
        test_configs = [
            # בלי סיסמה
            {'user': None, 'password': None, 'name': 'Anonymous'},
            # עם DN שונים וסיסמאות שונות
            {'user': 'cn=admin,dc=multidb,dc=local', 'password': '', 'name': 'Empty password'},
            {'user': 'cn=admin,dc=multidb,dc=local', 'password': 'admin', 'name': 'admin/admin'},
            {'user': 'cn=admin,dc=multidb,dc=local', 'password': 'admin123', 'name': 'admin/admin123'},
            {'user': 'cn=admin,dc=multidb,dc=local', 'password': 'secret', 'name': 'admin/secret'},
            {'user': 'cn=Manager,dc=multidb,dc=local', 'password': 'secret', 'name': 'Manager/secret'},
            {'user': 'cn=admin,cn=config', 'password': 'admin', 'name': 'config admin'},
        ]
        
        for config in test_configs:
            try:
                print(f"🧪 מנסה: {config['name']}")
                
                if config['user'] is None:
                    conn = Connection(server, auto_bind=True)
                else:
                    conn = Connection(
                        server,
                        user=config['user'],
                        password=config['password'],
                        auto_bind=True
                    )
                
                # ניסיון חיפוש
                conn.search(
                    search_base='dc=multidb,dc=local',
                    search_filter='(objectClass=*)',
                    search_scope=SUBTREE
                )
                
                print(f"   ✅ עבד! נמצאו {len(conn.entries)} רשומות")
                print(f"   📋 Credentials: {config['user']} / {config['password']}")
                
                # הצגת רשומות שנמצאו
                for entry in conn.entries[:3]:
                    print(f"      - {entry.entry_dn}")
                
                conn.unbind()
                return config
                
            except Exception as e:
                print(f"   ❌ לא עבד: {e}")
                continue
        
        print("❌ לא נמצא admin שעובד")
        return None
        
    except Exception as e:
        print(f"❌ שגיאה כללית: {e}")
        return None

if __name__ == "__main__":
    test_anonymous_ldap()
    print()
    working_config = find_working_admin()
    
    if working_config:
        print(f"\n🎯 מצאתי תצורה שעובדת!")
        print(f"   User: {working_config['user']}")
        print(f"   Password: {working_config['password']}")
        print(f"\n📝 עדכון ל-MultiDBManager:")
        print(f"   עדכן את TEST_CONFIGS['local_system'] עם הפרטים האלה")
    else:
        print(f"\n⚠️ לא מצאתי תצורה שעובדת")
        print(f"💡 אפשרויות:")
        print(f"   1. המשך עם ForumSys (עובד מצוין)")
        print(f"   2. נסה לאפס LDAP עם sudo")
        print(f"   3. התקן LDAP מחדש")