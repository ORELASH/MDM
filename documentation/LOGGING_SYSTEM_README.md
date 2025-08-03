# 📋 מערכת לוגים כללית - RedshiftManager

## 🎯 סקירה כללית

מערכת לוגים מתקדמת ומקיפה עבור RedshiftManager הכוללת:
- **Structured Logging** עם JSON format
- **שמירה בבסיס נתונים** SQLite עם indexing
- **ממשק צפייה אינטראקטיבי** עם סינון וחיפוש
- **אנליטיקס מתקדם** לזיהוי דפוסים ותובנות
- **ייצוא וגיבוי** במספר פורמטים
- **התראות** לשגיאות קריטיות (Slack)

---

## 🏗️ ארכיטקטורה

### קבצי המערכת

```
core/
├── logging_system.py    # מערכת הלוגים המרכזית
├── log_analytics.py     # מודול אנליטיקס מתקדם
└── log_export.py        # מודול ייצוא וגיבוי

pages/
└── logs_viewer.py       # ממשק הצפייה בלוגים

logs/                    # תיקיית הלוגים
├── logs.db             # בסיס נתונים SQLite
├── redshift_manager.log # לוג טקסט רגיל
├── redshift_manager.json # לוג JSON מובנה
└── errors.log          # לוג שגיאות בלבד

exports/                 # תיקיית ייצואים וגיבויים
├── logs_export_*.csv
├── logs_export_*.json
└── logs_backup_*.zip
```

### רכיבי המערכת

1. **RedshiftManagerLogger** - מחלקה מרכזית לניהול הלוגים
2. **JSONFormatter** - פורמטר ל-JSON מובנה
3. **DatabaseHandler** - handler לשמירה בבסיס נתונים
4. **SlackHandler** - handler להתראות Slack
5. **LogAnalytics** - מודול אנליטיקס מתקדם
6. **LogExporter** - מודול ייצוא וגיבוי

---

## 🚀 התחלה מהירה

### הפעלת המערכת

```python
from core.logging_system import get_logger, log_user_action, log_operation

# קבלת logger
logger = get_logger("my_module")

# לוגים בסיסיים
logger.info("Application started")
logger.error("Database connection failed")

# לוגים עם context
log_user_action("login", user_id="admin", session_id="sess123")
log_operation("QUERY_EXECUTION", user_id="analyst", duration=1500)
```

### יצירת לוגים לדוגמה

```bash
python test_logging_system.py
```

### צפייה בלוגים

1. **דרך המערכת הראשית**: עמוד "📋 Logs Viewer"
2. **הרצה ישירה**: `streamlit run pages/logs_viewer.py`

---

## 📊 סוגי לוגים

### 1. לוגים כלליים
```python
logger = get_logger("module_name")
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical system error")
```

### 2. לוגי פעולות
```python
log_operation(
    operation="CLUSTER_CONNECT",
    level="INFO",
    user_id="admin",
    cluster_id="prod-cluster",
    duration=2500,  # milliseconds
    status="SUCCESS"
)
```

### 3. לוגי שאילתות
```python
log_query(
    query="SELECT * FROM users",
    cluster_id="prod-cluster", 
    user_id="analyst",
    duration=1200,
    rows_affected=150,
    status="SUCCESS"
)
```

### 4. לוגי פעולות משתמש
```python
log_user_action(
    action="page_view",
    user_id="user123",
    session_id="sess456",
    page="dashboard",
    ip_address="192.168.1.100"
)
```

### 5. לוגי אירועי מערכת
```python
log_system_event(
    event="BACKUP_COMPLETED",
    severity="INFO",
    cluster_id="prod-cluster",
    backup_size="2.5GB"
)
```

---

## 🔍 ממשק הצפייה

### תכונות עיקריות

#### 📊 סטטיסטיקות
- סך כל הלוגים במערכת
- לוגים ב-24 שעות אחרונות
- שגיאות בשבוע האחרון
- אחוז שגיאות
- התפלגות לפי רמות ומודולים

