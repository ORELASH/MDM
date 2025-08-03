#!/usr/bin/env python3
"""
מערכת ייצוא וגיבוי לוגים
Log export and backup system
"""

import csv
import gzip
import json
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class LogExporter:
    """מחלקה לייצוא וגיבוי לוגים"""

    def __init__(self, db_path: str = "logs/logs.db", export_dir: str = "exports"):
        self.db_path = db_path
        self.export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)

    def get_connection(self):
        """קבלת חיבור לבסיס הנתונים"""
        return sqlite3.connect(self.db_path)

    def export_logs_csv(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        level: str = None,
        compress: bool = True,
    ) -> str:
        """ייצוא לוגים לפורמט CSV"""
        try:
            conn = self.get_connection()
            
            # בניית שאילתה
            query = "SELECT * FROM logs WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if level:
                query += " AND level = ?"
                params.append(level)
            
            query += " ORDER BY timestamp"
            
            # שליפת נתונים
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if df.empty:
                return None
            
            # יצירת שם קובץ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs_export_{timestamp}.csv"
            
            if compress:
                filename += ".gz"
                filepath = os.path.join(self.export_dir, filename)
                
                # שמירה עם דחיסה
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    df.to_csv(f, index=False)
            else:
                filepath = os.path.join(self.export_dir, filename)
                df.to_csv(filepath, index=False, encoding='utf-8')
            
            return filepath
            
        except Exception as e:
            raise Exception(f"שגיאה בייצוא CSV: {e}")

    def export_logs_json(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        level: str = None,
        compress: bool = True,
    ) -> str:
        """ייצוא לוגים לפורמט JSON"""
        try:
            conn = self.get_connection()
            
            # בניית שאילתה
            query = "SELECT * FROM logs WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if level:
                query += " AND level = ?"
                params.append(level)
            
            query += " ORDER BY timestamp"
            
            # שליפת נתונים
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if df.empty:
                return None
            
            # המרה ל-JSON
            logs_data = {
                "export_info": {
                    "export_date": datetime.now().isoformat(),
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "level_filter": level,
                    "total_records": len(df),
                },
                "logs": df.to_dict('records')
            }
            
            # יצירת שם קובץ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs_export_{timestamp}.json"
            
            if compress:
                filename += ".gz"
                filepath = os.path.join(self.export_dir, filename)
                
                # שמירה עם דחיסה
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    json.dump(logs_data, f, ensure_ascii=False, indent=2, default=str)
            else:
                filepath = os.path.join(self.export_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(logs_data, f, ensure_ascii=False, indent=2, default=str)
            
            return filepath
            
        except Exception as e:
            raise Exception(f"שגיאה בייצוא JSON: {e}")

    def export_logs_xlsx(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        level: str = None,
    ) -> str:
        """ייצוא לוגים לפורמט Excel"""
        try:
            conn = self.get_connection()
            
            # בניית שאילתה
            query = "SELECT * FROM logs WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if level:
                query += " AND level = ?"
                params.append(level)
            
            query += " ORDER BY timestamp"
            
            # שליפת נתונים
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if df.empty:
                return None
            
            # יצירת שם קובץ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs_export_{timestamp}.xlsx"
            filepath = os.path.join(self.export_dir, filename)
            
            # שמירה כ-Excel עם מספר sheets
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Sheet עיקרי עם כל הנתונים
                df.to_excel(writer, sheet_name='All Logs', index=False)
                
                # Sheet עם סיכום לפי רמות
                if 'level' in df.columns:
                    level_summary = df['level'].value_counts().reset_index()
                    level_summary.columns = ['Level', 'Count']
                    level_summary.to_excel(writer, sheet_name='Level Summary', index=False)
                
                # Sheet עם סיכום לפי מודולים
                if 'logger' in df.columns:
                    logger_summary = df['logger'].value_counts().reset_index()
                    logger_summary.columns = ['Logger', 'Count']
                    logger_summary.to_excel(writer, sheet_name='Logger Summary', index=False)
                
                # Sheet עם שגיאות בלבד
                errors_df = df[df['level'].isin(['ERROR', 'CRITICAL'])] if 'level' in df.columns else pd.DataFrame()
                if not errors_df.empty:
                    errors_df.to_excel(writer, sheet_name='Errors Only', index=False)
            
            return filepath
            
        except Exception as e:
            raise Exception(f"שגיאה בייצוא Excel: {e}")

    def create_backup(self, backup_type: str = "full") -> str:
        """יצירת גיבוי מלא של מערכת הלוגים"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"logs_backup_{backup_type}_{timestamp}"
            backup_dir = os.path.join(self.export_dir, backup_name)
            os.makedirs(backup_dir, exist_ok=True)
            
            if backup_type == "full":
                # גיבוי בסיס הנתונים
                shutil.copy2(self.db_path, os.path.join(backup_dir, "logs.db"))
                
                # גיבוי קבצי לוג אם קיימים
                logs_dir = os.path.dirname(self.db_path)
                for log_file in Path(logs_dir).glob("*.log*"):
                    shutil.copy2(log_file, backup_dir)
                
                # גיבוי קבצי JSON אם קיימים
                for json_file in Path(logs_dir).glob("*.json*"):
                    shutil.copy2(json_file, backup_dir)
            
            elif backup_type == "database_only":
                # גיבוי בסיס הנתונים בלבד
                shutil.copy2(self.db_path, os.path.join(backup_dir, "logs.db"))
            
            elif backup_type == "recent":
                # גיבוי נתונים מהשבוע האחרון
                week_ago = datetime.now() - timedelta(days=7)
                
                # ייצוא נתונים מהשבוע האחרון
                json_file = self.export_logs_json(start_date=week_ago, compress=True)
                if json_file:
                    shutil.move(json_file, backup_dir)
            
            # יצירת מידע על הגיבוי
            backup_info = {
                "backup_date": datetime.now().isoformat(),
                "backup_type": backup_type,
                "backup_name": backup_name,
                "files_included": os.listdir(backup_dir),
            }
            
            with open(os.path.join(backup_dir, "backup_info.json"), 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            # דחיסה לקובץ ZIP
            zip_path = f"{backup_dir}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(backup_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, backup_dir)
                        zipf.write(file_path, arcname)
            
            # ניקוי תיקיית הגיבוי הזמנית
            shutil.rmtree(backup_dir)
            
            return zip_path
            
        except Exception as e:
            raise Exception(f"שגיאה ביצירת גיבוי: {e}")

    def restore_from_backup(self, backup_path: str) -> bool:
        """שחזור מגיבוי"""
        try:
            if not os.path.exists(backup_path):
                raise Exception("קובץ הגיבוי לא נמצא")
            
            # יצירת תיקייה זמנית לחילוץ
            temp_dir = os.path.join(self.export_dir, "temp_restore")
            os.makedirs(temp_dir, exist_ok=True)
            
            # חילוץ הגיבוי
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # קריאת מידע הגיבוי
            backup_info_path = os.path.join(temp_dir, "backup_info.json")
            if os.path.exists(backup_info_path):
                with open(backup_info_path, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)
            
            # שחזור בסיס הנתונים
            backup_db_path = os.path.join(temp_dir, "logs.db")
            if os.path.exists(backup_db_path):
                # יצירת גיבוי של הקובץ הנוכחי
                if os.path.exists(self.db_path):
                    backup_current = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.db_path, backup_current)
                
                # החלפת בסיס הנתונים
                shutil.copy2(backup_db_path, self.db_path)
            
            # ניקוי תיקייה זמנית
            shutil.rmtree(temp_dir)
            
            return True
            
        except Exception as e:
            raise Exception(f"שגיאה בשחזור מגיבוי: {e}")

    def cleanup_old_exports(self, days_to_keep: int = 30):
        """ניקוי ייצואים ישנים"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleaned_count = 0
            
            for file_path in Path(self.export_dir).glob("*"):
                if file_path.is_file():
                    # בדיקת תאריך יצירת הקובץ
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        file_path.unlink()
                        cleaned_count += 1
            
            return cleaned_count
            
        except Exception as e:
            raise Exception(f"שגיאה בניקוי ייצואים ישנים: {e}")

    def get_export_history(self) -> List[Dict[str, Any]]:
        """קבלת היסטוריית ייצואים"""
        try:
            exports = []
            
            for file_path in Path(self.export_dir).glob("*"):
                if file_path.is_file():
                    file_stat = file_path.stat()
                    
                    export_info = {
                        "filename": file_path.name,
                        "filepath": str(file_path),
                        "size_bytes": file_stat.st_size,
                        "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                        "created_date": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                        "modified_date": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "file_type": file_path.suffix,
                    }
                    
                    exports.append(export_info)
            
            # מיון לפי תאריך יצירה (החדשים ראשונים)
            exports.sort(key=lambda x: x['created_date'], reverse=True)
            
            return exports
            
        except Exception as e:
            raise Exception(f"שגיאה בקבלת היסטוריית ייצואים: {e}")

    def schedule_automatic_backup(self, backup_type: str = "recent", frequency: str = "daily"):
        """תזמון גיבויים אוטומטיים (תיאורי)"""
        # זהו interface תיאורי - בפועל יצריך אינטגרציה עם cron או scheduler אחר
        schedule_info = {
            "backup_type": backup_type,
            "frequency": frequency,
            "next_backup": self._calculate_next_backup_time(frequency),
            "enabled": True,
        }
        
        # שמירת הגדרות תזמון
        schedule_path = os.path.join(self.export_dir, "backup_schedule.json")
        with open(schedule_path, 'w', encoding='utf-8') as f:
            json.dump(schedule_info, f, ensure_ascii=False, indent=2, default=str)
        
        return schedule_info

    def _calculate_next_backup_time(self, frequency: str) -> datetime:
        """חישוב זמן הגיבוי הבא"""
        now = datetime.now()
        
        if frequency == "daily":
            return now + timedelta(days=1)
        elif frequency == "weekly":
            return now + timedelta(weeks=1)
        elif frequency == "monthly":
            return now + timedelta(days=30)
        else:
            return now + timedelta(days=1)

    def generate_export_report(self) -> Dict[str, Any]:
        """יצירת דוח על מצב הייצואים והגיבויים"""
        try:
            exports = self.get_export_history()
            
            # חישוב סטטיסטיקות
            total_exports = len(exports)
            total_size_mb = sum(exp['size_mb'] for exp in exports)
            
            # התפלגות לפי סוג קובץ
            file_types = {}
            for exp in exports:
                file_type = exp['file_type']
                if file_type not in file_types:
                    file_types[file_type] = {"count": 0, "size_mb": 0}
                file_types[file_type]["count"] += 1
                file_types[file_type]["size_mb"] += exp['size_mb']
            
            # קבצים מהשבוע האחרון
            week_ago = datetime.now() - timedelta(days=7)
            recent_exports = [
                exp for exp in exports 
                if datetime.fromisoformat(exp['created_date']) > week_ago
            ]
            
            report = {
                "report_date": datetime.now().isoformat(),
                "summary": {
                    "total_exports": total_exports,
                    "total_size_mb": round(total_size_mb, 2),
                    "exports_this_week": len(recent_exports),
                    "export_directory": self.export_dir,
                },
                "file_type_distribution": file_types,
                "recent_exports": recent_exports[:10],  # 10 האחרונים
                "oldest_export": exports[-1] if exports else None,
                "largest_export": max(exports, key=lambda x: x['size_mb']) if exports else None,
            }
            
            return report
            
        except Exception as e:
            raise Exception(f"שגיאה ביצירת דוח ייצוא: {e}")


# פונקציות עזר לשימוש נוח
def export_logs_quick(format: str = "json", days: int = 7, compress: bool = True) -> str:
    """ייצוא מהיר של לוגים"""
    exporter = LogExporter()
    start_date = datetime.now() - timedelta(days=days)
    
    if format.lower() == "csv":
        return exporter.export_logs_csv(start_date=start_date, compress=compress)
    elif format.lower() == "json":
        return exporter.export_logs_json(start_date=start_date, compress=compress)
    elif format.lower() == "xlsx":
        return exporter.export_logs_xlsx(start_date=start_date)
    else:
        raise ValueError("פורמט לא נתמך. השתמש ב: csv, json, xlsx")


def create_backup_quick(backup_type: str = "recent") -> str:
    """יצירת גיבוי מהיר"""
    exporter = LogExporter()
    return exporter.create_backup(backup_type=backup_type)