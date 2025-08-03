# 🔗 מדריך הקמת LDAP לבדיקות

## 1. 🌐 שרת LDAP ציבורי (ForumSys) - מומלץ

### פרטי החיבור:
```
שרת: ldap.forumsys.com
פורט: 389
Base DN: dc=example,dc=com
Admin DN: cn=read-only-admin,dc=example,dc=com
סיסמה: password
```

### משתמשי בדיקה:
- **tesla** / password
- **einstein** / password  
- **newton** / password
- **curie** / password
- **bohr** / password

### קבוצות:
- mathematicians
- scientists

### בדיקת חיבור:
```bash
python3 test_ldap_integration.py
```

---

## 2. 🐳 LDAP מקומי עם Docker

### דרישות:
- Docker מותקן
- הרשאות Docker (usermod -aG docker $USER)

### הפעלה:
```bash
# הפעלת שרת LDAP
docker run -d \
  --name test-ldap \
  -p 389:389 \
  -p 636:636 \
  -e LDAP_ORGANISATION="MultiDB Test" \
  -e LDAP_DOMAIN="multidb.local" \
  -e LDAP_ADMIN_PASSWORD="admin123" \
  osixia/openldap:1.5.0

# הפעלת ממשק ניהול web
docker run -d \
  --name ldap-admin \
  -p 8080:80 \
  --link test-ldap:ldap-host \
  -e PHPLDAPADMIN_LDAP_HOSTS=ldap-host \
  osixia/phpldapadmin:0.9.0
```

### פרטי חיבור:
```
שרת: localhost:389
Base DN: dc=multidb,dc=local
Admin DN: cn=admin,dc=multidb,dc=local
סיסמה: admin123
Web Admin: http://localhost:8080
```

---

## 3. 🛠️ התקנה מקומית (Ubuntu/Debian)

### התקנת OpenLDAP:
```bash
sudo apt update
sudo apt install slapd ldap-utils

# הגדרה
sudo dpkg-reconfigure slapd
```

### הגדרת משתמשי בדיקה:
```bash
# יצירת קובץ LDIF
cat > test-users.ldif << EOF
dn: ou=people,dc=multidb,dc=local
objectClass: organizationalUnit
ou: people

dn: cn=testuser,ou=people,dc=multidb,dc=local
objectClass: inetOrgPerson
cn: testuser
sn: User
givenName: Test
mail: test@multidb.local
userPassword: {SSHA}dGVzdDEyMw==
EOF

# טעינת נתונים
ldapadd -x -D "cn=admin,dc=multidb,dc=local" -W -f test-users.ldif
```

---

## 4. ☁️ שירותי ענן

### AWS Directory Service:
- 30 יום ניסיון חינם
- Simple AD או Managed Microsoft AD

### Azure AD Domain Services:
- קרדיט ניסיון
- אינטגרציה עם Azure AD

### Google Cloud Identity:
- חבילת Free tier
- עד 50 משתמשים

---

## 🧪 בדיקת התקנה

### 1. בדיקת חיבור בסיסי:
```bash
ldapsearch -x -H ldap://localhost:389 -b "dc=multidb,dc=local"
```

### 2. בדיקה עם MultiDBManager:
```bash
python3 test_ldap_integration.py
```

### 3. בדיקת אימות:
```bash
python3 test_auth_manager.py
```

---

## ⚙️ קונפיגורציה ב-MultiDBManager

### עדכון הגדרות LDAP:
```python
# ב-core/ldap_integration.py
TEST_CONFIGS = {
    'local': {
        'server': 'localhost',
        'port': 389,
        'base_dn': 'dc=multidb,dc=local',
        'bind_dn': 'cn=admin,dc=multidb,dc=local',
        'bind_password': 'admin123'
    }
}
```

### בדיקה דרך הממשק:
1. פתח את MultiDBManager
2. עבור ל"🔗 LDAP Sync"
3. בחר "Configuration"
4. הוסף שרת חדש

---

## 🔍 פתרון בעיות נפוצות

### שגיאת חיבור:
```bash
# בדוק שהשרת רץ
docker ps | grep ldap
netstat -ln | grep 389
```

### בעיות הרשאות:
```bash
# הוסף משתמש לקבוצת docker
sudo usermod -aG docker $USER
# התנתק והתחבר מחדש
```

### בעיות SSL:
```bash
# השבת SSL לבדיקות
use_ssl: False
```

---

## 📋 רשימת ביקורת

- [ ] שרת LDAP פועל על פורט 389
- [ ] חיבור בסיסי עובד (ldapsearch)
- [ ] משתמשי בדיקה נוצרו
- [ ] MultiDBManager מתחבר בהצלחה
- [ ] אימות משתמשים עובד
- [ ] סינכרון נתונים פועל

---

## 🎯 המלצות

**לפיתוח מקומי:** השתמש בשרת ForumSys הציבורי
**לבדיקות CI/CD:** Docker container
**לפרודקשן:** שירות ענן מנוהל או התקנה מקומית מאובטחת