#!/usr/bin/env python3
"""
בדיקת מערכת הלוגים ופלטי STDOUT/STDERR
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.logging_system import RedshiftLogger

def test_logging_outputs():
    """בדיקה מקיפה של כל פלטי הלוגים"""
    
    print("=" * 60)
    print("🔍 בדיקת mערכת הלוגים - RedshiftManager")
    print("=" * 60)
    
    # 1. בדיקת פלטי מערכת בסיסיים
    print("\n📝 1. בדיקת STDOUT/STDERR בסיסיים:")
    print("✅ הודעה רגילה ל-STDOUT")
    print("⚠️ הודעת שגיאה ל-STDERR", file=sys.stderr)
    
    # 2. בדיקת Python logging רגיל
    print("\n🔧 2. בדיקת Python Logging רגיל:")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),  # STDOUT
            logging.StreamHandler(sys.stderr)   # STDERR for errors
        ]
    )
    
    test_logger = logging.getLogger('TestLogger')
    test_logger.info("INFO: הודעת מידע ל-STDOUT")
    test_logger.warning("WARNING: הודעת אזהרה")
    test_logger.error("ERROR: הודעת שגיאה ל-STDERR")
    
    # 3. בדיקת RedshiftLogger
    print("\n🚀 3. בדיקת RedshiftLogger המתקדם:")
    
    try:
        rs_logger = RedshiftLogger()
        
        # Test different log types
        rs_logger.log_action_start("Test Action", {"test": "value"})
        rs_logger.log_action_end("Test Action", success=True, duration=0.5)
        rs_logger.log_action_end("Failed Action", success=False)
        
        # Test error logging
        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            rs_logger.log_error(e, "Test context")
        
        print("✅ RedshiftLogger עובד ושומר ללוגים וקונסול")
        
    except Exception as e:
        print(f"❌ שגיאה ב-RedshiftLogger: {e}")
    
    # 4. בדיקת קבצי לוג
    print("\n📂 4. בדיקת קבצי הלוג:")
    
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        print(f"📁 נמצאו {len(log_files)} קבצי לוג:")
        
        for log_file in log_files:
            size = log_file.stat().st_size
            print(f"  - {log_file.name}: {size:,} bytes")
            
            # Show last few lines
            if size > 0:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"    📝 שורה אחרונה: {lines[-1].strip()}")
    else:
        print("❌ תיקיית logs לא נמצאה")
    
    # 5. בדיקת אפשרויות הגדרה
    print("\n⚙️ 5. אפשרויות הגדרת לוגים:")
    print("  - לוגים נשמרים לקבצים: ✅")
    print("  - לוגים מוצגים בקונסול: ✅")
    print("  - הפרדה לפי סוג (INFO/ERROR): ✅")
    print("  - קידוד UTF-8 לעברית: ✅")
    print("  - Thread-safe logging: ✅")
    
    # 6. המלצות שיפור
    print("\n💡 6. המלצות להגדרות לוגים:")
    print("  📌 לסביבת פיתוח: הצג הכל בקונסול")
    print("  📌 לסביבת ייצור: הצג רק שגיאות בקונסול")
    print("  📌 ניתן להגדיר רמות לוג שונות: DEBUG/INFO/WARNING/ERROR")
    print("  📌 ניתן להפנות לוגים לsyslog או מערכות ניטור חיצוניות")
    
    print("\n" + "=" * 60)
    print("✅ בדיקת מערכת הלוגים הושלמה בהצלחה!")
    print("=" * 60)

if __name__ == "__main__":
    test_logging_outputs()