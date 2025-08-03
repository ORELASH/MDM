#!/usr/bin/env python3
"""
בדיקה ודמו למערכת הלוגים
Testing and demo for the logging system
"""

import random
import time
from datetime import datetime, timedelta

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.logging_system import (
    get_logger,
    log_operation,
    log_query,
    log_system_event,
    log_user_action,
    logger_system,
)


def generate_sample_logs():
    """יצירת לוגים לדוגמה לבדיקת המערכת"""
    print("🚀 יוצר לוגים לדוגמה...")
    
    # רשימת משתמשים לדוגמה
    users = ["admin", "analyst1", "developer", "manager", "guest"]
    
    # רשימת אשכולות לדוגמה
    clusters = ["production-cluster", "staging-cluster", "dev-cluster", "analytics-cluster"]
    
    # רשימת פעולות לדוגמה
    operations = ["QUERY_EXECUTION", "USER_LOGIN", "CLUSTER_CONNECT", "DATA_EXPORT", "BACKUP_CREATE"]
    
    # יצירת לוגים רגילים
    for i in range(50):
        user_id = random.choice(users)
        cluster_id = random.choice(clusters)
        operation = random.choice(operations)
        
        # לוג פעולת משתמש
        log_user_action(
            action=f"performed_{operation.lower()}",
            user_id=user_id,
            session_id=f"session_{random.randint(1000, 9999)}",
            cluster_id=cluster_id,
            ip_address=f"192.168.1.{random.randint(1, 255)}",
        )
        
        # לוג פעולה עם זמן ביצוע
        duration = random.uniform(100, 5000)  # milliseconds
        log_operation(
            operation=operation,
            level="INFO",
            user_id=user_id,
            cluster_id=cluster_id,
            duration=duration,
            rows_affected=random.randint(0, 10000) if operation == "QUERY_EXECUTION" else None,
        )
        
        time.sleep(0.1)  # מחכה קצת בין לוגים
    
    # יצירת כמה שאילתות לדוגמה
    queries = [
        "SELECT * FROM users WHERE active = true",
        "SELECT COUNT(*) FROM orders WHERE date > '2024-01-01'",
        "UPDATE products SET price = price * 1.1 WHERE category = 'electronics'",
        "INSERT INTO logs (message, level) VALUES ('Test', 'INFO')",
        "DELETE FROM temp_data WHERE created_at < '2024-01-01'",
    ]
    
    for i in range(20):
        query = random.choice(queries)
        cluster_id = random.choice(clusters)
        user_id = random.choice(users)
        duration = random.uniform(50, 3000)
        rows_affected = random.randint(1, 1000)
        
        log_query(
            query=query,
            cluster_id=cluster_id,
            user_id=user_id,
            duration=duration,
            rows_affected=rows_affected,
        )
        
        time.sleep(0.05)
    
    # יצירת כמה אירועי מערכת
    system_events = [
        "SYSTEM_STARTUP",
        "CLUSTER_CONNECTION_ESTABLISHED",
        "BACKUP_COMPLETED",
        "MAINTENANCE_MODE_ENABLED",
        "ALERT_TRIGGERED",
    ]
    
    for i in range(10):
        event = random.choice(system_events)
        severity = random.choice(["INFO", "WARNING", "ERROR"])
        
        log_system_event(
            event=event,
            severity=severity,
            cluster_id=random.choice(clusters) if event.startswith("CLUSTER") else None,
            details=f"System event details for {event}",
        )
        
        time.sleep(0.1)
    
    # יצירת כמה שגיאות לדוגמה
    logger = get_logger("test_errors")
    
    error_messages = [
        "Connection timeout to database",
        "Invalid user credentials",
        "Query execution failed",
        "Insufficient permissions",
        "Resource limit exceeded",
    ]
    
    for i in range(8):
        try:
            # יצירת שגיאה מלאכותית
            if random.random() < 0.5:
                raise ValueError(random.choice(error_messages))
            else:
                raise ConnectionError("Failed to connect to cluster")
        except Exception as e:
            logger.error(
                f"Test error occurred: {str(e)}",
                extra={
                    "user_id": random.choice(users),
                    "cluster_id": random.choice(clusters),
                    "operation": "ERROR_SIMULATION",
                    "error_code": random.randint(1001, 9999),
                },
                exc_info=True,
            )
        
        time.sleep(0.2)
    
    print("✅ נוצרו לוגים לדוגמה בהצלחה!")


