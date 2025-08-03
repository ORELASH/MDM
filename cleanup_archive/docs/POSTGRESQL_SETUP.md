# 🐘 PostgreSQL Setup Guide - RedshiftManager

מדריך התקנה ומעבר מ-SQLite ל-PostgreSQL

---

## 📋 דרישות מוקדמות

### 1. התקנת PostgreSQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb

# macOS (Homebrew)
brew install postgresql
brew services start postgresql

# Windows
# הורד והתקן מ: https://www.postgresql.org/download/windows/
```

### 2. התקנת Python dependencies
```bash
pip install psycopg2-binary asyncpg
```

---

## ⚙️ הגדרת PostgreSQL

### 1. יצירת משתמש ובסיס נתונים
```bash
# התחבר כ-postgres user
sudo -u postgres psql

# צור משתמש חדש
CREATE USER redshift_manager WITH PASSWORD 'your_secure_password';

# צור בסיס נתונים
CREATE DATABASE redshift_manager OWNER redshift_manager;

# תן הרשאות
GRANT ALL PRIVILEGES ON DATABASE redshift_manager TO redshift_manager;

# יציאה
\q
```

### 2. בדיקת חיבור
```bash
# בדוק שהחיבור עובד
psql -h localhost -U redshift_manager -d redshift_manager

# או השתמש בכלי העזר שלנו
python utilities/postgres_helper.py
```

---

## 🔧 עדכון קונפיגורציה

### 1. עדכן `config/system.json`:
```json
{
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "username": "redshift_manager",
    "password": "your_secure_password",
    "database": "redshift_manager"
  }
}
```

### 2. עדכן `config/app_settings.json`:
```json
{
  "database": {
    "primary": {
      "type": "postgresql"
    },
    "postgresql": {
      "host": "localhost",
      "port": 5432,
      "database": "redshift_manager",
      "username": "redshift_manager",
      "password": "your_secure_password",
      "ssl_mode": "prefer",
      "connect_timeout": 30,
      "application_name": "RedshiftManager"
    }
  }
}
```

---

## 📦 מעבר נתונים מ-SQLite

### 1. גיבוי SQLite נוכחי
```bash
# צור גיבוי של SQLite
cp data/redshift_manager.db backup/sqlite_backup_$(date +%Y%m%d_%H%M%S).db
```

### 2. ייצוא נתונים מ-SQLite
```bash
# ייצא נתונים ל-SQL
sqlite3 data/redshift_manager.db .dump > backup/sqlite_export.sql
```

### 3. התאמת SQL ל-PostgreSQL
```bash
# עריכה ידנית של קובץ SQL:
# - החלף 'INTEGER PRIMARY KEY AUTOINCREMENT' ב-'SERIAL PRIMARY KEY'
# - החלף 'TEXT' ב-'VARCHAR' או 'TEXT' לפי הצורך
# - הסר פקודות SQLite-specific כמו PRAGMA
```

### 4. יבוא ל-PostgreSQL
```bash
# צור טבלאות חדשות
python -c "
from models.database_models import DatabaseManager
db = DatabaseManager()
db.create_all_tables()
"

# או יבא נתונים מותאמים
psql -h localhost -U redshift_manager -d redshift_manager < backup/sqlite_export_adapted.sql
```

---

## 🔍 בדיקות ואימות

### 1. בדיקת חיבור
```bash
python utilities/postgres_helper.py
```

### 2. בדיקת טבלאות
```bash
psql -h localhost -U redshift_manager -d redshift_manager -c "\dt"
```

### 3. בדיקת נתונים
```bash
psql -h localhost -U redshift_manager -d redshift_manager -c "
SELECT table_name, 
       (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns,
       pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
FROM information_schema.tables t
WHERE table_schema = 'public'
ORDER BY table_name;
"
```

### 4. הרצת המערכת
```bash
# הפעל את המערכת
python main.py

# בדוק לוגים לשגיאות
tail -f logs/errors.log
```

---

## 🎯 בדיקות ביצועים

### 1. השוואת ביצועים
```bash
# בדוק זמני תגובה
python -c "
import time
from models.database_models import DatabaseManager

start = time.time()
db = DatabaseManager()
session = db.Session()
# בצע שאילתת בדיקה
result = session.execute('SELECT count(*) FROM users')
print(f'Query time: {time.time() - start:.3f}s')
"
```

### 2. ניטור חיבורים
```bash
# בדוק חיבורים פעילים
psql -h localhost -U redshift_manager -d redshift_manager -c "
SELECT pid, usename, application_name, client_addr, state, query_start 
FROM pg_stat_activity 
WHERE datname = 'redshift_manager';
"
```

---

## 🔒 אבטחה ואופטימיזציה

### 1. הגדרות אבטחה PostgreSQL
```bash
# ערוך postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf

# הגדרות מומלצות:
# listen_addresses = 'localhost'
# max_connections = 100
# shared_buffers = 256MB
# effective_cache_size = 1GB
```

### 2. הגדרות pg_hba.conf
```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf

# הוסף שורה:
# local   redshift_manager    redshift_manager                    md5
# host    redshift_manager    redshift_manager    127.0.0.1/32    md5
```

### 3. אתחול PostgreSQL
```bash
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

---

## 🚨 פתרון בעיות נפוצות

### בעיית חיבור
```bash
# בדוק שהשירות פועל
sudo systemctl status postgresql

# בדוק פורטים
netstat -tlnp | grep 5432

# בדוק לוגי PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

### בעיית הרשאות
```bash
# תן הרשאות מלאות למשתמש
sudo -u postgres psql -c "ALTER USER redshift_manager CREATEDB;"
```

### בעיית encoding
```bash
# צור DB עם UTF8
sudo -u postgres createdb -E UTF8 -O redshift_manager redshift_manager
```

---

## 📊 ניטור ותחזוקה

### 1. גיבויים אוטומטיים
```bash
# הוסף ל-crontab
crontab -e

# גיבוי יומי ב-2:00 לילה
0 2 * * * pg_dump -h localhost -U redshift_manager redshift_manager > /path/to/backup/daily_$(date +\%Y\%m\%d).sql
```

### 2. ניקוי תקופתי
```bash
# בצע VACUUM ANALYZE שבועי
0 3 * * 0 psql -h localhost -U redshift_manager -d redshift_manager -c "VACUUM ANALYZE;"
```

### 3. ניטור ביצועים
```bash
# התקן pg_stat_statements
sudo -u postgres psql -d redshift_manager -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
```

---

## ✅ סיכום

לאחר המעבר ל-PostgreSQL:

1. ✅ **ביצועים משופרים** - חיבורים מקבילים וטיפול טוב יותר בעומסים
2. ✅ **אבטחה מתקדמת** - הרשאות מפורטות ו-SSL support  
3. ✅ **גמישות** - תמיכה ב-JSON, arrays וסוגי נתונים מתקדמים
4. ✅ **מוכנות לפרודקשן** - אמינות גבוהה ותמיכה enterprise
5. ✅ **ניטור משופר** - כלי ניטור מובנים

**המערכת עכשיו מוכנה לסביבת פרודקשן עם PostgreSQL! 🎉**

---

**📅 נוצר**: $(date)  
**🔄 עדכון אחרון**: [יעודכן לאחר התקנה]