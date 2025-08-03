"""
Module Loader for RedshiftManager
Handles loading, instantiation, and lifecycle management of modules.
"""

import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
import logging
import json
import threading
from contextlib import contextmanager

from .plugin_interface import PluginInterface, ModuleManifest, ModuleContext, ModuleStatus
from .module_registry import ModuleRegistry


class ModuleLoadError(Exception):
    """Raised when module loading fails"""
    pass


class ModuleSandbox:
    """Security sandbox for module execution"""
    
    def __init__(self, module_name: str, permissions: List[str]):
        self.module_name = module_name
        self.permissions = permissions
        self.restricted_imports = {
            'os', 'sys', 'subprocess', 'importlib', '__builtin__', 'builtins'
        }
        self.allowed_imports = {
            'datetime', 'json', 're', 'math', 'random', 'uuid', 'hashlib',
            'pandas', 'numpy', 'sqlalchemy', 'streamlit', 'plotly'
        }
        self.logger = logging.getLogger(f"sandbox.{module_name}")
    
    def validate_import(self, module_name: str) -> bool:
        """Validate if module can be imported"""
        if module_name in self.restricted_imports:
            if not self.has_permission('system.import'):
                self.logger.warning(f"Blocked restricted import: {module_name}")
                return False
        
        if module_name in self.allowed_imports:
            return True
        
        # Allow imports from our own project
        if module_name.startswith('models.') or module_name.startswith('utils.'):
            return True
        
        self.logger.warning(f"Unknown import attempted: {module_name}")
        return True  # Allow for now, but log it
    
    def has_permission(self, permission: str) -> bool:
        """Check if sandbox has a specific permission"""
        return permission in self.permissions or 'admin.all' in self.permissions
    
    def create_restricted_globals(self, original_globals: Dict[str, Any]) -> Dict[str, Any]:
        """Create restricted globals for module execution"""
        # Start with safe builtins
        safe_globals = {
            '__builtins__': {
                'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                'min': min, 'max': max, 'sum': sum, 'sorted': sorted,
                'enumerate': enumerate, 'zip': zip, 'range': range,
                'isinstance': isinstance, 'hasattr': hasattr, 'getattr': getattr,
                'print': print  # Allow print for debugging
            }
        }
        
        # Add specific modules if permitted
        if self.has_permission('system.import'):
            safe_globals.update(original_globals)
        else:
            # Only include safe modules
            for key, value in original_globals.items():
                if key.startswith('__') and not key in ['__import__']:
                    safe_globals[key] = value
        
        return safe_globals


