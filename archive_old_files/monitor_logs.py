#!/usr/bin/env python3
"""
סקריפט ניטור לוגים בזמן אמת
מציג לוגים חדשים כשהם נכתבים
"""

import os
import time
import argparse
from pathlib import Path
from datetime import datetime
import threading
import sys

class LogMonitor:
    """מוניטור לוגים בזמן אמת"""
    
    def __init__(self, log_dir: str = "logs", activity_dir: str = "activity_logs"):
        self.log_dir = Path(log_dir)
        self.activity_dir = Path(activity_dir)
        self.monitoring = False
        self.file_positions = {}
        
        # יצירת ספריות אם לא קיימות
        self.log_dir.mkdir(exist_ok=True)
        self.activity_dir.mkdir(exist_ok=True)
    
    def get_log_files(self):
        """קבלת רשימת קבצי לוג נוכחיים"""
        today = datetime.now().strftime('%Y%m%d')
        
        log_files = {
            'main': self.log_dir / f"main_{today}.log",
            'errors': self.log_dir / f"errors_{today}.log",
            'performance': self.log_dir / f"performance_{today}.log",
            'modules': self.log_dir / f"modules_{today}.log"
        }
        
        activity_files = {
            'activity': self.activity_dir / f"activity_{today}.json",
            'summary': self.activity_dir / f"summary_{today}.md"
        }
        
        return {**log_files, **activity_files}
    
    def monitor_file(self, file_path: Path, file_type: str):
        """מעקב אחר קובץ בודד"""
        if not file_path.exists():
            return
            
        # קבלת מיקום נוכחי בקובץ
        current_position = self.file_positions.get(str(file_path), 0)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.seek(current_position)
                new_lines = f.readlines()
                
                if new_lines:
                    print(f"\n📁 {file_type.upper()} - {file_path.name}")
                    print("=" * 50)
                    for line in new_lines:
                        print(line.rstrip())
                    print()
                
                # עדכון מיקום
                self.file_positions[str(file_path)] = f.tell()
                
        except Exception as e:
            print(f"שגיאה בקריאת {file_path}: {e}")
    
    def monitor_all(self, interval: float = 1.0):
        """מעקב אחר כל הקבצים"""
        print(f"🔍 התחלת ניטור לוגים...")
        print(f"📁 ספריית לוגים: {self.log_dir}")
        print(f"📁 ספריית פעילות: {self.activity_dir}")
        print(f"⏱️ אינטרוול: {interval} שניות")
        print("=" * 60)
        
        self.monitoring = True
        
        try:
            while self.monitoring:
                log_files = self.get_log_files()
                
                for file_type, file_path in log_files.items():
                    if file_path.exists():
                        self.monitor_file(file_path, file_type)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 ניטור הופסק על ידי המשתמש")
        except Exception as e:
            print(f"\n❌ שגיאה בניטור: {e}")
        finally:
            self.monitoring = False
    
    def show_status(self):
        """הצגת סטטוס קבצי לוג"""
        log_files = self.get_log_files()
        
        print("📊 סטטוס קבצי לוג:")
        print("=" * 30)
        
        for file_type, file_path in log_files.items():
            if file_path.exists():
                size = file_path.stat().st_size
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                print(f"✅ {file_type}: {size:,} bytes (עודכן: {mtime.strftime('%H:%M:%S')})")
            else:
                print(f"❌ {file_type}: לא קיים")
    
    def tail_file(self, file_type: str, lines: int = 20):
        """הצגת שורות אחרונות מקובץ"""
        log_files = self.get_log_files()
        
        if file_type not in log_files:
            print(f"❌ סוג קובץ לא ידוע: {file_type}")
            print(f"אפשרויות: {', '.join(log_files.keys())}")
            return
        
        file_path = log_files[file_type]
        
        if not file_path.exists():
            print(f"❌ קובץ לא קיים: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                print(f"📄 {lines} שורות אחרונות מ-{file_type}:")
                print("=" * 50)
                for line in tail_lines:
                    print(line.rstrip())
                    
        except Exception as e:
            print(f"❌ שגיאה בקריאת קובץ: {e}")

def main():
    parser = argparse.ArgumentParser(description='מוניטור לוגים לRedshiftManager')
    parser.add_argument('--monitor', '-m', action='store_true', help='התחלת מעקב בזמן אמת')
    parser.add_argument('--status', '-s', action='store_true', help='הצגת סטטוס קבצים')
    parser.add_argument('--tail', '-t', type=str, help='הצגת שורות אחרונות מקובץ')
    parser.add_argument('--lines', '-n', type=int, default=20, help='מספר שורות להצגה (ברירת מחדל: 20)')
    parser.add_argument('--interval', '-i', type=float, default=1.0, help='אינטרוול מעקב בשניות')
    
    args = parser.parse_args()
    
    monitor = LogMonitor()
    
    if args.monitor:
        monitor.monitor_all(args.interval)
    elif args.status:
        monitor.show_status()
    elif args.tail:
        monitor.tail_file(args.tail, args.lines)
    else:
        print("🔍 מוניטור לוגים RedshiftManager")
        print()
        print("שימוש:")
        print("  python monitor_logs.py --monitor     # מעקב בזמן אמת")
        print("  python monitor_logs.py --status      # סטטוס קבצים")
        print("  python monitor_logs.py --tail main   # שורות אחרונות")
        print()
        print("סוגי קבצים זמינים:")
        log_files = monitor.get_log_files()
        for file_type in log_files.keys():
            print(f"  - {file_type}")

if __name__ == "__main__":
    main()