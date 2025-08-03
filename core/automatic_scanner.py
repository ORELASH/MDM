#!/usr/bin/env python3
"""
Automatic Database Scanner
Handles periodic scanning of all database servers for user changes
"""

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import os
import logging

class AutomaticScanner:
    """Manages automatic periodic scanning of database servers"""
    
    def __init__(self, scan_interval_hours: int = 4, config_file: str = None):
        self.scan_interval_hours = scan_interval_hours
        self.config_file = config_file or "/home/orel/my_installer/rsm/RedshiftManager/config/scanner_config.json"
        self.servers_file = "/home/orel/my_installer/rsm/RedshiftManager/data/servers.json"
        self.scan_results_dir = "/home/orel/my_installer/rsm/RedshiftManager/data/scan_results"
        
        self.is_running = False
        self.scanner_thread = None
        self.last_scan_time = None
        
        # Initialize directories
        Path(self.scan_results_dir).mkdir(parents=True, exist_ok=True)
        Path(os.path.dirname(self.config_file)).mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.load_config()
    
    def load_config(self):
        """Load scanner configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.scan_interval_hours = config.get('scan_interval_hours', 4)
                    self.last_scan_time = config.get('last_scan_time')
                    if self.last_scan_time:
                        self.last_scan_time = datetime.fromisoformat(self.last_scan_time)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self.save_config()
    
    def save_config(self):
        """Save scanner configuration"""
        try:
            config = {
                'scan_interval_hours': self.scan_interval_hours,
                'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
                'created_at': datetime.now().isoformat()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def load_servers(self) -> List[Dict]:
        """Load server configurations"""
        try:
            if os.path.exists(self.servers_file):
                with open(self.servers_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Error loading servers: {e}")
            return []
    
    def scan_server_users(self, server_info: Dict) -> Tuple[bool, List[Dict]]:
        """Scan a single server for users"""
        try:
            # Import here to avoid circular imports
            from ui.open_dashboard import execute_sql_command
            
            server_name = server_info.get('name', f"{server_info['Host']}:{server_info['Port']}")
            self.logger.info(f"Scanning server: {server_name}")
            
            # Determine database type
            port = server_info['Port']
            if port == 5432:
                db_type = "postgresql"
            elif port == 5439:
                db_type = "redshift"
            elif port == 3306:
                db_type = "mysql"
            else:
                db_type = "generic"
            
            users = []
            
            # Get users based on database type
            if db_type in ["postgresql", "redshift"]:
                sql = """
                    SELECT usename as username, 
                           usesysid as user_id,
                           usesuper as is_superuser,
                           usecreatedb as can_create_db,
                           valuntil as password_expiry
                    FROM pg_user 
                    ORDER BY usename;
                """
            elif db_type == "mysql":
                sql = """
                    SELECT User as username,
                           Host as host,
                           account_locked as is_locked,
                           password_expired as password_expired
                    FROM mysql.user 
                    ORDER BY User;
                """
            else:
                return False, []
            
            success, result = execute_sql_command(server_info, sql, fetch_results=True)
            
            if success and result:
                for row in result:
                    user_data = {
                        'username': row[0],
                        'server_name': server_name,
                        'database_type': db_type,
                        'scan_time': datetime.now().isoformat(),
                        'raw_data': dict(zip([desc[0] for desc in result.description] if hasattr(result, 'description') else [], row))
                    }
                    users.append(user_data)
            
            return True, users
            
        except Exception as e:
            self.logger.error(f"Error scanning server {server_info.get('name', 'unknown')}: {e}")
            return False, []
    
    def compare_scan_results(self, current_users: List[Dict], previous_users: List[Dict]) -> Dict:
        """Compare current scan with previous scan to find changes"""
        changes = {
            'new_users': [],
            'removed_users': [],
            'modified_users': [],
            'unchanged_users': []
        }
        
        # Create lookup dictionaries
        current_lookup = {f"{u['server_name']}:{u['username'].lower()}": u for u in current_users}
        previous_lookup = {f"{u['server_name']}:{u['username'].lower()}": u for u in previous_users}
        
        # Find new users
        for key, user in current_lookup.items():
            if key not in previous_lookup:
                changes['new_users'].append(user)
            else:
                # Check for modifications (simplified - could be more detailed)
                prev_user = previous_lookup[key]
                if user.get('raw_data') != prev_user.get('raw_data'):
                    changes['modified_users'].append({
                        'current': user,
                        'previous': prev_user
                    })
                else:
                    changes['unchanged_users'].append(user)
        
        # Find removed users
        for key, user in previous_lookup.items():
            if key not in current_lookup:
                changes['removed_users'].append(user)
        
        return changes
    
    def save_scan_results(self, scan_results: Dict):
        """Save scan results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scan_{timestamp}.json"
        filepath = os.path.join(self.scan_results_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(scan_results, f, indent=2, ensure_ascii=False, default=str)
            
            # Also save as latest scan
            latest_filepath = os.path.join(self.scan_results_dir, "latest_scan.json")
            with open(latest_filepath, 'w', encoding='utf-8') as f:
                json.dump(scan_results, f, indent=2, ensure_ascii=False, default=str)
                
            self.logger.info(f"Scan results saved to: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving scan results: {e}")
    
    def load_previous_scan(self) -> Optional[Dict]:
        """Load the most recent previous scan results"""
        try:
            latest_filepath = os.path.join(self.scan_results_dir, "latest_scan.json")
            if os.path.exists(latest_filepath):
                with open(latest_filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading previous scan: {e}")
            return None
    
    def perform_full_scan(self) -> Dict:
        """Perform a full scan of all configured servers"""
        self.logger.info("Starting full database scan...")
        
        servers = self.load_servers()
        if not servers:
            self.logger.warning("No servers configured for scanning")
            return {'servers': [], 'total_users': 0, 'scan_time': datetime.now().isoformat()}
        
        scan_results = {
            'scan_time': datetime.now().isoformat(),
            'servers': [],
            'total_users': 0,
            'scan_summary': {
                'servers_scanned': 0,
                'servers_failed': 0,
                'total_users_found': 0
            }
        }
        
        all_users = []
        
        for server in servers:
            server_result = {
                'server_info': server,
                'scan_success': False,
                'users': [],
                'error_message': None
            }
            
            try:
                success, users = self.scan_server_users(server)
                server_result['scan_success'] = success
                server_result['users'] = users
                
                if success:
                    scan_results['scan_summary']['servers_scanned'] += 1
                    scan_results['scan_summary']['total_users_found'] += len(users)
                    all_users.extend(users)
                else:
                    scan_results['scan_summary']['servers_failed'] += 1
                    server_result['error_message'] = "Failed to scan server"
                    
            except Exception as e:
                scan_results['scan_summary']['servers_failed'] += 1
                server_result['error_message'] = str(e)
                self.logger.error(f"Error scanning server {server.get('name', 'unknown')}: {e}")
            
            scan_results['servers'].append(server_result)
        
        scan_results['total_users'] = len(all_users)
        scan_results['all_users'] = all_users
        
        # Compare with previous scan
        previous_scan = self.load_previous_scan()
        if previous_scan:
            changes = self.compare_scan_results(
                all_users, 
                previous_scan.get('all_users', [])
            )
            scan_results['changes'] = changes
            
            # Create notifications for changes
            self._create_change_notifications(changes, scan_results['scan_time'])
            
            # Log significant changes
            if changes['new_users']:
                self.logger.info(f"Found {len(changes['new_users'])} new users")
            if changes['removed_users']:
                self.logger.info(f"Found {len(changes['removed_users'])} removed users")
            if changes['modified_users']:
                self.logger.info(f"Found {len(changes['modified_users'])} modified users")
        
        # Save results
        self.save_scan_results(scan_results)
        
        # Update last scan time
        self.last_scan_time = datetime.now()
        self.save_config()
        
        self.logger.info(f"Scan completed. Found {len(all_users)} users across {len(servers)} servers")
        
        return scan_results
    
    def _create_change_notifications(self, changes: Dict, scan_time: str):
        """Create notifications for detected changes"""
        try:
            from core.notification_system import get_notification_system
            from core.user_correlation import get_correlation_engine
            from models.local_user_storage import LocalUserStorage
            
            notification_system = get_notification_system()
            correlation_engine = get_correlation_engine()
            local_storage = LocalUserStorage()
            
            # Get existing users for correlation
            existing_users = local_storage.get_all_users()
            
            # Create notifications for new users with correlation
            for user in changes.get('new_users', []):
                # Find potential matches
                matches = correlation_engine.find_potential_matches(user, existing_users)
                
                if matches and matches[0][1] >= 0.4:  # If we have decent matches
                    # Create correlation request
                    potential_matches = [match[0] for match in matches[:3]]
                    confidence_scores = {str(i): match[1] for i, match in enumerate(matches[:3])}
                    
                    notification_system.create_correlation_request(
                        user, potential_matches, user.get('server_name', 'Unknown'), confidence_scores
                    )
                else:
                    # Create standard new user notification
                    notification_system.create_user_change_notification(
                        'new_user', user, user.get('server_name', 'Unknown'), scan_time
                    )
            
            # Create notifications for removed users
            for user in changes.get('removed_users', []):
                notification_system.create_user_change_notification(
                    'removed_user', user, user.get('server_name', 'Unknown'), scan_time
                )
            
            # Create notifications for modified users
            for change in changes.get('modified_users', []):
                current_user = change.get('current', {})
                notification_system.create_user_change_notification(
                    'modified_user', current_user, current_user.get('server_name', 'Unknown'), scan_time
                )
                
        except Exception as e:
            self.logger.error(f"Error creating change notifications: {e}")
    
    def should_scan(self) -> bool:
        """Check if it's time for the next scan"""
        if not self.last_scan_time:
            return True
        
        time_since_last = datetime.now() - self.last_scan_time
        return time_since_last >= timedelta(hours=self.scan_interval_hours)
    
    def scanner_loop(self):
        """Main scanner loop that runs in a separate thread"""
        self.logger.info(f"Scanner started with {self.scan_interval_hours} hour interval")
        
        while self.is_running:
            try:
                if self.should_scan():
                    self.perform_full_scan()
                
                # Sleep for 10 minutes before checking again
                time.sleep(600)  # 10 minutes
                
            except Exception as e:
                self.logger.error(f"Error in scanner loop: {e}")
                time.sleep(600)  # Wait 10 minutes before retrying
    
    def start_scanner(self):
        """Start the automatic scanner"""
        if self.is_running:
            self.logger.warning("Scanner is already running")
            return
        
        self.is_running = True
        self.scanner_thread = threading.Thread(target=self.scanner_loop, daemon=True)
        self.scanner_thread.start()
        self.logger.info("Automatic scanner started")
    
    def stop_scanner(self):
        """Stop the automatic scanner"""
        if not self.is_running:
            self.logger.warning("Scanner is not running")
            return
        
        self.is_running = False
        if self.scanner_thread and self.scanner_thread.is_alive():
            self.scanner_thread.join(timeout=5)
        self.logger.info("Automatic scanner stopped")
    
    def get_scanner_status(self) -> Dict:
        """Get current scanner status"""
        return {
            'is_running': self.is_running,
            'scan_interval_hours': self.scan_interval_hours,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'next_scan_due': (self.last_scan_time + timedelta(hours=self.scan_interval_hours)).isoformat() if self.last_scan_time else "Now",
            'should_scan_now': self.should_scan()
        }
    
    def get_recent_scans(self, limit: int = 10) -> List[Dict]:
        """Get recent scan results"""
        try:
            scan_files = []
            for filename in os.listdir(self.scan_results_dir):
                if filename.startswith('scan_') and filename.endswith('.json'):
                    filepath = os.path.join(self.scan_results_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    scan_files.append((mtime, filepath, filename))
            
            # Sort by modification time, newest first
            scan_files.sort(reverse=True)
            
            recent_scans = []
            for _, filepath, filename in scan_files[:limit]:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        scan_data = json.load(f)
                        recent_scans.append({
                            'filename': filename,
                            'scan_time': scan_data.get('scan_time'),
                            'total_users': scan_data.get('total_users', 0),
                            'servers_scanned': scan_data.get('scan_summary', {}).get('servers_scanned', 0),
                            'has_changes': bool(scan_data.get('changes', {}).get('new_users') or 
                                             scan_data.get('changes', {}).get('removed_users') or 
                                             scan_data.get('changes', {}).get('modified_users'))
                        })
                except Exception as e:
                    self.logger.error(f"Error reading scan file {filename}: {e}")
            
            return recent_scans
            
        except Exception as e:
            self.logger.error(f"Error getting recent scans: {e}")
            return []
    
    def get_scan_details(self, filename: str) -> Optional[Dict]:
        """Get detailed results for a specific scan"""
        try:
            filepath = os.path.join(self.scan_results_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading scan details for {filename}: {e}")
            return None

# Global scanner instance
_scanner_instance = None

def get_scanner_instance() -> AutomaticScanner:
    """Get the global scanner instance"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = AutomaticScanner()
    return _scanner_instance