#### 🔍 חיפוש וסינון
- **טווח תאריכים**: בחירת תקופה לניתוח
- **רמת לוג**: סינון לפי DEBUG, INFO, WARNING, ERROR, CRITICAL
- **מודול**: סינון לפי מודול ספציפי
- **חיפוש טקסט**: חיפוש חופשי בתוכן ההודעות
- **מגבלת תוצאות**: הגדרת מספר מקסימלי של תוצאות

#### 📈 Timeline
- גרף זמן של נפח לוגים
- התפלגות לפי רמות לאורך זמן
- זיהוי שעות שיא

#### 📋 טבלת תוצאות
- הצגה טבלאית של הלוגים
- בחירת עמודות להצגה
- פרטים מלאים של לוג נבחר
- Exception details ו-stack traces

#### 💾 ייצוא
- ייצוא ל-CSV, JSON, Excel
- דחיסה אוטומטית של קבצים גדולים

---

## 📈 מערכת אנליטיקס

### ניתוח דפוסי שגיאות

```python
from core.log_analytics import LogAnalytics

analytics = LogAnalytics()
error_analysis = analytics.analyze_error_patterns(days=7)

print(f"סך שגיאות: {error_analysis['total_errors']}")
print(f"שגיאות ייחודיות: {error_analysis['unique_errors']}")
```

#### תכונות האנליטיקס

1. **קטגוריזציה אוטומטית** של שגיאות לפי סוג
2. **זיהוי דפוסים חוזרים** ושגיאות ברצף
3. **ניתוח פרצי שגיאות** (error bursts)
4. **מגמות לאורך זמן** עם חישוב טרנדים

### ניתוח ביצועים

```python
performance_analysis = analytics.analyze_performance_trends(days=7)

print(f"זמן ממוצע: {performance_analysis['avg_duration']:.2f}ms")
print(f"P95: {performance_analysis['p95_duration']:.2f}ms")
```

#### מדדי ביצועים

1. **זמני ביצוע** ממוצעים ו-percentiles
2. **השוואה בין אשכולות** שונים
3. **ניתוח לפי סוג פעולה**
4. **מגמות ביצועים** לאורך זמן

### ניתוח פעילות משתמשים

```python
user_analysis = analytics.analyze_user_activity(days=7)

print(f"משתמשים פעילים: {user_analysis['unique_users']}")
print(f"פעולות: {user_analysis['total_user_actions']}")
```

---

## 💾 מערכת ייצוא וגיבוי

### ייצוא לוגים

```python
from core.log_export import LogExporter

exporter = LogExporter()

# ייצוא JSON עם דחיסה
json_file = exporter.export_logs_json(
    start_date=datetime.now() - timedelta(days=7),
    compress=True
)

# ייצוא Excel עם מספר sheets
xlsx_file = exporter.export_logs_xlsx(
    start_date=datetime.now() - timedelta(days=1)
)
```

### פורמטי ייצוא נתמכים

1. **CSV** - עם אפשרות דחיסה GZIP
2. **JSON** - עם metadata מלא
3. **Excel** - עם מספר sheets וסיכומים

### גיבויים אוטומטיים

```python
# גיבוי מלא של המערכת
full_backup = exporter.create_backup("full")

# גיבוי נתונים מהשבוع האחרון
recent_backup = exporter.create_backup("recent")

# גיבוי בסיס הנתונים בלבד
db_backup = exporter.create_backup("database_only")
```

### ניהול גיבויים

- **דחיסה אוטומטית** ל-ZIP
- **metadata** מלא על הגיבוי
- **שחזור** מגיבוי קיים
- **ניקוי גיבויים ישנים**

---

## ⚙️ הגדרות והתאמה אישית

### קונפיגורציה בסיסית

```python
config = {
    "log_dir": "logs",              # תיקיית לוגים
    "log_level": "INFO",            # רמת לוג מינימלית
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "backup_count": 10,             # מספר קבצי backup
    "database_enabled": True,       # שמירה בבסיס נתונים
    "console_enabled": True,        # הצגה בקונסול
    "json_enabled": True,           # קובץ JSON
    "slack_webhook": None,          # URL ל-Slack
    "retention_days": 30,           # ימים לשמירה
}

logger_system = RedshiftManagerLogger(config)
```

