"""
מערכת מעקב פעילות ותיעוד משימות
מתעדת כל פעולה ומשימה שמושלמת
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import threading

@dataclass
class TaskRecord:
    """רקורד משימה"""
    task_id: str
    name: str
    status: str  # started, completed, failed
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    files_created: Optional[List[str]] = None
    files_modified: Optional[List[str]] = None
    errors: Optional[List[str]] = None

class ActivityTracker:
    """מעקב פעילות ותיעוד משימות"""
    
    def __init__(self, log_dir: str = "activity_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # קובץ פעילות יומי
        today = datetime.now().strftime('%Y%m%d')
        self.activity_file = self.log_dir / f"activity_{today}.json"
        self.summary_file = self.log_dir / f"summary_{today}.md"
        
        # מעקב משימות פעילות
        self.active_tasks: Dict[str, TaskRecord] = {}
        self.completed_tasks: List[TaskRecord] = []
        
        # נעילה לthread safety
        self._lock = threading.Lock()
        
        # טעינת נתונים קיימים
        self._load_existing_data()
    
    def _load_existing_data(self):
        """טעינת נתונים קיימים מהקובץ"""
        try:
            if self.activity_file.exists():
                with open(self.activity_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # המרת רשימת משימות גמורות
                    self.completed_tasks = [
                        TaskRecord(**task) for task in data.get('completed_tasks', [])
                    ]
        except Exception as e:
            print(f"שגיאה בטעינת נתוני פעילות: {e}")
    
    def start_task(
        self, 
        task_id: str, 
        name: str, 
        details: Optional[Dict[str, Any]] = None
    ) -> TaskRecord:
        """התחלת משימה חדשה"""
        with self._lock:
            task = TaskRecord(
                task_id=task_id,
                name=name,
                status="started",
                start_time=datetime.now().isoformat(),
                details=details or {},
                files_created=[],
                files_modified=[],
                errors=[]
            )
            
            self.active_tasks[task_id] = task
            self._save_data()
            
            print(f"🟢 התחלת משימה: {name} (ID: {task_id})")
            return task
    
    def complete_task(
        self, 
        task_id: str, 
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        files_created: Optional[List[str]] = None,
        files_modified: Optional[List[str]] = None,
        errors: Optional[List[str]] = None
    ):
        """סיום משימה"""
        with self._lock:
            if task_id not in self.active_tasks:
                print(f"⚠️ משימה {task_id} לא נמצאת במעקב")
                return
            
            task = self.active_tasks[task_id]
            
            # עדכון פרטי סיום
            task.end_time = datetime.now().isoformat()
            task.status = "completed" if success else "failed"
            
            # חישוב משך זמן
            start_dt = datetime.fromisoformat(task.start_time)
            end_dt = datetime.fromisoformat(task.end_time)
            task.duration_seconds = (end_dt - start_dt).total_seconds()
            
            # עדכון פרטים
            if details:
                task.details.update(details)
            if files_created:
                task.files_created.extend(files_created)
            if files_modified:
                task.files_modified.extend(files_modified)
            if errors:
                task.errors.extend(errors)
            
            # העברה לרשימת משימות גמורות
            self.completed_tasks.append(task)
            del self.active_tasks[task_id]
            
            # שמירה ועדכון סיכום
            self._save_data()
            self._update_summary()
            
            status_icon = "✅" if success else "❌"
            duration_str = f" ({task.duration_seconds:.1f}s)" if task.duration_seconds else ""
            print(f"{status_icon} סיום משימה: {task.name}{duration_str}")
    
    def add_file_created(self, task_id: str, file_path: str):
        """הוספת קובץ שנוצר למשימה"""
        with self._lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id].files_created.append(file_path)
                self._save_data()
    
    def add_file_modified(self, task_id: str, file_path: str):
        """הוספת קובץ ששונה למשימה"""
        with self._lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id].files_modified.append(file_path)
                self._save_data()
    
    def add_error(self, task_id: str, error: str):
        """הוספת שגיאה למשימה"""
        with self._lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id].errors.append(error)
                self._save_data()
    
    def _save_data(self):
        """שמירת נתונים לקובץ"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'active_tasks': [asdict(task) for task in self.active_tasks.values()],
                'completed_tasks': [asdict(task) for task in self.completed_tasks]
            }
            
            with open(self.activity_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"שגיאה בשמירת נתוני פעילות: {e}")
    
    def _update_summary(self):
        """עדכון קובץ סיכום יומי"""
        try:
            with open(self.summary_file, 'w', encoding='utf-8') as f:
                f.write(f"# 📅 סיכום פעילות - {datetime.now().strftime('%d.%m.%Y')}\n\n")
                
                # סטטיסטיקות
                total_tasks = len(self.completed_tasks)
                successful_tasks = len([t for t in self.completed_tasks if t.status == "completed"])
                failed_tasks = len([t for t in self.completed_tasks if t.status == "failed"])
                
                f.write("## 📊 סטטיסטיקות\n")
                f.write(f"- **סה\"כ משימות:** {total_tasks}\n")
                f.write(f"- **הושלמו בהצלחה:** {successful_tasks} ✅\n")
                f.write(f"- **נכשלו:** {failed_tasks} ❌\n")
                f.write(f"- **משימות פעילות:** {len(self.active_tasks)} 🔄\n\n")
                
                # משימות שהושלמו
                if self.completed_tasks:
                    f.write("## ✅ משימות שהושלמו\n\n")
                    for task in self.completed_tasks:
                        icon = "✅" if task.status == "completed" else "❌"
                        duration = f" ({task.duration_seconds:.1f}s)" if task.duration_seconds else ""
                        f.write(f"### {icon} {task.name}{duration}\n")
                        f.write(f"- **זמן התחלה:** {task.start_time}\n")
                        f.write(f"- **זמן סיום:** {task.end_time}\n")
                        
                        if task.files_created:
                            f.write(f"- **קבצים שנוצרו:** {len(task.files_created)}\n")
                            for file_path in task.files_created:
                                f.write(f"  - `{file_path}`\n")
                        
                        if task.files_modified:
                            f.write(f"- **קבצים ששונו:** {len(task.files_modified)}\n")
                            for file_path in task.files_modified:
                                f.write(f"  - `{file_path}`\n")
                        
                        if task.errors:
                            f.write(f"- **שגיאות:** {len(task.errors)}\n")
                            for error in task.errors:
                                f.write(f"  - `{error}`\n")
                        
                        f.write("\n")
                
                # משימות פעילות
                if self.active_tasks:
                    f.write("## 🔄 משימות פעילות\n\n")
                    for task in self.active_tasks.values():
                        f.write(f"### 🔄 {task.name}\n")
                        f.write(f"- **התחלה:** {task.start_time}\n")
                        f.write(f"- **סטטוס:** {task.status}\n\n")
                
        except Exception as e:
            print(f"שגיאה בעדכון סיכום: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """קבלת סטטוס נוכחי"""
        with self._lock:
            return {
                'active_tasks': len(self.active_tasks),
                'completed_tasks': len(self.completed_tasks),
                'successful_tasks': len([t for t in self.completed_tasks if t.status == "completed"]),
                'failed_tasks': len([t for t in self.completed_tasks if t.status == "failed"]),
                'activity_file': str(self.activity_file),
                'summary_file': str(self.summary_file)
            }

# Global tracker instance
tracker = ActivityTracker()

# Helper functions
def start_task(task_id: str, name: str, **details):
    """התחלת משימה - helper function"""
    return tracker.start_task(task_id, name, details if details else None)

def complete_task(task_id: str, success: bool = True, **kwargs):
    """סיום משימה - helper function"""
    return tracker.complete_task(task_id, success, **kwargs)

def add_created_file(task_id: str, file_path: str):
    """הוספת קובץ שנוצר"""
    return tracker.add_file_created(task_id, file_path)

def add_modified_file(task_id: str, file_path: str):
    """הוספת קובץ ששונה"""
    return tracker.add_file_modified(task_id, file_path)