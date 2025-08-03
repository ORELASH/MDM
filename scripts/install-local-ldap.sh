#!/bin/bash

# סקריפט התקנת OpenLDAP מקומי לבדיקות
echo "🔧 התקנת OpenLDAP מקומי לבדיקות..."

# בדיקת הרשאות
if [ "$EUID" -ne 0 ]; then 
    echo "❌ נדרשות הרשאות root. הפעל עם sudo"
    exit 1
fi

# עדכון חבילות
echo "📦 עדכון חבילות..."
apt update

# התקנת OpenLDAP
echo "🔧 מתקין OpenLDAP..."
DEBIAN_FRONTEND=noninteractive apt install -y slapd ldap-utils

# הגדרה בסיסית
echo "⚙️ מגדיר OpenLDAP..."

# יצירת קובץ הגדרות
cat > /tmp/ldap-config.ldif << EOF
dn: olcDatabase={1}mdb,cn=config
changetype: modify
replace: olcSuffix
olcSuffix: dc=multidb,dc=local

dn: olcDatabase={1}mdb,cn=config
changetype: modify
replace: olcRootDN
olcRootDN: cn=admin,dc=multidb,dc=local

dn: olcDatabase={1}mdb,cn=config
changetype: modify
replace: olcRootPW
olcRootPW: {SSHA}$(slappasswd -s admin123)
EOF

# החלת הגדרות
ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/ldap-config.ldif

# יצירת מבנה בסיסי
cat > /tmp/base-structure.ldif << EOF
dn: dc=multidb,dc=local
objectClass: top
objectClass: dcObject
objectClass: organization
o: MultiDB Test Organization
dc: multidb

dn: ou=people,dc=multidb,dc=local
objectClass: organizationalUnit
ou: people

dn: ou=groups,dc=multidb,dc=local
objectClass: organizationalUnit
ou: groups
EOF

# טעינת מבנה בסיסי
ldapadd -x -D "cn=admin,dc=multidb,dc=local" -w admin123 -f /tmp/base-structure.ldif

# יצירת משתמשי בדיקה
cat > /tmp/test-users.ldif << EOF
dn: cn=testuser1,ou=people,dc=multidb,dc=local
objectClass: inetOrgPerson
objectClass: posixAccount
cn: testuser1
sn: User1
givenName: Test
displayName: Test User 1
uid: testuser1
mail: testuser1@multidb.local
userPassword: {SSHA}$(slappasswd -s password123)
uidNumber: 1001
gidNumber: 1001
homeDirectory: /home/testuser1

dn: cn=testuser2,ou=people,dc=multidb,dc=local
objectClass: inetOrgPerson
objectClass: posixAccount
cn: testuser2
sn: User2
givenName: Test
displayName: Test User 2
uid: testuser2
mail: testuser2@multidb.local
userPassword: {SSHA}$(slappasswd -s password123)
uidNumber: 1002
gidNumber: 1002
homeDirectory: /home/testuser2

dn: cn=admin_user,ou=people,dc=multidb,dc=local
objectClass: inetOrgPerson
objectClass: posixAccount
cn: admin_user
sn: Admin
givenName: Admin
displayName: Admin User
uid: admin_user
mail: admin@multidb.local
userPassword: {SSHA}$(slappasswd -s admin123)
uidNumber: 1000
gidNumber: 1000
homeDirectory: /home/admin_user
EOF

# טעינת משתמשים
ldapadd -x -D "cn=admin,dc=multidb,dc=local" -w admin123 -f /tmp/test-users.ldif

# יצירת קבוצות
cat > /tmp/test-groups.ldif << EOF
dn: cn=db_admins,ou=groups,dc=multidb,dc=local
objectClass: groupOfNames
cn: db_admins
description: Database Administrators
member: cn=admin_user,ou=people,dc=multidb,dc=local

dn: cn=db_users,ou=groups,dc=multidb,dc=local
objectClass: groupOfNames
cn: db_users
description: Database Users
member: cn=testuser1,ou=people,dc=multidb,dc=local
member: cn=testuser2,ou=people,dc=multidb,dc=local

dn: cn=analysts,ou=groups,dc=multidb,dc=local
objectClass: groupOfNames
cn: analysts
description: Data Analysts
member: cn=testuser1,ou=people,dc=multidb,dc=local
EOF

# טעינת קבוצות
ldapadd -x -D "cn=admin,dc=multidb,dc=local" -w admin123 -f /tmp/test-groups.ldif

# ניקוי קבצים זמניים
rm -f /tmp/ldap-config.ldif /tmp/base-structure.ldif /tmp/test-users.ldif /tmp/test-groups.ldif

echo "✅ התקנת OpenLDAP הושלמה!"
echo ""
echo "📋 פרטי חיבור:"
echo "   שרת: localhost:389"
echo "   Base DN: dc=multidb,dc=local"
echo "   Admin DN: cn=admin,dc=multidb,dc=local"
echo "   סיסמת Admin: admin123"
echo ""
echo "👥 משתמשי בדיקה:"
echo "   testuser1 / password123"
echo "   testuser2 / password123"
echo "   admin_user / admin123"
echo ""
echo "🧪 בדיקת חיבור:"
echo "   ldapsearch -x -H ldap://localhost:389 -b 'dc=multidb,dc=local'"
echo ""
echo "🔧 עצירה/הפעלה:"
echo "   sudo systemctl stop slapd"
echo "   sudo systemctl start slapd"