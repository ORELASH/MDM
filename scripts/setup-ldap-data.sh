#!/bin/bash

# סקריפט ליצירת נתונים בסיסיים ב-LDAP
echo "🔧 מגדיר נתונים בסיסיים ב-LDAP..."

# בדיקה שה-LDAP רץ
if ! systemctl is-active --quiet slapd; then
    echo "❌ שירות LDAP לא רץ. מפעיל..."
    sudo systemctl start slapd
    sleep 2
fi

# בדיקת admin password הנוכחית
echo "🔍 בודק פרטי admin הנוכחיים..."

# נסיון חיבור עם admin DN שונים
ADMIN_DNS=(
    "cn=admin,dc=multidb,dc=local"
    "cn=admin,cn=config"
    "cn=admin,dc=nodomain"
)

PASSWORDS=(
    "admin123"
    "admin"
    ""
)

WORKING_ADMIN=""
WORKING_PASSWORD=""

for admin_dn in "${ADMIN_DNS[@]}"; do
    for password in "${PASSWORDS[@]}"; do
        echo "🧪 מנסה: $admin_dn עם סיסמה: '${password:-<ריק>}'"
        
        if [ -z "$password" ]; then
            # ללא סיסמה
            if ldapsearch -x -H ldap://localhost:389 -D "$admin_dn" -b "dc=multidb,dc=local" -s base >/dev/null 2>&1; then
                echo "✅ עבד עם: $admin_dn (ללא סיסמה)"
                WORKING_ADMIN="$admin_dn"
                WORKING_PASSWORD=""
                break 2
            fi
        else
            # עם סיסמה
            if ldapsearch -x -H ldap://localhost:389 -D "$admin_dn" -w "$password" -b "dc=multidb,dc=local" -s base >/dev/null 2>&1; then
                echo "✅ עבד עם: $admin_dn / $password"
                WORKING_ADMIN="$admin_dn"
                WORKING_PASSWORD="$password"
                break 2
            fi
        fi
    done
done

if [ -z "$WORKING_ADMIN" ]; then
    echo "❌ לא מצאתי admin שעובד. מנסה לאפס..."
    
    # ניסיון איפוס עם dpkg-reconfigure
    echo "🔄 מאפס הגדרות LDAP..."
    echo -e "multidb.local\nmultidb\nadmin123\nadmin123" | sudo debconf-set-selections << EOF
slapd slapd/internal/generated_adminpw password admin123
slapd slapd/internal/adminpw password admin123
slapd slapd/password2 password admin123
slapd slapd/password1 password admin123
slapd slapd/domain string multidb.local
slapd slapd/organization string MultiDB Test
slapd slapd/purge_database boolean true
slapd slapd/move_old_database boolean true
slapd slapd/allow_ldap_v2 boolean false
slapd slapd/no_configuration boolean false
slapd shared/organization string MultiDB Test
slapd slapd/dump_database_destdir string /var/backups/slapd-VERSION
slapd slapd/dump_database select when needed
EOF

    sudo DEBIAN_FRONTEND=noninteractive dpkg-reconfigure slapd
    
    # המתנה ובדיקה חוזרת
    sleep 3
    WORKING_ADMIN="cn=admin,dc=multidb,dc=local"
    WORKING_PASSWORD="admin123"
    
    if ldapsearch -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -w "$WORKING_PASSWORD" -b "dc=multidb,dc=local" -s base >/dev/null 2>&1; then
        echo "✅ איפוס הצליח!"
    else
        echo "❌ איפוס לא הצליח"
        exit 1
    fi
fi

echo "🎯 פרטי admin שעובדים:"
echo "   DN: $WORKING_ADMIN"
echo "   Password: ${WORKING_PASSWORD:-<ריק>}"

# יצירת מבנה בסיסי
echo "📂 יוצר מבנה בסיסי..."

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
if [ -z "$WORKING_PASSWORD" ]; then
    ldapadd -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -f /tmp/base-structure.ldif 2>/dev/null
else
    ldapadd -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -w "$WORKING_PASSWORD" -f /tmp/base-structure.ldif 2>/dev/null
fi

# יצירת משתמשי בדיקה
echo "👥 יוצר משתמשי בדיקה..."

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
userPassword: password123
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
userPassword: password123
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
userPassword: admin123
uidNumber: 1000
gidNumber: 1000
homeDirectory: /home/admin_user
EOF

# טעינת משתמשים
if [ -z "$WORKING_PASSWORD" ]; then
    ldapadd -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -f /tmp/test-users.ldif 2>/dev/null
else
    ldapadd -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -w "$WORKING_PASSWORD" -f /tmp/test-users.ldif 2>/dev/null
fi

# יצירת קבוצות
echo "🏷️ יוצר קבוצות..."

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
if [ -z "$WORKING_PASSWORD" ]; then
    ldapadd -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -f /tmp/test-groups.ldif 2>/dev/null
else
    ldapadd -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -w "$WORKING_PASSWORD" -f /tmp/test-groups.ldif 2>/dev/null
fi

# ניקוי קבצים זמניים
rm -f /tmp/base-structure.ldif /tmp/test-users.ldif /tmp/test-groups.ldif

# בדיקה סופית
echo "🧪 בדיקה סופית..."
if [ -z "$WORKING_PASSWORD" ]; then
    USER_COUNT=$(ldapsearch -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -b "ou=people,dc=multidb,dc=local" "(objectClass=inetOrgPerson)" | grep -c "^dn:")
else
    USER_COUNT=$(ldapsearch -x -H ldap://localhost:389 -D "$WORKING_ADMIN" -w "$WORKING_PASSWORD" -b "ou=people,dc=multidb,dc=local" "(objectClass=inetOrgPerson)" | grep -c "^dn:")
fi

echo "✅ הגדרת LDAP הושלמה!"
echo ""
echo "📋 פרטי חיבור:"
echo "   שרת: localhost:389"
echo "   Base DN: dc=multidb,dc=local"
echo "   Admin DN: $WORKING_ADMIN"
echo "   Admin Password: ${WORKING_PASSWORD:-<ריק>}"
echo ""
echo "👥 משתמשים נוצרו: $USER_COUNT"
echo "   testuser1 / password123"
echo "   testuser2 / password123"
echo "   admin_user / admin123"
echo ""
echo "🧪 בדיקת חיבור:"
if [ -z "$WORKING_PASSWORD" ]; then
    echo "   ldapsearch -x -H ldap://localhost:389 -D '$WORKING_ADMIN' -b 'dc=multidb,dc=local'"
else
    echo "   ldapsearch -x -H ldap://localhost:389 -D '$WORKING_ADMIN' -w '$WORKING_PASSWORD' -b 'dc=multidb,dc=local'"
fi