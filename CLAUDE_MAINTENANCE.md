# 🔧 CLAUDE - מידע לתחזוקה מהירה
**מדריך מהיר למתן מידע לקלוד עבור תחזוקת המערכת**

---

## 📊 סטטוס מערכת נוכחי

### ✅ מערכת פעילה
- **גרסה**: RedshiftManager v1.0.0-beta (build 20240727001)
- **סביבה**: Development / Debug mode מופעל  
- **מצב תחזוקה**: לא פעיל
- **ארכיטקטורה**: Streamlit UI + FastAPI + SQLite + Modular Core

### 📈 נתוני פעילות
- **לוגים כוללים**: ~588 רשומות בקבצים שונים
- **שגיאות מתועדות**: 274 (רובן מבדיקות)
- **בסיס נתונים**: SQLite ב-`data/redshift_manager.db`
- **גיבויים אוטומטיים**: מופעלים (כל 24 שעות)

---

## 🏗️ ארכיטקטורת המערכת

### נקודות כניסה
```bash
# הפעלה ראשית
python main.py              # נקודת כניסה עם בדיקות
python dashboard.py         # כניסה ישירה לדשבורד
./run.sh                   # Linux/Mac
run.bat                    # Windows

# API ושירותים
python api/main.py         # FastAPI server
python utilities/monitor_system.py  # ניטור
```

### מבנה תיקיות קריטי
```
RedshiftManager/
├── ui/open_dashboard.py    # ממשק ראשי
├── core/                   # מערכות ליבה
│   ├── logging_system.py   # לוגים מרכזיים  
│   ├── security_manager.py # אבטחה
│   └── modular_core.py     # מודולים
├── data/                   # בסיסי נתונים
├── logs/                   # לוגי מערכת
├── config/                 # הגדרות
└── backup/                 # גיבויים
```

---

## ⚙️ הגדרות קריטיות

### בסיס נתונים
- **סוגים נתמכים**: SQLite (default) / PostgreSQL / MySQL
- **SQLite מיקום**: `./data/redshift_manager.db`
- **PostgreSQL**: localhost:5432/redshift_manager
- **MySQL**: localhost:3306/redshift_manager
- **הצפנה**: מופעלת
- **גיבוי**: אוטומטי כל 24 שעות

### אבטחה
- **סיסמאות**: מינימום 12 תווים, מדיניות חזקה
- **הפעלות**: 3600 שניות timeout
- **ניסיונות כניסה**: מקסימום 5, נעילה 15 דקות
- **הצפנה**: AES-256-GCM עם rotiation כל 90 יום

### ביצועים
- **Connection Pool**: 10 חיבורים, עד 20 overflow
- **Query Timeout**: 300 שניות (5 דקות)
- **Cache**: מופעל, TTL 300 שניות
- **Logging Level**: INFO

---

## 📋 בעיות נפוצות ופתרונות

### 🔴 בעיות חיבור
```bash
# בדיקת חיבור Redshift
python utilities/api_test.py

# בדיקת הגדרות
cat config/app_settings.json | jq '.redshift'
```

### 🔴 בעיות ביצועים
```bash
# ניטור זיכרון ו-CPU
python utilities/monitor_system.py

# בחינת לוגי ביצועים
tail -f logs/performance_*.log
```

### 🔴 שגיאות אפליקציה
```bash
# לוגים אחרונים
tail -20 logs/errors.log

# לוגים מפורטים
tail -f logs/redshift_manager.log
```

### 🔴 בעיות בבסיס נתונים

#### SQLite:
```bash
# גיבוי לפני תיקון
cp data/redshift_manager.db backup/manual_backup_$(date +%Y%m%d_%H%M%S).db

# בדיקת שלמות
sqlite3 data/redshift_manager.db "PRAGMA integrity_check;"
```

#### PostgreSQL:
```bash
# בדיקת חיבור PostgreSQL
python utilities/postgres_helper.py

# גיבוי PostgreSQL
pg_dump -h localhost -U postgres redshift_manager > backup/postgres_backup_$(date +%Y%m%d_%H%M%S).sql

# שחזור PostgreSQL
psql -h localhost -U postgres redshift_manager < backup/postgres_backup_YYYYMMDD_HHMMSS.sql
```