class ModuleLoader:
    """
    Handles loading and lifecycle management of modules.
    Provides hot-reload capabilities and security sandboxing.
    """
    
    def __init__(self, registry: ModuleRegistry, core_instance):
        self.registry = registry
        self.core = core_instance
        self.loaded_modules: Dict[str, PluginInterface] = {}
        self.module_locks: Dict[str, threading.Lock] = {}
        self.sandboxes: Dict[str, ModuleSandbox] = {}
        self.logger = logging.getLogger("core.loader")
        
        # Module state tracking
        self.loading_modules: set = set()
        self.failed_modules: Dict[str, str] = {}  # module_name -> error_message
    
    def load_module(self, module_name: str, config_override: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load a module by name.
        Returns True if loading successful, False otherwise.
        """
        if module_name in self.loading_modules:
            self.logger.warning(f"Module {module_name} is already being loaded")
            return False
        
        if module_name in self.loaded_modules:
            self.logger.info(f"Module {module_name} is already loaded")
            return True
        
        # Get module lock
        if module_name not in self.module_locks:
            self.module_locks[module_name] = threading.Lock()
        
        with self.module_locks[module_name]:
            return self._load_module_internal(module_name, config_override)
    
    def _load_module_internal(self, module_name: str, config_override: Optional[Dict[str, Any]]) -> bool:
        """Internal module loading implementation"""
        try:
            self.loading_modules.add(module_name)
            self.registry.set_module_status(module_name, ModuleStatus.LOADING)
            
            # Get module manifest and path
            manifest = self.registry.get_module_manifest(module_name)
            if not manifest:
                raise ModuleLoadError(f"Module {module_name} not found in registry")
            
            module_path = self.registry.get_module_path(module_name)
            if not module_path:
                raise ModuleLoadError(f"Module path not found for {module_name}")
            
            self.logger.info(f"Loading module: {module_name} from {module_path}")
            
            # Load dependencies first
            for dep_name in manifest.required_modules:
                if dep_name not in self.loaded_modules:
                    self.logger.info(f"Loading dependency: {dep_name}")
                    if not self.load_module(dep_name):
                        raise ModuleLoadError(f"Failed to load dependency: {dep_name}")
            
            # Create sandbox
            sandbox = ModuleSandbox(module_name, manifest.grants_permissions)
            self.sandboxes[module_name] = sandbox
            
            # Load module code
            module_instance = self._instantiate_module(manifest, module_path, config_override, sandbox)
            
            # Initialize module
            if not module_instance.initialize():
                raise ModuleLoadError(f"Module {module_name} initialization failed")
            
            # Store loaded module
            self.loaded_modules[module_name] = module_instance
            self.registry.set_module_status(module_name, ModuleStatus.INACTIVE)
            
            # Clear any previous failure record
            if module_name in self.failed_modules:
                del self.failed_modules[module_name]
            
            self.logger.info(f"Successfully loaded module: {module_name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to load module {module_name}: {e}"
            self.logger.error(error_msg)
            self.failed_modules[module_name] = str(e)
            self.registry.set_module_status(module_name, ModuleStatus.ERROR)
            
            # Clean up partial loading
            if module_name in self.loaded_modules:
                del self.loaded_modules[module_name]
            if module_name in self.sandboxes:
                del self.sandboxes[module_name]
            
            return False
            
        finally:
            self.loading_modules.discard(module_name)
    
    def _instantiate_module(self, manifest: ModuleManifest, module_path: str, 
                          config_override: Optional[Dict[str, Any]], sandbox: ModuleSandbox) -> PluginInterface:
        """Instantiate a module from its code"""
        
        # Prepare module configuration
        config = manifest.default_config.copy()
        if config_override:
            config.update(config_override)
        
        # Create module context
        context = ModuleContext(self.core, manifest.name, config)
        
        # Load the module code
        module_file_path = Path(module_path) / "__init__.py"
        if not module_file_path.exists():
            raise ModuleLoadError(f"Module entry point not found: {module_file_path}")
        
        # Create module spec
        spec = importlib.util.spec_from_file_location(
            f"modules.{manifest.name}", 
            module_file_path
        )
        if not spec or not spec.loader:
            raise ModuleLoadError(f"Could not create module spec for {manifest.name}")
        
        # Create and execute module
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules for proper imports
        sys.modules[f"modules.{manifest.name}"] = module
        
        try:
            # Execute module code
            spec.loader.exec_module(module)
            
            # Find the plugin class
            plugin_class = self._find_plugin_class(module, manifest.name)
            
            # Instantiate the plugin
            plugin_instance = plugin_class(manifest, context)
            
            # Validate that it implements PluginInterface
            if not isinstance(plugin_instance, PluginInterface):
                raise ModuleLoadError(f"Module {manifest.name} does not implement PluginInterface")
            
            return plugin_instance
            
        except Exception as e:
            # Clean up sys.modules
            if f"modules.{manifest.name}" in sys.modules:
                del sys.modules[f"modules.{manifest.name}"]
            raise ModuleLoadError(f"Error instantiating module {manifest.name}: {e}")
    
    def _find_plugin_class(self, module, module_name: str) -> Type[PluginInterface]:
        """Find the main plugin class in a module"""
        
        # Look for class with specific names
        for class_name in [f"{module_name.title()}Plugin", f"{module_name.title()}Module", "Plugin", "Module"]:
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                if (isinstance(cls, type) and 
                    issubclass(cls, PluginInterface) and 
                    cls != PluginInterface):
                    return cls
        
        # Look for any class that implements PluginInterface
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, PluginInterface) and 
                obj != PluginInterface):
                return obj
        
        raise ModuleLoadError(f"No plugin class found in module {module_name}")
    
    def unload_module(self, module_name: str, force: bool = False) -> bool:
        """
        Unload a module.
        Returns True if unloading successful, False otherwise.
        """
        if module_name not in self.loaded_modules:
            self.logger.warning(f"Module {module_name} is not loaded")
            return True
        
        # Check dependencies unless forced
        if not force:
            dependents = self.registry.get_dependents(module_name)
            active_dependents = [
                name for name in dependents 
                if name in self.loaded_modules and self.loaded_modules[name].active
            ]
            if active_dependents:
                self.logger.error(f"Cannot unload {module_name}. Active dependents: {active_dependents}")
                return False
        
        # Get module lock
        if module_name not in self.module_locks:
            self.module_locks[module_name] = threading.Lock()
        
        with self.module_locks[module_name]:
            return self._unload_module_internal(module_name, force)
    
    def _unload_module_internal(self, module_name: str, force: bool) -> bool:
        """Internal module unloading implementation"""
        try:
            module_instance = self.loaded_modules[module_name]
            
            # Deactivate if active
            if module_instance.active:
                if not module_instance.deactivate():
                    if not force:
                        self.logger.error(f"Failed to deactivate module {module_name}")
                        return False
            
            # Cleanup
            module_instance.cleanup()
            
            # Remove from tracking
            del self.loaded_modules[module_name]
            if module_name in self.sandboxes:
                del self.sandboxes[module_name]
            
            # Clean up sys.modules
            module_sys_name = f"modules.{module_name}"
            if module_sys_name in sys.modules:
                del sys.modules[module_sys_name]
            
            self.registry.set_module_status(module_name, ModuleStatus.INACTIVE)
            
            self.logger.info(f"Successfully unloaded module: {module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unloading module {module_name}: {e}")
            if force:
                # Force removal even if cleanup failed
                if module_name in self.loaded_modules:
                    del self.loaded_modules[module_name]
                if module_name in self.sandboxes:
                    del self.sandboxes[module_name]
                self.registry.set_module_status(module_name, ModuleStatus.ERROR)
                return True
            return False
    
    def reload_module(self, module_name: str, config_override: Optional[Dict[str, Any]] = None) -> bool:
        """
        Reload a module (hot-reload).
        Returns True if reloading successful, False otherwise.
        """
        if module_name not in self.loaded_modules:
            # Just load it normally
            return self.load_module(module_name, config_override)
        
        self.logger.info(f"Reloading module: {module_name}")
        
        # Store current state
        was_active = self.loaded_modules[module_name].active
        
        # Unload
        if not self.unload_module(module_name):
            return False
        
        # Reload
        if not self.load_module(module_name, config_override):
            return False
        
        # Restore state
        if was_active:
            return self.activate_module(module_name)
        
        return True
    
    def activate_module(self, module_name: str) -> bool:
        """Activate a loaded module"""
        if module_name not in self.loaded_modules:
            self.logger.error(f"Module {module_name} is not loaded")
            return False
        
        module_instance = self.loaded_modules[module_name]
        if module_instance.active:
            self.logger.info(f"Module {module_name} is already active")
            return True
        
        try:
            if module_instance.activate():
                self.registry.set_module_status(module_name, ModuleStatus.ACTIVE)
                self.logger.info(f"Activated module: {module_name}")
                return True
            else:
                self.logger.error(f"Failed to activate module: {module_name}")
                return False
        except Exception as e:
            self.logger.error(f"Error activating module {module_name}: {e}")
            return False
    
    def deactivate_module(self, module_name: str) -> bool:
        """Deactivate an active module"""
        if module_name not in self.loaded_modules:
            self.logger.error(f"Module {module_name} is not loaded")
            return False
        
        module_instance = self.loaded_modules[module_name]
        if not module_instance.active:
            self.logger.info(f"Module {module_name} is already inactive")
            return True
        
        try:
            if module_instance.deactivate():
                self.registry.set_module_status(module_name, ModuleStatus.INACTIVE)
                self.logger.info(f"Deactivated module: {module_name}")
                return True
            else:
                self.logger.error(f"Failed to deactivate module: {module_name}")
                return False
        except Exception as e:
            self.logger.error(f"Error deactivating module {module_name}: {e}")
            return False
    
    def get_loaded_module(self, module_name: str) -> Optional[PluginInterface]:
        """Get a loaded module instance"""
        return self.loaded_modules.get(module_name)
    
    def list_loaded_modules(self, active_only: bool = False) -> List[str]:
        """List loaded modules"""
        if active_only:
            return [name for name, module in self.loaded_modules.items() if module.active]
        return list(self.loaded_modules.keys())
    
    def get_module_health(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Get health status of a module"""
        if module_name not in self.loaded_modules:
            return None
        
        try:
            return self.loaded_modules[module_name].get_health_status()
        except Exception as e:
            return {
                'status': 'error',
                'healthy': False,
                'details': {'error': str(e)}
            }
    
    def load_module_set(self, module_names: List[str], 
                       config_overrides: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """
        Load multiple modules in dependency order.
        Returns dict of module_name -> success status.
        """
        results = {}
        
        try:
            # Get loading order
            load_order = self.registry.get_load_order(module_names)
            
            for module_name in load_order:
                config_override = None
                if config_overrides and module_name in config_overrides:
                    config_override = config_overrides[module_name]
                
                success = self.load_module(module_name, config_override)
                results[module_name] = success
                
                if not success:
                    self.logger.error(f"Failed to load {module_name}, stopping module set loading")
                    break
                    
        except Exception as e:
            self.logger.error(f"Error loading module set: {e}")
            
        return results
    
    def activate_module_set(self, module_names: List[str]) -> Dict[str, bool]:
        """Activate multiple modules"""
        results = {}
        
        for module_name in module_names:
            if module_name in self.loaded_modules:
                results[module_name] = self.activate_module(module_name)
            else:
                results[module_name] = False
                
        return results
    
    @contextmanager
    def module_context(self, module_name: str):
        """Context manager for safe module operations"""
        if module_name not in self.module_locks:
            self.module_locks[module_name] = threading.Lock()
            
        with self.module_locks[module_name]:
            yield self.loaded_modules.get(module_name)
    
    def get_failure_info(self, module_name: str) -> Optional[str]:
        """Get failure information for a module"""
        return self.failed_modules.get(module_name)
    
    def clear_failures(self):
        """Clear failure tracking"""
        self.failed_modules.clear()
    
    def export_module_states(self) -> Dict[str, Any]:
        """Export current module states for backup/restore"""
        states = {}
        
        for module_name, module_instance in self.loaded_modules.items():
            states[module_name] = {
                'loaded': True,
                'active': module_instance.active,
                'config': module_instance.config,
                'health': self.get_module_health(module_name)
            }
            
        return states
    
    def restore_module_states(self, states: Dict[str, Any]) -> Dict[str, bool]:
        """Restore module states from backup"""
        results = {}
        
        for module_name, state in states.items():
            if state.get('loaded', False):
                # Load module
                success = self.load_module(module_name, state.get('config'))
                results[module_name] = success
                
                # Activate if it was active
                if success and state.get('active', False):
                    self.activate_module(module_name)
                    
        return results