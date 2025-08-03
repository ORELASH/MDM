#!/usr/bin/env python3
"""
בדיקת LDAP מקומי
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_local_ldap():
    """בדיקת השרת המקומי"""
    print("🧪 בדיקת LDAP מקומי...")
    
    try:
        from core.ldap_integration import LDAPManager, TEST_CONFIGS
        
        # בדיקת כל התצורות המקומיות
        configs_to_test = ['local_docker', 'local_system']
        
        for config_name in configs_to_test:
            print(f"\n🔧 בודק תצורה: {config_name}")
            
            if config_name not in TEST_CONFIGS:
                print(f"❌ תצורה {config_name} לא נמצאה")
                continue
                
            ldap_manager = LDAPManager(TEST_CONFIGS[config_name])
            
            # בדיקת חיבור
            success, message = ldap_manager.test_connection()
            print(f"   חיבור: {'✅' if success else '❌'} {message}")
            
            if success:
                # בדיקת משתמשים
                users = ldap_manager.get_all_users()
                print(f"   משתמשים נמצאו: {len(users)}")
                
                for user in users[:3]:
                    print(f"   - {user.get('username', 'N/A')}")
                
                # בדיקת אימות אם יש משתמשים
                if users:
                    test_user = users[0]
                    username = test_user.get('username')
                    # ננסה סיסמאות נפוצות
                    passwords_to_try = ['password123', 'admin123', 'password']
                    
                    for password in passwords_to_try:
                        auth_success, user_info = ldap_manager.authenticate_user(username, password)
                        if auth_success:
                            print(f"   ✅ אימות הצליח: {username} / {password}")
                            break
                    else:
                        print(f"   ❌ אימות נכשל לכל הסיסמאות")
            
            print(f"   {'='*30}")
        
        # אם אף תצורה מקומית לא עבדה, בדוק את ForumSys
        print(f"\n🌐 בדיקת ForumSys כגיבוי...")
        ldap_manager = LDAPManager(TEST_CONFIGS['forumsys'])
        success, message = ldap_manager.test_connection()
        print(f"   ForumSys: {'✅' if success else '❌'} {message}")
        
        if success:
            users = ldap_manager.get_all_users()
            print(f"   משתמשים: {len(users)}")
            
            # בדיקת אימות tesla
            auth_success, user_info = ldap_manager.authenticate_user('tesla', 'password')
            if auth_success:
                print(f"   ✅ אימות tesla הצליח")
            else:
                print(f"   ❌ אימות tesla נכשל")
    
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False
    
    return True

def show_ldap_status():
    """הצגת סטטוס LDAP"""
    print("📊 סטטוס מערכות LDAP:")
    print("="*40)
    
    # בדיקת שרתים זמינים
    servers = [
        ("ForumSys (ציבורי)", "ldap.forumsys.com", 389),
        ("מקומי", "localhost", 389)
    ]
    
    for name, host, port in servers:
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ {name}: זמין ({host}:{port})")
            else:
                print(f"❌ {name}: לא זמין ({host}:{port})")
        except Exception as e:
            print(f"❌ {name}: שגיאה - {e}")

if __name__ == "__main__":
    show_ldap_status()
    print()
    test_local_ldap()