#### MySQL:
```bash
# בדיקת חיבור MySQL
python utilities/mysql_helper.py

# גיבוי MySQL
mysqldump -u root -p redshift_manager > backup/mysql_backup_$(date +%Y%m%d_%H%M%S).sql

# שחזור MySQL
mysql -u root -p redshift_manager < backup/mysql_backup_YYYYMMDD_HHMMSS.sql

# אופטימיזציה
mysql -u root -p redshift_manager -e "OPTIMIZE TABLE table_name;"
```

---

## 🔍 פקודות אבחון מהירות

### בדיקת סטטוס מערכת
```bash
# בדיקת תהליכים
ps aux | grep -E "(streamlit|python.*main|python.*dashboard)"

# בדיקת פורטים
netstat -tlnp | grep -E "(8501|8000)"

# בדיקת שימוש בדיסק
du -sh data/ logs/ backup/
```

### בדיקת לוגים
```bash
# שגיאות אחרונות
grep -i error logs/errors.log | tail -10

# פעילות אחרונה  
tail -20 logs/main_$(date +%Y%m%d).log

# ספירת שגיאות לפי סוג
grep -c "ERROR\|WARNING\|CRITICAL" logs/*.log
```

### בדיקת תלויות
```bash
# בדיקת Python packages
pip list | grep -E "(streamlit|fastapi|sqlalchemy|pandas)"

# בדיקת requirements
pip check

# גרסת Python
python --version
```

---

## 📞 מידע לטיפול חירום

### קבצי הגדרות קריטיים
- `config/app_settings.json` - הגדרות ראשיות
- `config/system.json` - הגדרות מערכת בסיסיות  
- `data/redshift_manager.db` - בסיס נתונים ראשי
- `requirements.txt` - תלויות Python

### נתיבי גיבוי
- `backup/` - גיבויים אוטומטיים
- `exports/` - ייצואים ידניים
- `archive_old_files/` - קבצים ישנים

### כלי אבחון
- `utilities/monitor_system.py` - ניטור מערכת
- `utilities/live_monitor.py` - ניטור חי
- `utilities/postgres_helper.py` - כלים PostgreSQL
- `utilities/mysql_helper.py` - כלים MySQL
- `tests/test_logging_system.py` - בדיקת מערכת לוגים

---

## 💡 טיפים למתן מידע לקלוד

### ✅ מידע שכדאי לתת מיד
1. **איזה שגיאה?** - הודעת שגיאה מדויקת
2. **מתי קרה?** - זמן האירוע
3. **מה ניסית לעשות?** - הפעולה שגרמה לבעיה
4. **סביבה?** - פיתוח/פרודקשן, מערכת הפעלה
5. **לוגים רלוונטיים** - העתק מהקובץ המתאים

### ⚡ פקודות למידע מהיר
```bash
# העתק למסך - סטטוס מערכת
echo "=== System Status ===" && \
python --version && \
ps aux | grep -E "(streamlit|python.*main)" && \
ls -la logs/ | head -5

# העתק למסך - שגיאות אחרונות  
echo "=== Recent Errors ===" && \
tail -10 logs/errors.log

# העתק למסך - הגדרות חיבור
echo "=== Connection Config ===" && \
cat config/system.json | jq '.database, .redshift // empty'

# בדיקת PostgreSQL אם מוגדר
echo "=== PostgreSQL Test ===" && \
python utilities/postgres_helper.py

# בדיקת MySQL אם מוגדר
echo "=== MySQL Test ===" && \
python utilities/mysql_helper.py
```

### 📋 תבנית דיווח תקלה
```
🔴 **בעיה**: [תיאור קצר]
⏰ **זמן**: [DD/MM/YYYY HH:MM]  
🖥️ **פעולה**: [מה ניסית לעשות]
📊 **סביבה**: [Development/Production]
📝 **שגיאה**:
```
[הודעת שגיאה או לוג רלוונטי]
```

---

## 🎯 דגשים לקלוד

### מה לא לשכוח
- ✅ תמיד בדוק לוגים לפני תיקונים
- ✅ גבה קבצים קריטיים לפני שינויים  
- ✅ השתמש ב-utilities/ לאבחון
- ✅ עדכן CLAUDE_MAINTENANCE.md אחרי תיקונים

### נתיבים חשובים לזכור
- **Config**: `config/app_settings.json`
- **Logs**: `logs/errors.log`, `logs/redshift_manager.log`
- **DB**: `data/redshift_manager.db`
- **Main UI**: `ui/open_dashboard.py`
- **Core**: `core/logging_system.py`

---

**📅 נוצר**: $(date)  
**🔄 עדכון אחרון**: [יעודכן לאחר כל תיקון]