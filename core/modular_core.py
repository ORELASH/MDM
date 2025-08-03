"""
Modular Core System for RedshiftManager
Central orchestrator for the modular architecture.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import threading
import json
from datetime import datetime

from .module_registry import ModuleRegistry
from .module_loader import ModuleLoader
from .action_framework import ActionFramework
from .population_manager import PopulationManager
from .plugin_interface import ModuleStatus, ModuleType


class ModularCore:
    """
    Central core system that orchestrates all modular components.
    Provides unified interface for module management, action execution, and system coordination.
    """
    
    def __init__(self, core_version: str = "1.0.0", config: Optional[Dict[str, Any]] = None):
        self.core_version = core_version
        self.config = config or {}
        
        # Setup logging
        self.logger = logging.getLogger("core.modular")
        
        # Initialize core components
        self.registry = ModuleRegistry(core_version)
        self.loader = ModuleLoader(self.registry, self)
        self.action_framework = ActionFramework(self)
        self.population_manager = PopulationManager(self)
        
        # System state
        self.system_started = False
        self.startup_time = None
        self.shutdown_time = None
        
        # Event system
        self.event_subscribers: Dict[str, List[Callable]] = {}
        self.event_lock = threading.Lock()
        
        # Extension points
        self.ui_components: Dict[str, Dict[str, Any]] = {}
        self.api_endpoints: Dict[str, Callable] = {}
        
        # Security and audit
        self.audit_log: List[Dict[str, Any]] = []
        self.security_manager = None  # Will be injected
        
        self.logger.info(f"Modular Core initialized (version {core_version})")
    
    def start_system(self, auto_discover: bool = True, auto_load: List[str] = None) -> bool:
        """
        Start the modular system.
        
        Args:
            auto_discover: Whether to automatically discover modules
            auto_load: List of module names to automatically load on startup
        
        Returns:
            True if startup successful, False otherwise
        """
        try:
            self.logger.info("Starting Modular Core System")
            self.startup_time = datetime.utcnow()
            
            # Discover modules if requested
            if auto_discover:
                discovered = self.registry.discover_modules()
                self.logger.info(f"Discovered {len(discovered)} modules")
            
            # Auto-load specified modules
            if auto_load:
                self.logger.info(f"Auto-loading modules: {auto_load}")
                for module_name in auto_load:
                    if not self.load_module(module_name):
                        self.logger.warning(f"Failed to auto-load module: {module_name}")
            
            self.system_started = True
            self.emit_event("system_started", {"startup_time": self.startup_time})
            
            self.logger.info("Modular Core System started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Modular Core System: {e}")
            return False
    
    def shutdown_system(self, force: bool = False) -> bool:
        """
        Shutdown the modular system.
        
        Args:
            force: Whether to force shutdown even if modules fail to unload
        
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            self.logger.info("Shutting down Modular Core System")
            self.shutdown_time = datetime.utcnow()
            
            # Emit shutdown event
            self.emit_event("system_shutdown", {"shutdown_time": self.shutdown_time})
            
            # Unload all modules
            loaded_modules = self.loader.list_loaded_modules()
            for module_name in loaded_modules:
                if not self.unload_module(module_name, force=force):
                    if not force:
                        self.logger.error(f"Failed to unload module {module_name}")
                        return False
            
            self.system_started = False
            self.logger.info("Modular Core System shutdown complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during system shutdown: {e}")
            return False
    
    def restart_system(self) -> bool:
        """Restart the modular system"""
        self.logger.info("Restarting Modular Core System")
        
        # Save current state
        module_states = self.loader.export_module_states()
        
        # Shutdown
        if not self.shutdown_system():
            self.logger.error("Failed to shutdown system for restart")
            return False
        
        # Start
        if not self.start_system():
            self.logger.error("Failed to start system during restart")
            return False
        
        # Restore module states
        self.loader.restore_module_states(module_states)
        
        self.logger.info("System restart complete")
        return True
    
    # Module Management Interface
    
    def discover_modules(self, force_refresh: bool = False) -> List[str]:
        """Discover available modules"""
        return self.registry.discover_modules(force_refresh)
    
    def list_modules(self, module_type: Optional[ModuleType] = None, 
                    status: Optional[ModuleStatus] = None) -> List[str]:
        """List registered modules with optional filtering"""
        return self.registry.list_modules(module_type, status)
    
    def get_module_info(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a module"""
        manifest = self.registry.get_module_manifest(module_name)
        if not manifest:
            return None
        
        module_instance = self.loader.get_loaded_module(module_name)
        health = self.loader.get_module_health(module_name) if module_instance else None
        
        return {
            "manifest": manifest.__dict__,
            "status": self.registry.get_module_status(module_name).value,
            "loaded": module_instance is not None,
            "active": module_instance.active if module_instance else False,
            "health": health,
            "dependencies": list(self.registry.dependency_graph.get(module_name, set())),
            "dependents": list(self.registry.get_dependents(module_name))
        }
    
    def load_module(self, module_name: str, config_override: Optional[Dict[str, Any]] = None) -> bool:
        """Load a module"""
        return self.loader.load_module(module_name, config_override)
    
    def unload_module(self, module_name: str, force: bool = False) -> bool:
        """Unload a module"""
        return self.loader.unload_module(module_name, force)
    
    def reload_module(self, module_name: str, config_override: Optional[Dict[str, Any]] = None) -> bool:
        """Reload a module"""
        return self.loader.reload_module(module_name, config_override)
    
    def activate_module(self, module_name: str) -> bool:
        """Activate a loaded module"""
        success = self.loader.activate_module(module_name)
        
        if success:
            # Register module UI components and actions
            self._register_module_extensions(module_name)
            self.emit_event("module_activated", {"module_name": module_name})
        
        return success
    
    def deactivate_module(self, module_name: str) -> bool:
        """Deactivate an active module"""
        success = self.loader.deactivate_module(module_name)
        
        if success:
            # Unregister module extensions
            self._unregister_module_extensions(module_name)
            self.emit_event("module_deactivated", {"module_name": module_name})
        
        return success
    
    def get_loaded_module(self, module_name: str):
        """Get a loaded module instance"""
        return self.loader.get_loaded_module(module_name)
    
    # Action Framework Interface
    
    def execute_action(self, action_name: str, population_target, parameters: Dict[str, Any], 
                      user_id: str) -> Optional[str]:
        """Execute an action and return execution ID"""
        # Validate request
        errors = self.action_framework.validate_execution_request(
            action_name, population_target, parameters, user_id
        )
        
        if errors:
            self.logger.error(f"Action execution validation failed: {errors}")
            return None
        
        # Create and execute
        execution_id = self.action_framework.create_execution(
            action_name, population_target, parameters, user_id
        )
        
        # Execute in background (in real implementation, you might use a task queue)
        success = self.action_framework.execute_action(execution_id)
        
        if success:
            self.emit_event("action_completed", {
                "execution_id": execution_id,
                "action_name": action_name,
                "user_id": user_id
            })
        else:
            self.emit_event("action_failed", {
                "execution_id": execution_id,
                "action_name": action_name,
                "user_id": user_id
            })
        
        return execution_id
    
    def get_action_catalog(self) -> Dict[str, Any]:
        """Get catalog of available actions"""
        return self.action_framework.get_action_catalog()
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an action execution"""
        execution = self.action_framework.get_execution(execution_id)
        return execution.to_dict() if execution else None
    
    # Population Management Interface
    
    def resolve_population(self, population_target) -> List[Any]:
        """Resolve a population target to actual objects"""
        return self.population_manager.resolve_targets(population_target)
    
    def preview_population(self, population_target, limit: int = 10) -> Dict[str, Any]:
        """Preview a population target"""
        return self.population_manager.preview_targets(population_target, limit)
    
    def create_population_group(self, group) -> bool:
        """Create a new population group"""
        return self.population_manager.create_group(group)
    
    def get_supported_target_types(self) -> List[str]:
        """Get supported population target types"""
        return self.population_manager.get_supported_target_types()
    
    # Event System
    
    def emit_event(self, event_name: str, data: Any = None, source_module: str = None):
        """Emit an event to all subscribers"""
        with self.event_lock:
            subscribers = self.event_subscribers.get(event_name, [])
            
            for callback in subscribers:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_name}: {e}")
            
            # Log the event
            self.log_audit("event_emitted", {
                "event_name": event_name,
                "source_module": source_module,
                "subscriber_count": len(subscribers)
            })
    
    def subscribe_event(self, event_name: str, callback: Callable, subscriber_module: str = None):
        """Subscribe to an event"""
        with self.event_lock:
            if event_name not in self.event_subscribers:
                self.event_subscribers[event_name] = []
            
            self.event_subscribers[event_name].append(callback)
            
            self.logger.debug(f"Module {subscriber_module} subscribed to event {event_name}")
    
    def unsubscribe_event(self, event_name: str, callback: Callable):
        """Unsubscribe from an event"""
        with self.event_lock:
            if event_name in self.event_subscribers:
                try:
                    self.event_subscribers[event_name].remove(callback)
                except ValueError:
                    pass
    
    # UI and API Extension Points
    
    def register_ui_component(self, module_name: str, component_type: str, 
                             component_name: str, component: Any):
        """Register a UI component from a module"""
        if module_name not in self.ui_components:
            self.ui_components[module_name] = {}
        
        if component_type not in self.ui_components[module_name]:
            self.ui_components[module_name][component_type] = {}
        
        self.ui_components[module_name][component_type][component_name] = component
        
        self.logger.debug(f"Registered {component_type} '{component_name}' from module {module_name}")
    
    def unregister_ui_components(self, module_name: str):
        """Unregister all UI components from a module"""
        if module_name in self.ui_components:
            del self.ui_components[module_name]
            self.logger.debug(f"Unregistered UI components for module {module_name}")
    
    def get_ui_components(self, component_type: Optional[str] = None) -> Dict[str, Any]:
        """Get registered UI components"""
        if component_type:
            components = {}
            for module_name, module_components in self.ui_components.items():
                if component_type in module_components:
                    components[module_name] = module_components[component_type]
            return components
        
        return self.ui_components
    
    def register_api_endpoint(self, module_name: str, endpoint_name: str, handler: Callable):
        """Register an API endpoint from a module"""
        full_endpoint_name = f"{module_name}.{endpoint_name}"
        self.api_endpoints[full_endpoint_name] = handler
        self.logger.debug(f"Registered API endpoint: {full_endpoint_name}")
    
    def get_api_endpoints(self) -> Dict[str, Callable]:
        """Get all registered API endpoints"""
        return self.api_endpoints.copy()
    
    # System Integration Points
    
    def get_database_session(self):
        """Get database session (to be injected)"""
        if hasattr(self, '_database_manager'):
            return self._database_manager.session_scope()
        return None
    
    def set_database_manager(self, database_manager):
        """Inject database manager"""
        self._database_manager = database_manager
    
    def get_encryption_manager(self):
        """Get encryption manager (to be injected)"""
        return getattr(self, '_encryption_manager', None)
    
    def set_encryption_manager(self, encryption_manager):
        """Inject encryption manager"""
        self._encryption_manager = encryption_manager
    
    def set_security_manager(self, security_manager):
        """Inject security manager"""
        self.security_manager = security_manager
    
    def log_audit(self, action: str, details: Dict[str, Any], **kwargs):
        """Log audit event"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details,
            **kwargs
        }
        
        self.audit_log.append(audit_entry)
        
        # Keep only recent entries (configurable limit)
        max_entries = self.config.get('audit_log_max_entries', 10000)
        if len(self.audit_log) > max_entries:
            self.audit_log = self.audit_log[-max_entries:]
    
    # System Status and Health
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        loaded_modules = self.loader.list_loaded_modules()
        active_modules = self.loader.list_loaded_modules(active_only=True)
        
        return {
            "system_started": self.system_started,
            "core_version": self.core_version,
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds() if self.startup_time else 0,
            "modules": {
                "total_registered": len(self.registry.registered_modules),
                "loaded": len(loaded_modules),
                "active": len(active_modules),
                "failed": len(self.loader.failed_modules)
            },
            "actions": {
                "total_registered": len(self.action_framework.registered_actions),
                "executions_total": len(self.action_framework.executions)
            },
            "events": {
                "total_subscribers": sum(len(subs) for subs in self.event_subscribers.values()),
                "event_types": len(self.event_subscribers)
            },
            "ui_components": {
                "modules_with_ui": len(self.ui_components),
                "total_components": sum(
                    len(comps) for module_comps in self.ui_components.values() 
                    for comps in module_comps.values()
                )
            }
        }
    
    def get_module_health_report(self) -> Dict[str, Any]:
        """Get health report for all modules"""
        report = {}
        
        for module_name in self.loader.list_loaded_modules():
            health = self.loader.get_module_health(module_name)
            report[module_name] = health
        
        return report
    
    # Private Helper Methods
    
    def _register_module_extensions(self, module_name: str):
        """Register UI components and API endpoints from a module"""
        module_instance = self.loader.get_loaded_module(module_name)
        if not module_instance:
            return
        
        try:
            # Register UI components
            ui_components = module_instance.get_ui_components()
            for component_type, components in ui_components.items():
                if isinstance(components, dict):
                    for comp_name, comp in components.items():
                        self.register_ui_component(module_name, component_type, comp_name, comp)
            
            # Register API endpoints
            api_endpoints = module_instance.get_api_endpoints()
            for endpoint_name, handler in api_endpoints.items():
                self.register_api_endpoint(module_name, endpoint_name, handler)
            
            # Register actions
            actions = module_instance.get_actions()
            for action_name, action in actions.items():
                self.action_framework.register_action(action)
                
        except Exception as e:
            self.logger.error(f"Error registering extensions for module {module_name}: {e}")
    
    def _unregister_module_extensions(self, module_name: str):
        """Unregister UI components and API endpoints from a module"""
        try:
            # Unregister UI components
            self.unregister_ui_components(module_name)
            
            # Unregister API endpoints
            endpoints_to_remove = [
                endpoint for endpoint in self.api_endpoints.keys()
                if endpoint.startswith(f"{module_name}.")
            ]
            for endpoint in endpoints_to_remove:
                del self.api_endpoints[endpoint]
            
            # Unregister actions (this would need to be tracked by module)
            # For now, we'll leave actions registered to avoid breaking running executions
            
        except Exception as e:
            self.logger.error(f"Error unregistering extensions for module {module_name}: {e}")


# Global instance for easy access
_modular_core_instance = None

def get_modular_core() -> Optional[ModularCore]:
    """Get the global modular core instance"""
    return _modular_core_instance

def initialize_modular_core(core_version: str = "1.0.0", config: Optional[Dict[str, Any]] = None) -> ModularCore:
    """Initialize the global modular core instance"""
    global _modular_core_instance
    _modular_core_instance = ModularCore(core_version, config)
    return _modular_core_instance