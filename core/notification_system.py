#!/usr/bin/env python3
"""
Notification and Approval System
Handles notifications, approvals, and user correlation for manual changes
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from enum import Enum
import uuid
import logging

class NotificationType(Enum):
    NEW_USER_DETECTED = "new_user_detected"
    USER_REMOVED = "user_removed"
    USER_MODIFIED = "user_modified"
    CORRELATION_REQUEST = "correlation_request"
    SYSTEM_ALERT = "system_alert"

class NotificationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISMISSED = "dismissed"
    EXPIRED = "expired"

class ApprovalType(Enum):
    USER_CORRELATION = "user_correlation"
    IMPORT_USER = "import_user"
    MANAGE_USER = "manage_user"
    IGNORE_USER = "ignore_user"

class NotificationSystem:
    """Manages notifications, approvals, and user correlations"""
    
    def __init__(self, notifications_dir: str = None):
        self.notifications_dir = notifications_dir or "/home/orel/my_installer/rsm/RedshiftManager/data/notifications"
        self.pending_notifications_file = os.path.join(self.notifications_dir, "pending_notifications.json")
        self.notification_history_file = os.path.join(self.notifications_dir, "notification_history.json")
        self.user_correlations_file = os.path.join(self.notifications_dir, "user_correlations.json")
        
        # Initialize directories
        Path(self.notifications_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize data files
        self._init_data_files()
    
    def _init_data_files(self):
        """Initialize data files if they don't exist"""
        for file_path in [self.pending_notifications_file, self.notification_history_file, self.user_correlations_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
    
    def create_notification(self, notification_type: NotificationType, title: str, message: str, 
                          data: Dict = None, priority: str = "medium", expires_hours: int = 168) -> str:
        """Create a new notification"""
        notification_id = str(uuid.uuid4())
        
        notification = {
            'id': notification_id,
            'type': notification_type.value,
            'title': title,
            'message': message,
            'data': data or {},
            'priority': priority,  # low, medium, high, critical
            'status': NotificationStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=expires_hours)).isoformat(),
            'actions': [],  # Available actions for this notification
            'responses': []  # User responses/actions taken
        }
        
        # Add to pending notifications
        pending = self._load_pending_notifications()
        pending.append(notification)
        self._save_pending_notifications(pending)
        
        self.logger.info(f"Created notification: {notification_id} - {title}")
        return notification_id
    
    def create_user_change_notification(self, change_type: str, user_data: Dict, 
                                      server_name: str, scan_time: str) -> str:
        """Create notification for user changes detected in scan"""
        change_messages = {
            'new_user': 'נמצא משתמש חדש במערכת',
            'removed_user': 'משתמש הוסר מהמערכת',
            'modified_user': 'משתמש שונה במערכת'
        }
        
        notification_types = {
            'new_user': NotificationType.NEW_USER_DETECTED,
            'removed_user': NotificationType.USER_REMOVED,
            'modified_user': NotificationType.USER_MODIFIED
        }
        
        title = f"{change_messages.get(change_type, 'שינוי במשתמש')} - {user_data.get('username', 'Unknown')}"
        message = (f"נמצא שינוי במשתמש {user_data.get('username', 'Unknown')} "
                  f"בשרת {server_name} בסריקה מתאריך {scan_time}")
        
        # Define available actions based on change type
        actions = []
        if change_type == 'new_user':
            actions = [
                {'id': 'import_user', 'label': 'ייבא למערכת', 'type': 'primary'},
                {'id': 'correlate_user', 'label': 'שייך למשתמש קיים', 'type': 'secondary'},
                {'id': 'ignore_user', 'label': 'התעלם', 'type': 'default'},
                {'id': 'dismiss', 'label': 'סגור התראה', 'type': 'default'}
            ]
        elif change_type == 'removed_user':
            actions = [
                {'id': 'confirm_removal', 'label': 'אשר הסרה', 'type': 'primary'},
                {'id': 'investigate', 'label': 'חקור', 'type': 'secondary'},
                {'id': 'dismiss', 'label': 'סגור התראה', 'type': 'default'}
            ]
        elif change_type == 'modified_user':
            actions = [
                {'id': 'sync_changes', 'label': 'סנכרן שינויים', 'type': 'primary'},
                {'id': 'review_changes', 'label': 'בדוק שינויים', 'type': 'secondary'},
                {'id': 'dismiss', 'label': 'סגור התראה', 'type': 'default'}
            ]
        
        data = {
            'change_type': change_type,
            'user_data': user_data,
            'server_name': server_name,
            'scan_time': scan_time,
            'database_type': user_data.get('database_type', 'unknown')
        }
        
        notification_id = self.create_notification(
            notification_types.get(change_type, NotificationType.SYSTEM_ALERT),
            title, message, data, priority="high"
        )
        
        # Update notification with actions
        self.update_notification_actions(notification_id, actions)
        
        return notification_id
    
    def create_correlation_request(self, new_user: Dict, potential_matches: List[Dict], 
                                 server_name: str, confidence_scores: Dict = None) -> str:
        """Create a user correlation request notification"""
        username = new_user.get('username', 'Unknown')
        title = f"בקשת שיוך משתמש - {username}"
        
        if potential_matches:
            match_names = [m.get('username', 'Unknown') for m in potential_matches[:3]]
            message = f"נמצא משתמש חדש {username} בשרת {server_name}. התאמות אפשריות: {', '.join(match_names)}"
        else:
            message = f"נמצא משתמש חדש {username} בשרת {server_name}. לא נמצאו התאמות אוטומטיות."
        
        actions = [
            {'id': 'approve_correlation', 'label': 'אשר שיוך', 'type': 'primary'},
            {'id': 'create_new_user', 'label': 'צור משתמש חדש', 'type': 'secondary'},
            {'id': 'manual_correlation', 'label': 'שיוך ידני', 'type': 'secondary'},
            {'id': 'ignore', 'label': 'התעלם', 'type': 'default'}
        ]
        
        data = {
            'new_user': new_user,
            'potential_matches': potential_matches,
            'server_name': server_name,
            'confidence_scores': confidence_scores or {},
            'correlation_type': 'automatic' if potential_matches else 'manual'
        }
        
        notification_id = self.create_notification(
            NotificationType.CORRELATION_REQUEST,
            title, message, data, priority="high"
        )
        
        self.update_notification_actions(notification_id, actions)
        return notification_id
    
    def update_notification_actions(self, notification_id: str, actions: List[Dict]):
        """Update available actions for a notification"""
        pending = self._load_pending_notifications()
        
        for notification in pending:
            if notification['id'] == notification_id:
                notification['actions'] = actions
                break
        
        self._save_pending_notifications(pending)
    
    def respond_to_notification(self, notification_id: str, action_id: str, 
                              response_data: Dict = None, user_id: str = "system") -> bool:
        """Respond to a notification with an action"""
        pending = self._load_pending_notifications()
        notification = None
        
        # Find the notification
        for notif in pending:
            if notif['id'] == notification_id:
                notification = notif
                break
        
        if not notification:
            self.logger.error(f"Notification {notification_id} not found")
            return False
        
        # Add response
        response = {
            'action_id': action_id,
            'response_data': response_data or {},
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        notification['responses'].append(response)
        
        # Process the action
        success = self._process_notification_action(notification, action_id, response_data)
        
        if success:
            # Update status based on action
            if action_id in ['dismiss', 'ignore']:
                notification['status'] = NotificationStatus.DISMISSED.value
            elif action_id in ['approve_correlation', 'import_user', 'confirm_removal', 'sync_changes']:
                notification['status'] = NotificationStatus.APPROVED.value
            elif action_id == 'reject':
                notification['status'] = NotificationStatus.REJECTED.value
            
            # Move to history if completed
            if notification['status'] != NotificationStatus.PENDING.value:
                self._move_to_history(notification)
                pending = [n for n in pending if n['id'] != notification_id]
            
            self._save_pending_notifications(pending)
            
            self.logger.info(f"Processed action {action_id} for notification {notification_id}")
            return True
        
        return False
    
    def _process_notification_action(self, notification: Dict, action_id: str, response_data: Dict) -> bool:
        """Process a specific notification action"""
        try:
            notification_type = notification.get('type')
            data = notification.get('data', {})
            
            if action_id == 'import_user':
                return self._process_import_user(data, response_data)
            elif action_id == 'correlate_user':
                return self._process_correlate_user(data, response_data)
            elif action_id == 'approve_correlation':
                return self._process_approve_correlation(data, response_data)
            elif action_id == 'sync_changes':
                return self._process_sync_changes(data, response_data)
            elif action_id in ['dismiss', 'ignore']:
                return True  # Always succeed for dismiss/ignore
            else:
                self.logger.warning(f"Unknown action: {action_id}")
                return True  # Don't fail for unknown actions
                
        except Exception as e:
            self.logger.error(f"Error processing action {action_id}: {e}")
            return False
    
    def _process_import_user(self, notification_data: Dict, response_data: Dict) -> bool:
        """Process importing a new user into the system"""
        try:
            # This would integrate with the UserSyncManager
            user_data = notification_data.get('user_data', {})
            server_name = notification_data.get('server_name')
            
            self.logger.info(f"Importing user {user_data.get('username')} from {server_name}")
            
            # Here you would call the actual import logic
            # from core.user_sync_manager import UserSyncManager
            # sync_manager = UserSyncManager()
            # return sync_manager.import_user_from_notification(user_data, server_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing user: {e}")
            return False
    
    def _process_correlate_user(self, notification_data: Dict, response_data: Dict) -> bool:
        """Process user correlation"""
        try:
            new_user = notification_data.get('user_data', {})
            target_user_id = response_data.get('target_user_id')
            
            if not target_user_id:
                return False
            
            # Save correlation
            correlation = {
                'id': str(uuid.uuid4()),
                'new_user': new_user,
                'target_user_id': target_user_id,
                'server_name': notification_data.get('server_name'),
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            correlations = self._load_user_correlations()
            correlations.append(correlation)
            self._save_user_correlations(correlations)
            
            self.logger.info(f"Correlated user {new_user.get('username')} with user ID {target_user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error correlating user: {e}")
            return False
    
    def _process_approve_correlation(self, notification_data: Dict, response_data: Dict) -> bool:
        """Process approval of automatic correlation"""
        try:
            # Get the selected match
            selected_match_index = response_data.get('selected_match_index', 0)
            potential_matches = notification_data.get('potential_matches', [])
            
            if selected_match_index < len(potential_matches):
                selected_match = potential_matches[selected_match_index]
                return self._process_correlate_user(
                    notification_data, 
                    {'target_user_id': selected_match.get('id')}
                )
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error approving correlation: {e}")
            return False
    
    def _process_sync_changes(self, notification_data: Dict, response_data: Dict) -> bool:
        """Process syncing user changes"""
        try:
            user_data = notification_data.get('user_data', {})
            server_name = notification_data.get('server_name')
            
            self.logger.info(f"Syncing changes for user {user_data.get('username')} from {server_name}")
            
            # Here you would call the actual sync logic
            return True
            
        except Exception as e:
            self.logger.error(f"Error syncing changes: {e}")
            return False
    
    def get_pending_notifications(self, priority_filter: str = None, 
                                type_filter: str = None) -> List[Dict]:
        """Get pending notifications with optional filters"""
        notifications = self._load_pending_notifications()
        
        # Remove expired notifications
        current_time = datetime.now()
        active_notifications = []
        
        for notification in notifications:
            expires_at = datetime.fromisoformat(notification['expires_at'])
            if expires_at > current_time:
                active_notifications.append(notification)
            else:
                # Mark as expired and move to history
                notification['status'] = NotificationStatus.EXPIRED.value
                self._move_to_history(notification)
        
        # Save cleaned up notifications
        self._save_pending_notifications(active_notifications)
        
        # Apply filters
        filtered_notifications = active_notifications
        
        if priority_filter:
            filtered_notifications = [n for n in filtered_notifications 
                                    if n.get('priority') == priority_filter]
        
        if type_filter:
            filtered_notifications = [n for n in filtered_notifications 
                                    if n.get('type') == type_filter]
        
        # Sort by priority and creation time
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        filtered_notifications.sort(
            key=lambda n: (priority_order.get(n.get('priority', 'medium'), 2), 
                          n.get('created_at')), 
            reverse=True
        )
        
        return filtered_notifications
    
    def get_notification_by_id(self, notification_id: str) -> Optional[Dict]:
        """Get a specific notification by ID"""
        # Check pending notifications
        pending = self._load_pending_notifications()
        for notification in pending:
            if notification['id'] == notification_id:
                return notification
        
        # Check history
        history = self._load_notification_history()
        for notification in history:
            if notification['id'] == notification_id:
                return notification
        
        return None
    
    def get_notification_statistics(self) -> Dict:
        """Get notification system statistics"""
        pending = self._load_pending_notifications()
        history = self._load_notification_history()
        
        # Count by status
        status_counts = {}
        for notification in pending:
            status = notification.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for notification in history:
            status = notification.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by priority
        priority_counts = {}
        for notification in pending:
            priority = notification.get('priority', 'medium')
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Count by type
        type_counts = {}
        for notification in pending + history[-100:]:  # Last 100 historical
            notif_type = notification.get('type', 'unknown')
            type_counts[notif_type] = type_counts.get(notif_type, 0) + 1
        
        return {
            'total_pending': len(pending),
            'total_processed': len(history),
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'type_counts': type_counts,
            'last_notification': pending[0]['created_at'] if pending else None
        }
    
    def cleanup_old_notifications(self, days_to_keep: int = 30):
        """Clean up old notifications from history"""
        history = self._load_notification_history()
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        cleaned_history = []
        for notification in history:
            created_at = datetime.fromisoformat(notification['created_at'])
            if created_at > cutoff_date:
                cleaned_history.append(notification)
        
        self._save_notification_history(cleaned_history)
        
        removed_count = len(history) - len(cleaned_history)
        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old notifications")
    
    def _move_to_history(self, notification: Dict):
        """Move a notification to history"""
        history = self._load_notification_history()
        notification['completed_at'] = datetime.now().isoformat()
        history.append(notification)
        self._save_notification_history(history)
    
    def _load_pending_notifications(self) -> List[Dict]:
        """Load pending notifications from file"""
        try:
            with open(self.pending_notifications_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_pending_notifications(self, notifications: List[Dict]):
        """Save pending notifications to file"""
        try:
            with open(self.pending_notifications_file, 'w', encoding='utf-8') as f:
                json.dump(notifications, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"Error saving pending notifications: {e}")
    
    def _load_notification_history(self) -> List[Dict]:
        """Load notification history from file"""
        try:
            with open(self.notification_history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_notification_history(self, history: List[Dict]):
        """Save notification history to file"""
        try:
            with open(self.notification_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"Error saving notification history: {e}")
    
    def _load_user_correlations(self) -> List[Dict]:
        """Load user correlations from file"""
        try:
            with open(self.user_correlations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_user_correlations(self, correlations: List[Dict]):
        """Save user correlations to file"""
        try:
            with open(self.user_correlations_file, 'w', encoding='utf-8') as f:
                json.dump(correlations, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"Error saving user correlations: {e}")

# Global notification system instance
_notification_system = None

def get_notification_system() -> NotificationSystem:
    """Get the global notification system instance"""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationSystem()
    return _notification_system