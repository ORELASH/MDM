"""
דקורטור למעקב אוטומטי אחר משימות
מעקב זמן, לוגים ותיעוד אוטומטי
"""

import time
import functools
from typing import Callable, Any, Optional, Dict
from .logging_system import logger, log_start, log_end, log_error
from .activity_tracker import tracker, start_task, complete_task, add_created_file, add_modified_file

def track_task(
    task_name: Optional[str] = None,
    task_id: Optional[str] = None,
    log_performance: bool = True,
    track_files: bool = True
):
    """
    דקורטור למעקב אחר משימות
    
    Args:
        task_name: שם המשימה (אם לא מוגדר, ייקח את שם הפונקציה)
        task_id: ID של המשימה (אם לא מוגדר, ייקח את שם הפונקציה)
        log_performance: האם לתעד ביצועים
        track_files: האם לעקוב אחר קבצים שנוצרו/שונו
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # הגדרת שמות
            actual_task_name = task_name or func.__name__
            actual_task_id = task_id or func.__name__
            
            # מעקב קבצים לפני
            files_before = set()
            if track_files:
                try:
                    import os
                    for root, dirs, files in os.walk('.'):
                        for file in files:
                            if file.endswith(('.py', '.json', '.md', '.txt', '.yaml', '.yml')):
                                files_before.add(os.path.join(root, file))
                except:
                    pass
            
            # התחלת מעקב
            start_time = time.time()
            log_start(actual_task_name)
            task_record = start_task(actual_task_id, actual_task_name)
            
            try:
                # ביצוע הפונקציה
                result = func(*args, **kwargs)
                
                # סיום מוצלח
                end_time = time.time()
                duration = end_time - start_time
                
                # מעקב קבצים אחרי
                files_created = []
                files_modified = []
                
                if track_files:
                    try:
                        files_after = set()
                        for root, dirs, files in os.walk('.'):
                            for file in files:
                                if file.endswith(('.py', '.json', '.md', '.txt', '.yaml', '.yml')):
                                    files_after.add(os.path.join(root, file))
                        
                        files_created = list(files_after - files_before)
                        # files_modified יכול להיות מורכב יותר - נשאיר פשוט לעת עתה
                        
                    except:
                        pass
                
                # תיעוד סיום
                log_end(actual_task_name, True, duration)
                if log_performance:
                    logger.log_performance(actual_task_name, duration)
                
                complete_task(
                    actual_task_id, 
                    success=True,
                    duration_seconds=duration,
                    files_created=files_created,
                    files_modified=files_modified
                )
                
                return result
                
            except Exception as e:
                # סיום עם שגיאה
                end_time = time.time()
                duration = end_time - start_time
                
                log_error(e, actual_task_name)
                log_end(actual_task_name, False, duration)
                
                complete_task(
                    actual_task_id,
                    success=False,
                    duration_seconds=duration,
                    errors=[str(e)]
                )
                
                raise
        
        return wrapper
    return decorator

# דקורטור פשוט יותר לשימוש מהיר
def track(name: str = None):
    """דקורטור פשוט למעקב משימות"""
    return track_task(task_name=name, log_performance=True, track_files=True)

# Context manager למעקב ידני
class TaskTracker:
    """Context manager למעקב משימות"""
    
    def __init__(self, task_name: str, task_id: str = None):
        self.task_name = task_name
        self.task_id = task_id or task_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        log_start(self.task_name)
        start_task(self.task_id, self.task_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        if success:
            log_end(self.task_name, True, duration)
            complete_task(self.task_id, success=True, duration_seconds=duration)
        else:
            log_error(exc_val, self.task_name)
            log_end(self.task_name, False, duration)
            complete_task(self.task_id, success=False, duration_seconds=duration, errors=[str(exc_val)])
        
        return False  # Don't suppress exceptions