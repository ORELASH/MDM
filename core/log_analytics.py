#!/usr/bin/env python3
"""
מערכת אנליטיקס מתקדמת ללוגים
Advanced log analytics and pattern recognition
"""

import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class LogAnalytics:
    """מחלקה לאנליטיקס מתקדם של לוגים"""

    def __init__(self, db_path: str = "logs/logs.db"):
        self.db_path = db_path

    def get_connection(self):
        """קבלת חיבור לבסיס הנתונים"""
        return sqlite3.connect(self.db_path)

    def analyze_error_patterns(self, days: int = 7) -> Dict[str, Any]:
        """ניתוח דפוסי שגיאות"""
        try:
            conn = self.get_connection()
            
            # שליפת שגיאות מהתקופה הרצויה
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            query = """
                SELECT message, exception_type, exception_message, timestamp, module, function
                FROM logs 
                WHERE level IN ('ERROR', 'CRITICAL') 
                AND timestamp >= ?
                ORDER BY timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(cutoff_date,))
            conn.close()
            
            if df.empty:
                return {"status": "no_data", "message": "לא נמצאו שגיאות בתקופה הנבחרת"}
            
            # ניתוח דפוסים
            analysis = {
                "total_errors": len(df),
                "unique_errors": df['message'].nunique(),
                "time_range": f"{days} ימים אחרונים",
                "error_frequency": self._analyze_error_frequency(df),
                "error_categories": self._categorize_errors(df),
                "error_timeline": self._create_error_timeline(df),
                "top_modules": self._analyze_modules_with_errors(df),
                "exception_types": self._analyze_exception_types(df),
                "patterns": self._identify_error_patterns(df),
            }
            
            return analysis
            
        except Exception as e:
            return {"status": "error", "message": f"שגיאה בניתוח: {e}"}

    def _analyze_error_frequency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """ניתוח תדירות שגיאות"""
        # חישוב תדירות לפי הודעה
        message_counts = df['message'].value_counts().head(10)
        
        # חישוב שינויים בזמן
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.floor('H')
        hourly_counts = df.groupby('hour').size()
        
        return {
            "most_frequent_messages": message_counts.to_dict(),
            "hourly_distribution": hourly_counts.to_dict(),
            "peak_hour": hourly_counts.idxmax() if not hourly_counts.empty else None,
            "peak_count": hourly_counts.max() if not hourly_counts.empty else 0,
        }

    def _categorize_errors(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """קטגוריזציה של שגיאות לפי סוג"""
        categories = {
            "Database": [],
            "Network": [],
            "Authentication": [],
            "Validation": [],
            "System": [],
            "Unknown": []
        }
        
        # דפוסי חיפוש לקטגוריות
        patterns = {
            "Database": [r"database", r"sql", r"connection", r"query", r"table", r"column"],
            "Network": [r"network", r"timeout", r"connection refused", r"host", r"port"],
            "Authentication": [r"auth", r"login", r"password", r"token", r"permission"],
            "Validation": [r"validation", r"invalid", r"required", r"format", r"type"],
            "System": [r"system", r"memory", r"disk", r"cpu", r"resource"],
        }
        
        for _, row in df.iterrows():
            message = row['message'].lower()
            categorized = False
            
            for category, category_patterns in patterns.items():
                if any(re.search(pattern, message) for pattern in category_patterns):
                    categories[category].append(row['message'])
                    categorized = True
                    break
            
            if not categorized:
                categories["Unknown"].append(row['message'])
        
        # המרה לספירה
        return {cat: len(messages) for cat, messages in categories.items() if messages}

    def _create_error_timeline(self, df: pd.DataFrame) -> Dict[str, Any]:
        """יצירת timeline של שגיאות"""
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        
        daily_counts = df.groupby('date').size()
        
        return {
            "daily_counts": {str(date): count for date, count in daily_counts.items()},
            "trend": self._calculate_trend(daily_counts),
        }

    def _calculate_trend(self, series: pd.Series) -> str:
        """חישוב מגמה"""
        if len(series) < 2:
            return "insufficient_data"
        
        # חישוב מגמה פשוט
        first_half = series.iloc[:len(series)//2].mean()
        second_half = series.iloc[len(series)//2:].mean()
        
        if second_half > first_half * 1.1:
            return "increasing"
        elif second_half < first_half * 0.9:
            return "decreasing"
        else:
            return "stable"

    def _analyze_modules_with_errors(self, df: pd.DataFrame) -> Dict[str, int]:
        """ניתוח מודולים עם שגיאות"""
        return df['module'].value_counts().head(10).to_dict()

    def _analyze_exception_types(self, df: pd.DataFrame) -> Dict[str, int]:
        """ניתוח סוגי חריגות"""
        exception_counts = df['exception_type'].value_counts()
        return exception_counts.to_dict()

    def _identify_error_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """זיהוי דפוסים בשגיאות"""
        patterns = []
        
        # דפוס 1: שגיאות חוזרות ברצף
        df_sorted = df.sort_values('timestamp')
        message_sequences = []
        current_message = None
        count = 0
        
        for _, row in df_sorted.iterrows():
            if row['message'] == current_message:
                count += 1
            else:
                if count >= 3:  # אם יש 3 או יותר שגיאות זהות ברצף
                    message_sequences.append({
                        "type": "repeated_error",
                        "message": current_message,
                        "count": count,
                        "severity": "high" if count >= 10 else "medium"
                    })
                current_message = row['message']
                count = 1
        
        patterns.extend(message_sequences)
        
        # דפוס 2: פרצי שגיאות (burst errors)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['minute'] = df['timestamp'].dt.floor('min')
        minute_counts = df.groupby('minute').size()
        
        high_error_minutes = minute_counts[minute_counts >= 5]  # 5+ שגיאות בדקה
        if not high_error_minutes.empty:
            patterns.append({
                "type": "error_burst",
                "count": len(high_error_minutes),
                "max_per_minute": high_error_minutes.max(),
                "severity": "high"
            })
        
        return patterns

    def analyze_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """ניתוח מגמות ביצועים"""
        try:
            conn = self.get_connection()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # שליפת נתוני ביצועים
            query = """
                SELECT timestamp, duration_ms, operation, cluster_id
                FROM logs 
                WHERE duration_ms IS NOT NULL 
                AND timestamp >= ?
                ORDER BY timestamp
            """
            
            df = pd.read_sql_query(query, conn, params=(cutoff_date,))
            conn.close()
            
            if df.empty:
                return {"status": "no_data", "message": "לא נמצאו נתוני ביצועים"}
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            analysis = {
                "total_operations": len(df),
                "avg_duration": df['duration_ms'].mean(),
                "median_duration": df['duration_ms'].median(),
                "p95_duration": df['duration_ms'].quantile(0.95),
                "slowest_operations": self._find_slowest_operations(df),
                "performance_by_operation": self._analyze_performance_by_operation(df),
                "performance_trends": self._analyze_performance_trends_over_time(df),
                "cluster_performance": self._analyze_cluster_performance(df),
            }
            
            return analysis
            
        except Exception as e:
            return {"status": "error", "message": f"שגיאה בניתוח ביצועים: {e}"}

    def _find_slowest_operations(self, df: pd.DataFrame, limit: int = 10) -> List[Dict]:
        """מציאת הפעולות הכי איטיות"""
        slowest = df.nlargest(limit, 'duration_ms')
        return slowest[['timestamp', 'operation', 'duration_ms', 'cluster_id']].to_dict('records')

    def _analyze_performance_by_operation(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """ניתוח ביצועים לפי סוג פעולה"""
        performance = {}
        
        for operation in df['operation'].unique():
            if pd.isna(operation):
                continue
                
            op_data = df[df['operation'] == operation]['duration_ms']
            performance[operation] = {
                "count": len(op_data),
                "avg_duration": op_data.mean(),
                "median_duration": op_data.median(),
                "max_duration": op_data.max(),
                "min_duration": op_data.min(),
            }
        
        return performance

    def _analyze_performance_trends_over_time(self, df: pd.DataFrame) -> Dict[str, Any]:
        """ניתוח מגמות ביצועים לאורך זמן"""
        df['hour'] = df['timestamp'].dt.floor('H')
        hourly_performance = df.groupby('hour')['duration_ms'].agg(['mean', 'count'])
        
        return {
            "hourly_avg": hourly_performance['mean'].to_dict(),
            "hourly_count": hourly_performance['count'].to_dict(),
        }

    def _analyze_cluster_performance(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """ניתוח ביצועים לפי אשכול"""
        performance = {}
        
        for cluster in df['cluster_id'].unique():
            if pd.isna(cluster):
                continue
                
            cluster_data = df[df['cluster_id'] == cluster]['duration_ms']
            performance[cluster] = {
                "count": len(cluster_data),
                "avg_duration": cluster_data.mean(),
                "median_duration": cluster_data.median(),
            }
        
        return performance

    def analyze_user_activity(self, days: int = 7) -> Dict[str, Any]:
        """ניתוח פעילות משתמשים"""
        try:
            conn = self.get_connection()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            query = """
                SELECT timestamp, user_id, operation, level
                FROM logs 
                WHERE user_id IS NOT NULL 
                AND timestamp >= ?
                ORDER BY timestamp
            """
            
            df = pd.read_sql_query(query, conn, params=(cutoff_date,))
            conn.close()
            
            if df.empty:
                return {"status": "no_data", "message": "לא נמצאו נתוני משתמשים"}
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            analysis = {
                "total_user_actions": len(df),
                "unique_users": df['user_id'].nunique(),
                "most_active_users": df['user_id'].value_counts().head(10).to_dict(),
                "user_operations": self._analyze_user_operations(df),
                "user_activity_timeline": self._analyze_user_activity_timeline(df),
                "user_error_rates": self._analyze_user_error_rates(df),
            }
            
            return analysis
            
        except Exception as e:
            return {"status": "error", "message": f"שגיאה בניתוח פעילות משתמשים: {e}"}

    def _analyze_user_operations(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """ניתוח פעולות לפי משתמש"""
        user_ops = {}
        
        for user_id in df['user_id'].unique():
            user_data = df[df['user_id'] == user_id]
            user_ops[user_id] = {
                "total_actions": len(user_data),
                "operations": user_data['operation'].value_counts().to_dict(),
                "first_activity": user_data['timestamp'].min().isoformat(),
                "last_activity": user_data['timestamp'].max().isoformat(),
            }
        
        return user_ops

    def _analyze_user_activity_timeline(self, df: pd.DataFrame) -> Dict[str, Any]:
        """ניתוח timeline של פעילות משתמשים"""
        df['hour'] = df['timestamp'].dt.floor('H')
        hourly_users = df.groupby('hour')['user_id'].nunique()
        
        return {
            "hourly_active_users": hourly_users.to_dict(),
            "peak_activity_hour": hourly_users.idxmax().isoformat() if not hourly_users.empty else None,
            "peak_user_count": hourly_users.max() if not hourly_users.empty else 0,
        }

    def _analyze_user_error_rates(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """ניתוח שיעורי שגיאות למשתמש"""
        user_errors = {}
        
        for user_id in df['user_id'].unique():
            user_data = df[df['user_id'] == user_id]
            total_actions = len(user_data)
            errors = len(user_data[user_data['level'].isin(['ERROR', 'CRITICAL'])])
            
            user_errors[user_id] = {
                "total_actions": total_actions,
                "errors": errors,
                "error_rate": (errors / total_actions * 100) if total_actions > 0 else 0,
            }
        
        return user_errors

    def generate_insights_report(self, days: int = 7) -> Dict[str, Any]:
        """יצירת דוח תובנות מקיף"""
        report = {
            "report_date": datetime.now().isoformat(),
            "analysis_period": f"{days} ימים",
            "error_analysis": self.analyze_error_patterns(days),
            "performance_analysis": self.analyze_performance_trends(days),
            "user_activity": self.analyze_user_activity(days),
            "recommendations": self._generate_recommendations(),
        }
        
        return report

    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """יצירת המלצות על בסיס הניתוח"""
        recommendations = [
            {
                "category": "Performance",
                "title": "מעקב אחר שאילתות איטיות",
                "description": "המלץ להגדיר התראות עבור שאילתות שלוקחות יותר מ-30 שניות",
                "priority": "medium",
            },
            {
                "category": "Errors",
                "title": "ניטור שגיאות חוזרות",
                "description": "המלץ להקים מערכת התראות עבור שגיאות שחוזרות יותר מ-5 פעמים ב-10 דקות",
                "priority": "high",
            },
            {
                "category": "Users",
                "title": "ניתוח דפוסי שימוש",
                "description": "המלץ לנתח דפוסי שימוש של משתמשים לזיהוי בעיות פוטנציאליות",
                "priority": "low",
            },
        ]
        
        return recommendations

    def search_logs_advanced(
        self, 
        query: str, 
        search_type: str = "simple",
        days: int = 7,
        level: str = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """חיפוש מתקדם בלוגים"""
        try:
            conn = self.get_connection()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            base_query = """
                SELECT * FROM logs 
                WHERE timestamp >= ?
            """
            params = [cutoff_date]
            
            # הוספת מסנן רמה
            if level:
                base_query += " AND level = ?"
                params.append(level)
            
            # הוספת חיפוש טקסט
            if search_type == "simple":
                base_query += " AND message LIKE ?"
                params.append(f"%{query}%")
            elif search_type == "regex":
                # SQLite תומך ב-REGEX רק עם extension
                base_query += " AND message LIKE ?"
                params.append(f"%{query}%")
            elif search_type == "exact":
                base_query += " AND message = ?"
                params.append(query)
            
            base_query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            df = pd.read_sql_query(base_query, conn, params=params)
            conn.close()
            
            # ניתוח תוצאות
            analysis = {
                "total_results": len(df),
                "search_query": query,
                "search_type": search_type,
                "time_range": f"{days} ימים",
                "results": df.to_dict('records') if not df.empty else [],
                "level_distribution": df['level'].value_counts().to_dict() if not df.empty else {},
                "module_distribution": df['logger'].value_counts().to_dict() if not df.empty else {},
            }
            
            return analysis
            
        except Exception as e:
            return {"status": "error", "message": f"שגיאה בחיפוש: {e}"}

    def export_analysis_report(self, analysis: Dict[str, Any], format: str = "json") -> str:
        """ייצוא דוח ניתוח"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            filename = f"log_analysis_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
        
        return filename