### התראות Slack
```python
config["slack_webhook"] = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

שגיאות ברמת ERROR וCRITICAL יישלחו אוטומטית ל-Slack.

---

## 🛠️ פונקציות עזר

### שליפת לוגים פרוגרמטית

```python
from core.logging_system import logger_system

# שליפת לוגים עם סינון
df = logger_system.get_logs(
    start_date=datetime.now() - timedelta(hours=1),
    level="ERROR",
    user_id="admin",
    limit=100
)

# סטטיסטיקות מערכת
stats = logger_system.get_log_statistics()
```

### ניקוי לוגים ישנים

```python
# ניקוי אוטומטי לפי מדיניות retention
logger_system.cleanup_old_logs()

# ניקוי ייצואים ישנים
from core.log_export import LogExporter
exporter = LogExporter()
cleaned_count = exporter.cleanup_old_exports(days_to_keep=30)
```

---

## 📱 אינטגרציה עם המערכת הקיימת

המערכת משולבת באופן מלא עם RedshiftManager:

### בדשבורד הראשי
```python
from core.logging_system import log_user_action, get_logger

logger = get_logger("dashboard")

def show_dashboard_page():
    log_user_action("page_view", "system", page="dashboard")
    logger.info("Dashboard page accessed")
    # ... קוד הדשבורד
```

### בביצוע שאילתות
```python
from core.logging_system import log_query

def execute_query(query, cluster_id, user_id):
    start_time = time.time()
    try:
        # ביצוע השאילתה
        result = run_query(query)
        
        # לוג הצלחה
        log_query(
            query=query,
            cluster_id=cluster_id,
            user_id=user_id,
            duration=(time.time() - start_time) * 1000,
            rows_affected=len(result),
            status="SUCCESS"
        )
        
    except Exception as e:
        # לוג שגיאה
        logger.error(f"Query failed: {e}", extra={
            "query": query,
            "cluster_id": cluster_id,
            "user_id": user_id
        })
```

---

## 🔧 בעיות נפוצות ופתרונות

### המערכת לא כותבת לוגים
- בדוק שתיקיית `logs/` נוצרה
- בדוק הרשאות כתיבה
- ודא שהמודול מיובא נכון

### בסיס הנתונים נעול
```python
# הוסף timeout לחיבור
conn = sqlite3.connect(self.db_path, timeout=30)
```

### קבצי לוג גדולים מדי
- הגדר `max_file_size` נמוך יותר
- הגבר את `backup_count`
- השתמש בדחיסה

### ביצועים איטיים
- הגדל את `batch_size` בכתיבה לבסיס נתונים
- השתמש באינדקסים נוספים
- הפעל ניקוי לוגים ישנים

---

## 📊 מדדי ביצועים

המערכת מותאמת לטיפול ב:
- **100,000+ לוגים ביום**
- **חיפושים מהירים** עם אינדקסים
- **ייצוא גדול** עד 1GB+
- **גיבויים מהירים** עם דחיסה

---

## 🎯 המלצות לשימוש

### לפיתוח
- השתמש ברמת DEBUG לפרטים מלאים
- הוסף context מלא עם `extra` fields
- בדוק לוגים לאחר כל שינוי

### לייצור
- השתמש ברמת INFO או WARNING
- הפעל ניקוי אוטומטי
- הגדר התראות Slack
- צור גיבויים תקופתיים

### למעקב ותחזוקה
- עקוב אחר מגמות שגיאות
- נתח ביצועים שבועית
- בדוק דפוסי שימוש משתמשים
- יצא דוחות לניתוח חיצוני

---

## 🔮 תוכניות עתידיות

- **ElasticSearch integration** לחיפוש מתקדם
- **Grafana dashboards** לוויזואליזציה
- **Machine Learning** לזיהוי אנומליות
- **Real-time alerts** עם Webhook
- **API endpoints** לגישה חיצונית

---

*מערכת הלוגים נוצרה כחלק מ-RedshiftManager ומספקת פתרון מקיף לניטור, ניתוח וניהול לוגים.*