def test_log_analytics():
    """בדיקת מערכת האנליטיקס"""
    print("\n🔍 בדיקת מערכת האנליטיקס...")
    
    try:
        from core.log_analytics import LogAnalytics
        
        analytics = LogAnalytics()
        
        # ניתוח דפוסי שגיאות
        print("📊 מבצע ניתוח דפוסי שגיאות...")
        error_analysis = analytics.analyze_error_patterns(days=1)
        
        if error_analysis.get("status") != "error":
            print(f"  📈 סך שגיאות: {error_analysis.get('total_errors', 0)}")
            print(f"  🔢 שגיאות ייחודיות: {error_analysis.get('unique_errors', 0)}")
            
            # הצגת המודולים עם הכי הרבה שגיאות
            top_modules = error_analysis.get('top_modules', {})
            if top_modules:
                print("  🔝 מודולים עם הכי הרבה שגיאות:")
                for module, count in list(top_modules.items())[:3]:
                    print(f"    - {module}: {count}")
        
        # ניתוח מגמות ביצועים
        print("\n⚡ מבצע ניתוח מגמות ביצועים...")
        performance_analysis = analytics.analyze_performance_trends(days=1)
        
        if performance_analysis.get("status") != "error":
            print(f"  📊 סך פעולות: {performance_analysis.get('total_operations', 0)}")
            print(f"  ⏱️ זמן ממוצע: {performance_analysis.get('avg_duration', 0):.2f}ms")
            print(f"  🐌 P95: {performance_analysis.get('p95_duration', 0):.2f}ms")
        
        # ניתוח פעילות משתמשים
        print("\n👥 מבצע ניתוח פעילות משתמשים...")
        user_analysis = analytics.analyze_user_activity(days=1)
        
        if user_analysis.get("status") != "error":
            print(f"  👤 משתמשים ייחודיים: {user_analysis.get('unique_users', 0)}")
            print(f"  🎯 סך פעולות משתמשים: {user_analysis.get('total_user_actions', 0)}")
            
            # הצגת המשתמשים הכי פעילים
            active_users = user_analysis.get('most_active_users', {})
            if active_users:
                print("  🏆 משתמשים הכי פעילים:")
                for user, count in list(active_users.items())[:3]:
                    print(f"    - {user}: {count} פעולות")
        
        print("✅ בדיקת אנליטיקס הושלמה בהצלחה!")
        
    except ImportError:
        print("❌ לא ניתן לייבא מודול אנליטיקס")
    except Exception as e:
        print(f"❌ שגיאה בבדיקת אנליטיקס: {e}")


def test_log_export():
    """בדיקת מערכת הייצוא"""
    print("\n💾 בדיקת מערכת הייצוא...")
    
    try:
        from core.log_export import LogExporter
        
        exporter = LogExporter()
        
        # יצירת ייצוא JSON
        print("📝 יוצר ייצוא JSON...")
        start_date = datetime.now() - timedelta(hours=1)
        json_file = exporter.export_logs_json(start_date=start_date, compress=True)
        
        if json_file:
            print(f"  ✅ ייצוא JSON נוצר: {json_file}")
        else:
            print("  ℹ️ אין נתונים לייצוא")
        
        # יצירת גיבוי
        print("🗄️ יוצר גיבוי...")
        backup_file = exporter.create_backup(backup_type="recent")
        print(f"  ✅ גיבוי נוצר: {backup_file}")
        
        # קבלת היסטוריית ייצואים
        print("📋 בודק היסטוריית ייצואים...")
        history = exporter.get_export_history()
        print(f"  📊 נמצאו {len(history)} קבצי ייצוא")
        
        # הצגת הקבצים החדשים ביותר
        if history:
            print("  📁 קבצים אחרונים:")
            for exp in history[:3]:
                print(f"    - {exp['filename']} ({exp['size_mb']} MB)")
        
        print("✅ בדיקת ייצוא הושלמה בהצלחה!")
        
    except ImportError:
        print("❌ לא ניתן לייבא מודול ייצוא")
    except Exception as e:
        print(f"❌ שגיאה בבדיקת ייצוא: {e}")


def test_log_system_stats():
    """בדיקת סטטיסטיקות מערכת הלוגים"""
    print("\n📊 בדיקת סטטיסטיקות מערכת...")
    
    try:
        stats = logger_system.get_log_statistics()
        
        if stats:
            print(f"  📈 סך לוגים במערכת: {stats.get('total_logs', 0):,}")
            print(f"  📅 לוגים ב-24 שעות: {stats.get('last_24h', 0):,}")
            print(f"  ⚠️ שגיאות השבוע: {stats.get('errors_last_week', 0):,}")
            
            # התפלגות לפי רמות
            by_level = stats.get('by_level', {})
            if by_level:
                print("  📊 התפלגות לפי רמות:")
                for level, count in by_level.items():
                    print(f"    - {level}: {count:,}")
            
            # התפלגות לפי loggers
            by_logger = stats.get('by_logger', {})
            if by_logger:
                print("  🔧 התפלגות לפי מודולים:")
                for logger_name, count in list(by_logger.items())[:5]:
                    print(f"    - {logger_name}: {count:,}")
        
        print("✅ בדיקת סטטיסטיקות הושלמה בהצלחה!")
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקת סטטיסטיקות: {e}")


def main():
    """פונקציה ראשית לבדיקת המערכת"""
    print("🧪 מתחיל בדיקות מערכת הלוגים")
    print("=" * 50)
    
    # יצירת לוגים לדוגמה
    generate_sample_logs()
    
    # בדיקת סטטיסטיקות
    test_log_system_stats()
    
    # בדיקת אנליטיקס
    test_log_analytics()
    
    # בדיקת ייצוא
    test_log_export()
    
    print("\n" + "=" * 50)
    print("🎉 כל הבדיקות הושלמו!")
    print("\n📋 כעת ניתן לגשת לממשק הצפייה בלוגים דרך:")
    print("   1. המערכת הראשית: עמוד 'Logs Viewer'")
    print("   2. הרצה ישירה: python pages/logs_viewer.py")
    print("\n💡 המערכת כוללת:")
    print("   ✅ לוגים מובנים ב-JSON ו-טקסט")
    print("   ✅ שמירה בבסיס נתונים SQLite")
    print("   ✅ אנליטיקס מתקדם ודפוסי שגיאות")
    print("   ✅ ייצוא ב-CSV, JSON, Excel")
    print("   ✅ גיבויים אוטומטיים")
    print("   ✅ ממשק צפייה אינטראקטיבי")
    print("   ✅ חיפוש וסינון מתקדם")


if __name__ == "__main__":
    main()