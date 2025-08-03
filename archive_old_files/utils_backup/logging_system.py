"""
מערכת לוגים מתקדמת לRedshiftManager
מספקת לוגים למערכת, מודולים, וביצועים
"""

import logging
import os
from datetime import datetime
from pathlib import Path
import json
import traceback
from typing import Dict, Any, Optional
import threading

class RedshiftLogger:
    """מנהל לוגים ראשי לכל המערכת"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # יצירת קבצי לוג נפרדים
        self.main_log = self.log_dir / f"main_{datetime.now().strftime('%Y%m%d')}.log"
        self.error_log = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"  
        self.performance_log = self.log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.log"
        self.module_log = self.log_dir / f"modules_{datetime.now().strftime('%Y%m%d')}.log"
        
        self._setup_loggers()
        self._log_lock = threading.Lock()
    
    def _setup_loggers(self):
        """הגדרת כל הלוגרים"""
        
        # פורמט כללי
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # לוגר ראשי
        self.main_logger = logging.getLogger('RedshiftMain')
        self.main_logger.setLevel(logging.INFO)
        main_handler = logging.FileHandler(self.main_log, encoding='utf-8')
        main_handler.setFormatter(formatter)
        self.main_logger.addHandler(main_handler)
        
        # לוגר שגיאות
        self.error_logger = logging.getLogger('RedshiftErrors')
        self.error_logger.setLevel(logging.ERROR)
        error_handler = logging.FileHandler(self.error_log, encoding='utf-8')
        error_handler.setFormatter(formatter)
        self.error_logger.addHandler(error_handler)
        
        # לוגר ביצועים
        self.perf_logger = logging.getLogger('RedshiftPerf')
        self.perf_logger.setLevel(logging.INFO)
        perf_handler = logging.FileHandler(self.performance_log, encoding='utf-8')
        perf_handler.setFormatter(formatter)
        self.perf_logger.addHandler(perf_handler)
        
        # לוגר מודולים
        self.module_logger = logging.getLogger('RedshiftModules')
        self.module_logger.setLevel(logging.INFO)
        module_handler = logging.FileHandler(self.module_log, encoding='utf-8')
        module_handler.setFormatter(formatter)
        self.module_logger.addHandler(module_handler)
        
        # הוספת console handler למהלך הפיתוח
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.main_logger.addHandler(console_handler)
    
    def log_action_start(self, action: str, details: Optional[Dict] = None):
        """תיעוד תחילת פעולה"""
        with self._log_lock:
            msg = f"🟢 התחלת פעולה: {action}"
            if details:
                msg += f" | פרטים: {details}"
            self.main_logger.info(msg)
    
    def log_action_end(self, action: str, success: bool = True, duration: Optional[float] = None, details: Optional[Dict] = None):
        """תיעוד סיום פעולה"""
        with self._log_lock:
            status = "✅ הצלחה" if success else "❌ כישלון"
            msg = f"{status}: {action}"
            
            if duration:
                msg += f" | זמן: {duration:.2f}s"
            if details:
                msg += f" | פרטים: {details}"
                
            if success:
                self.main_logger.info(msg)
            else:
                self.error_logger.error(msg)
    
    def log_error(self, error: Exception, context: str = "", extra_data: Optional[Dict] = None):
        """תיעוד שגיאה מפורט"""
        with self._log_lock:
            error_data = {
                'context': context,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc(),
                'extra_data': extra_data or {}
            }
            
            msg = f"❌ שגיאה בהקשר: {context} | {type(error).__name__}: {error}"
            self.error_logger.error(msg)
            self.error_logger.error(f"Traceback: {traceback.format_exc()}")
    
    def log_performance(self, operation: str, duration: float, details: Optional[Dict] = None):
        """תיעוד ביצועים"""
        with self._log_lock:
            msg = f"⏱️ {operation}: {duration:.3f}s"
            if details:
                msg += f" | {details}"
            self.perf_logger.info(msg)
    
    def log_module_activity(self, module_name: str, action: str, status: str, details: Optional[Dict] = None):
        """תיעוד פעילות מודולים"""
        with self._log_lock:
            msg = f"📦 {module_name} | {action} | {status}"
            if details:
                msg += f" | {details}"
            self.module_logger.info(msg)
    
    def get_log_summary(self) -> Dict[str, Any]:
        """קבלת סיכום לוגים נוכחי"""
        try:
            logs_summary = {
                'timestamp': datetime.now().isoformat(),
                'log_files': {
                    'main': str(self.main_log),
                    'errors': str(self.error_log),
                    'performance': str(self.performance_log),
                    'modules': str(self.module_log)
                },
                'file_sizes': {}
            }
            
            # גדלי קבצים
            for log_type, log_path in logs_summary['log_files'].items():
                if os.path.exists(log_path):
                    logs_summary['file_sizes'][log_type] = os.path.getsize(log_path)
                else:
                    logs_summary['file_sizes'][log_type] = 0
            
            return logs_summary
            
        except Exception as e:
            self.log_error(e, "get_log_summary")
            return {'error': str(e)}

# Global logger instance
logger = RedshiftLogger()

# Helper functions לשימוש קל
def log_start(action: str, **kwargs):
    """helper לתחילת פעולה"""
    logger.log_action_start(action, kwargs if kwargs else None)

def log_end(action: str, success: bool = True, duration: float = None, **kwargs):
    """helper לסיום פעולה"""
    logger.log_action_end(action, success, duration, kwargs if kwargs else None)

def log_error(error: Exception, context: str = "", **kwargs):
    """helper לשגיאות"""
    logger.log_error(error, context, kwargs if kwargs else None)

def log_perf(operation: str, duration: float, **kwargs):
    """helper לביצועים"""
    logger.log_performance(operation, duration, kwargs if kwargs else None)

def log_module(module_name: str, action: str, status: str, **kwargs):
    """helper למודולים"""
    logger.log_module_activity(module_name, action, status, kwargs if kwargs else None)