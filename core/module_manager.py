#!/usr/bin/env python3
"""
Real Module Manager - Manages actual system modules
No mock data, no simulation - real functionality only
"""

import os
import sys
import json
import sqlite3
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

class ModuleManager:
    """Real module management system"""
    
    def __init__(self, modules_dir: str = "modules", db_path: str = "data/multidb_manager.db"):
        self.modules_dir = Path(modules_dir)
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._ensure_modules_table()
        
    def _ensure_modules_table(self):
        """Create modules table if it doesn't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS installed_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    version TEXT NOT NULL,
                    module_type TEXT NOT NULL DEFAULT 'extension',
                    status TEXT NOT NULL DEFAULT 'active',
                    description TEXT,
                    author TEXT,
                    dependencies TEXT, -- JSON array
                    config_schema TEXT, -- JSON schema
                    install_path TEXT NOT NULL,
                    installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_loaded_at DATETIME,
                    load_errors TEXT,
                    metadata JSON
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS module_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    config_key TEXT NOT NULL,
                    config_value TEXT NOT NULL,
                    data_type TEXT DEFAULT 'string',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (module_name) REFERENCES installed_modules(name) ON DELETE CASCADE,
                    UNIQUE(module_name, config_key)
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to create modules table: {e}")
    
    def discover_modules(self) -> List[Dict[str, Any]]:
        """Discover all modules in the modules directory"""
        discovered = []
        
        if not self.modules_dir.exists():
            self.logger.warning(f"Modules directory {self.modules_dir} does not exist")
            return discovered
            
        for module_path in self.modules_dir.iterdir():
            if module_path.is_dir() and not module_path.name.startswith('.'):
                module_info = self._load_module_info(module_path)
                if module_info:
                    discovered.append(module_info)
                    
        return discovered
    
    def _load_module_info(self, module_path: Path) -> Optional[Dict[str, Any]]:
        """Load module information from module.json"""
        try:
            module_json = module_path / "module.json"
            if not module_json.exists():
                self.logger.warning(f"No module.json found in {module_path}")
                return None
                
            with open(module_json, 'r', encoding='utf-8') as f:
                info = json.load(f)
                
            # Add computed fields
            info['install_path'] = str(module_path)
            info['is_installed'] = self._is_module_installed(info['name'])
            info['is_loadable'] = self._check_module_loadable(module_path, info)
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to load module info from {module_path}: {e}")
            return None
    
    def _is_module_installed(self, module_name: str) -> bool:
        """Check if module is registered as installed"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM installed_modules WHERE name = ?", (module_name,))
            result = cursor.fetchone() is not None
            conn.close()
            return result
        except Exception:
            return False
    
    def _check_module_loadable(self, module_path: Path, info: Dict[str, Any]) -> bool:
        """Check if module can be loaded (dependencies, main file exists)"""
        try:
            # Check main file exists
            main_file = info.get('main_file', '__init__.py')
            if not (module_path / main_file).exists():
                return False
                
            # Check dependencies
            dependencies = info.get('dependencies', [])
            for dep in dependencies:
                try:
                    importlib.import_module(dep)
                except ImportError:
                    return False
                    
            return True
            
        except Exception:
            return False
    
    def install_module(self, module_name: str) -> Dict[str, Any]:
        """Install a discovered module"""
        try:
            # Find module in discovered modules
            discovered = self.discover_modules()
            module_info = None
            for mod in discovered:
                if mod['name'] == module_name:
                    module_info = mod
                    break
                    
            if not module_info:
                return {"success": False, "error": f"Module {module_name} not found"}
                
            if module_info['is_installed']:
                return {"success": False, "error": f"Module {module_name} already installed"}
                
            if not module_info['is_loadable']:
                return {"success": False, "error": f"Module {module_name} is not loadable (missing dependencies or files)"}
            
            # Register in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO installed_modules 
                (name, version, module_type, status, description, author, dependencies, install_path, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                module_info['name'],
                module_info['version'],
                module_info.get('type', 'extension'),
                'active',
                module_info.get('description', ''),
                module_info.get('author', ''),
                json.dumps(module_info.get('dependencies', [])),
                module_info['install_path'],
                json.dumps(module_info)
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Module {module_name} installed successfully")
            return {"success": True, "message": f"Module {module_name} installed"}
            
        except Exception as e:
            self.logger.error(f"Failed to install module {module_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def uninstall_module(self, module_name: str) -> Dict[str, Any]:
        """Uninstall a module"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if module exists
            cursor.execute("SELECT id FROM installed_modules WHERE name = ?", (module_name,))
            if not cursor.fetchone():
                conn.close()
                return {"success": False, "error": f"Module {module_name} not installed"}
            
            # Remove from database
            cursor.execute("DELETE FROM installed_modules WHERE name = ?", (module_name,))
            cursor.execute("DELETE FROM module_configs WHERE module_name = ?", (module_name,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Module {module_name} uninstalled successfully")
            return {"success": True, "message": f"Module {module_name} uninstalled"}
            
        except Exception as e:
            self.logger.error(f"Failed to uninstall module {module_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_installed_modules(self) -> List[Dict[str, Any]]:
        """Get all installed modules"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM installed_modules 
                ORDER BY name
            """)
            
            modules = []
            for row in cursor.fetchall():
                module = dict(row)
                module['dependencies'] = json.loads(module['dependencies'] or '[]')
                module['metadata'] = json.loads(module['metadata'] or '{}')
                modules.append(module)
                
            conn.close()
            return modules
            
        except Exception as e:
            self.logger.error(f"Failed to get installed modules: {e}")
            return []
    
    def get_module_status(self, module_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific module"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM installed_modules WHERE name = ?", (module_name,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return {"exists": False, "error": "Module not found"}
                
            module = dict(row)
            module['dependencies'] = json.loads(module['dependencies'] or '[]')
            module['metadata'] = json.loads(module['metadata'] or '{}')
            
            # Check if module is still loadable
            module_path = Path(module['install_path'])
            module['is_loadable'] = self._check_module_loadable(module_path, module['metadata'])
            
            # Get configuration
            cursor.execute("SELECT * FROM module_configs WHERE module_name = ?", (module_name,))
            configs = [dict(row) for row in cursor.fetchall()]
            module['configs'] = configs
            
            conn.close()
            
            module['exists'] = True
            return module
            
        except Exception as e:
            self.logger.error(f"Failed to get module status for {module_name}: {e}")
            return {"exists": False, "error": str(e)}
    
    def update_module_status(self, module_name: str, status: str) -> Dict[str, Any]:
        """Update module status (active, disabled, error)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE installed_modules 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE name = ?
            """, (status, module_name))
            
            if cursor.rowcount == 0:
                conn.close()
                return {"success": False, "error": f"Module {module_name} not found"}
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": f"Module {module_name} status updated to {status}"}
            
        except Exception as e:
            self.logger.error(f"Failed to update module status: {e}")
            return {"success": False, "error": str(e)}
    
    def set_module_config(self, module_name: str, config_key: str, config_value: Any, data_type: str = "string") -> Dict[str, Any]:
        """Set module configuration value"""
        try:
            # Validate module exists
            if not self._is_module_installed(module_name):
                return {"success": False, "error": f"Module {module_name} not installed"}
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert value to string for storage
            if data_type == "json":
                value_str = json.dumps(config_value)
            else:
                value_str = str(config_value)
            
            cursor.execute("""
                INSERT OR REPLACE INTO module_configs 
                (module_name, config_key, config_value, data_type, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (module_name, config_key, value_str, data_type))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": f"Configuration {config_key} set for module {module_name}"}
            
        except Exception as e:
            self.logger.error(f"Failed to set module config: {e}")
            return {"success": False, "error": str(e)}
    
    def get_module_config(self, module_name: str, config_key: str = None) -> Dict[str, Any]:
        """Get module configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if config_key:
                cursor.execute("""
                    SELECT * FROM module_configs 
                    WHERE module_name = ? AND config_key = ?
                """, (module_name, config_key))
                row = cursor.fetchone()
                
                if not row:
                    conn.close()
                    return {"success": False, "error": f"Config {config_key} not found for module {module_name}"}
                
                config = dict(row)
                # Parse value based on data type
                if config['data_type'] == 'json':
                    config['parsed_value'] = json.loads(config['config_value'])
                elif config['data_type'] == 'boolean':
                    config['parsed_value'] = config['config_value'].lower() == 'true'
                elif config['data_type'] == 'integer':
                    config['parsed_value'] = int(config['config_value'])
                elif config['data_type'] == 'float':
                    config['parsed_value'] = float(config['config_value'])
                else:
                    config['parsed_value'] = config['config_value']
                
                conn.close()
                return {"success": True, "config": config}
            else:
                cursor.execute("""
                    SELECT * FROM module_configs 
                    WHERE module_name = ?
                    ORDER BY config_key
                """, (module_name,))
                
                configs = {}
                for row in cursor.fetchall():
                    config = dict(row)
                    key = config['config_key']
                    
                    # Parse value based on data type
                    if config['data_type'] == 'json':
                        configs[key] = json.loads(config['config_value'])
                    elif config['data_type'] == 'boolean':
                        configs[key] = config['config_value'].lower() == 'true'
                    elif config['data_type'] == 'integer':
                        configs[key] = int(config['config_value'])
                    elif config['data_type'] == 'float':
                        configs[key] = float(config['config_value'])
                    else:
                        configs[key] = config['config_value']
                
                conn.close()
                return {"success": True, "configs": configs}
                
        except Exception as e:
            self.logger.error(f"Failed to get module config: {e}")
            return {"success": False, "error": str(e)}
    
    def load_module(self, module_name: str) -> Dict[str, Any]:
        """Dynamically load a module"""
        try:
            module_info = self.get_module_status(module_name)
            if not module_info.get('exists'):
                return {"success": False, "error": f"Module {module_name} not installed"}
                
            if not module_info['is_loadable']:
                return {"success": False, "error": f"Module {module_name} is not loadable"}
            
            module_path = Path(module_info['install_path'])
            main_file = module_info['metadata'].get('main_file', '__init__.py')
            
            # Add module path to sys.path if not already there
            module_path_str = str(module_path.parent)
            if module_path_str not in sys.path:
                sys.path.insert(0, module_path_str)
            
            # Load the module
            spec = importlib.util.spec_from_file_location(
                module_name, 
                module_path / main_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Update last loaded time
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE installed_modules 
                SET last_loaded_at = CURRENT_TIMESTAMP, load_errors = NULL 
                WHERE name = ?
            """, (module_name,))
            conn.commit()
            conn.close()
            
            return {"success": True, "module": module, "message": f"Module {module_name} loaded successfully"}
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Failed to load module {module_name}: {e}")
            
            # Record load error
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE installed_modules 
                    SET load_errors = ?, status = 'error' 
                    WHERE name = ?
                """, (error_msg, module_name))
                conn.commit()
                conn.close()
            except:
                pass
                
            return {"success": False, "error": error_msg}
    
    def get_module_dependencies(self, module_name: str) -> Dict[str, Any]:
        """Get module dependency information"""
        try:
            module_info = self.get_module_status(module_name)
            if not module_info.get('exists'):
                return {"success": False, "error": f"Module {module_name} not found"}
            
            dependencies = module_info.get('dependencies', [])
            dependency_status = {}
            
            for dep in dependencies:
                try:
                    importlib.import_module(dep)
                    dependency_status[dep] = {"available": True, "error": None}
                except ImportError as e:
                    dependency_status[dep] = {"available": False, "error": str(e)}
            
            return {
                "success": True,
                "module": module_name,
                "dependencies": dependencies,
                "dependency_status": dependency_status,
                "all_available": all(status["available"] for status in dependency_status.values())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get dependencies for {module_name}: {e}")
            return {"success": False, "error": str(e)}