"""
Plugin Interface for RedshiftManager Modular System
Defines the standard interface that all modules must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json


class ModuleType(Enum):
    """Types of modules in the system"""
    CORE = "core"
    CONNECTOR = "connector"
    UI = "ui"
    UTILITY = "utility"
    ANALYTICS = "analytics"
    SECURITY = "security"
    INTEGRATION = "integration"


class ModuleStatus(Enum):
    """Module lifecycle status"""
    UNKNOWN = "unknown"
    LOADING = "loading"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UPDATING = "updating"


@dataclass
class ModuleManifest:
    """Module manifest containing metadata and configuration"""
    name: str
    version: str
    description: str
    author: str
    module_type: ModuleType
    
    # Compatibility
    core_version_min: str
    core_version_max: Optional[str] = None
    python_version_min: str = "3.8"
    platforms: List[str] = None
    
    # Dependencies
    required_modules: List[str] = None
    optional_modules: List[str] = None
    system_dependencies: List[str] = None
    
    # Capabilities
    provides_capabilities: List[str] = None
    requires_capabilities: List[str] = None
    
    # UI Integration
    ui_pages: List[str] = None
    ui_widgets: List[str] = None
    menu_items: List[Dict[str, Any]] = None
    
    # Permissions
    required_permissions: List[str] = None
    grants_permissions: List[str] = None
    
    # Hooks and Events
    lifecycle_hooks: Dict[str, str] = None
    event_handlers: Dict[str, str] = None
    
    # Configuration
    config_schema: Dict[str, Any] = None
    default_config: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values for lists and dicts"""
        if self.platforms is None:
            self.platforms = ["linux", "windows", "darwin"]
        if self.required_modules is None:
            self.required_modules = []
        if self.optional_modules is None:
            self.optional_modules = []
        if self.system_dependencies is None:
            self.system_dependencies = []
        if self.provides_capabilities is None:
            self.provides_capabilities = []
        if self.requires_capabilities is None:
            self.requires_capabilities = []
        if self.ui_pages is None:
            self.ui_pages = []
        if self.ui_widgets is None:
            self.ui_widgets = []
        if self.menu_items is None:
            self.menu_items = []
        if self.required_permissions is None:
            self.required_permissions = []
        if self.grants_permissions is None:
            self.grants_permissions = []
        if self.lifecycle_hooks is None:
            self.lifecycle_hooks = {}
        if self.event_handlers is None:
            self.event_handlers = {}
        if self.config_schema is None:
            self.config_schema = {}
        if self.default_config is None:
            self.default_config = {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModuleManifest':
        """Create manifest from dictionary (loaded from JSON)"""
        # Convert string module_type to enum
        if isinstance(data.get('module_type'), str):
            data['module_type'] = ModuleType(data['module_type'])
        
        return cls(**data)

    @classmethod
    def from_json_file(cls, file_path: str) -> 'ModuleManifest':
        """Load manifest from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class ModuleContext:
    """Context object passed to modules with system access"""
    
    def __init__(self, core_instance, module_name: str, config: Dict[str, Any]):
        self.core = core_instance
        self.module_name = module_name
        self.config = config
        self.logger = self._create_logger()
        self._event_handlers = {}
    
    def _create_logger(self):
        """Create module-specific logger"""
        import logging
        logger = logging.getLogger(f"module.{self.module_name}")
        return logger
    
    def get_module(self, module_name: str) -> Optional['PluginInterface']:
        """Get reference to another loaded module"""
        return self.core.get_loaded_module(module_name)
    
    def emit_event(self, event_name: str, data: Any = None):
        """Emit an event to the system"""
        self.core.emit_event(event_name, data, source_module=self.module_name)
    
    def subscribe_event(self, event_name: str, handler: Callable):
        """Subscribe to system events"""
        self.core.subscribe_event(event_name, handler, subscriber_module=self.module_name)
    
    def get_database_session(self):
        """Get database session from core"""
        return self.core.get_database_session()
    
    def get_encryption_manager(self):
        """Get encryption manager from core"""
        return self.core.get_encryption_manager()
    
    def log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit event"""
        self.core.log_audit(action, details, module=self.module_name)


class PluginInterface(ABC):
    """
    Abstract base class that all plugins must implement.
    Provides the standard interface for module lifecycle and capabilities.
    """
    
    def __init__(self, manifest: ModuleManifest, context: ModuleContext):
        self.manifest = manifest
        self.context = context
        self.status = ModuleStatus.UNKNOWN
        self._config = manifest.default_config.copy()
        self._config.update(context.config)
    
    @property
    def name(self) -> str:
        """Module name"""
        return self.manifest.name
    
    @property
    def version(self) -> str:
        """Module version"""
        return self.manifest.version
    
    @property
    def config(self) -> Dict[str, Any]:
        """Module configuration"""
        return self._config
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the module.
        Called when the module is first loaded.
        Returns True if initialization successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def activate(self) -> bool:
        """
        Activate the module.
        Called when the module should start providing its services.
        Returns True if activation successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def deactivate(self) -> bool:
        """
        Deactivate the module.
        Called when the module should stop providing its services.
        Returns True if deactivation successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """
        Clean up module resources.
        Called before the module is unloaded.
        """
        pass
    
    def get_ui_components(self) -> Dict[str, Any]:
        """
        Return UI components provided by this module.
        Override in subclasses to provide custom UI.
        """
        return {
            'pages': {},
            'widgets': {},
            'menu_items': []
        }
    
    def get_api_endpoints(self) -> Dict[str, Callable]:
        """
        Return API endpoints provided by this module.
        Override in subclasses to provide custom APIs.
        """
        return {}
    
    def get_actions(self) -> Dict[str, Callable]:
        """
        Return actions provided by this module.
        Override in subclasses to provide custom actions.
        """
        return {}
    
    def handle_event(self, event_name: str, data: Any):
        """
        Handle system events.
        Override in subclasses to respond to events.
        """
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate module configuration.
        Override in subclasses for custom validation.
        """
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Return module health status.
        Override in subclasses to provide custom health checks.
        """
        return {
            'status': self.status.value,
            'healthy': self.status == ModuleStatus.ACTIVE,
            'details': {}
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update module configuration"""
        if self.validate_config(new_config):
            self._config.update(new_config)
            return True
        return False


class ModuleBase(PluginInterface):
    """
    Base implementation of PluginInterface with common functionality.
    Most modules should inherit from this instead of PluginInterface directly.
    """
    
    def __init__(self, manifest: ModuleManifest, context: ModuleContext):
        super().__init__(manifest, context)
        self._initialized = False
        self._active = False
    
    def initialize(self) -> bool:
        """Base initialization - calls on_initialize hook"""
        try:
            self.status = ModuleStatus.LOADING
            result = self.on_initialize()
            if result:
                self._initialized = True
                self.context.logger.info(f"Module {self.name} initialized successfully")
            else:
                self.status = ModuleStatus.ERROR
                self.context.logger.error(f"Module {self.name} initialization failed")
            return result
        except Exception as e:
            self.status = ModuleStatus.ERROR
            self.context.logger.error(f"Module {self.name} initialization error: {e}")
            return False
    
    def activate(self) -> bool:
        """Base activation - calls on_activate hook"""
        if not self._initialized:
            self.context.logger.error(f"Cannot activate uninitialized module {self.name}")
            return False
        
        try:
            result = self.on_activate()
            if result:
                self._active = True
                self.status = ModuleStatus.ACTIVE
                self.context.logger.info(f"Module {self.name} activated successfully")
            else:
                self.status = ModuleStatus.ERROR
                self.context.logger.error(f"Module {self.name} activation failed")
            return result
        except Exception as e:
            self.status = ModuleStatus.ERROR
            self.context.logger.error(f"Module {self.name} activation error: {e}")
            return False
    
    def deactivate(self) -> bool:
        """Base deactivation - calls on_deactivate hook"""
        try:
            result = self.on_deactivate()
            if result:
                self._active = False
                self.status = ModuleStatus.INACTIVE
                self.context.logger.info(f"Module {self.name} deactivated successfully")
            return result
        except Exception as e:
            self.context.logger.error(f"Module {self.name} deactivation error: {e}")
            return False
    
    def cleanup(self):
        """Base cleanup - calls on_cleanup hook"""
        try:
            self.on_cleanup()
            self._initialized = False
            self._active = False
            self.context.logger.info(f"Module {self.name} cleaned up successfully")
        except Exception as e:
            self.context.logger.error(f"Module {self.name} cleanup error: {e}")
    
    # Hook methods to be overridden by subclasses
    def on_initialize(self) -> bool:
        """Override this method for custom initialization logic"""
        return True
    
    def on_activate(self) -> bool:
        """Override this method for custom activation logic"""
        return True
    
    def on_deactivate(self) -> bool:
        """Override this method for custom deactivation logic"""
        return True
    
    def on_cleanup(self):
        """Override this method for custom cleanup logic"""
        pass
    
    @property
    def initialized(self) -> bool:
        """Check if module is initialized"""
        return self._initialized
    
    @property
    def active(self) -> bool:
        """Check if module is active"""
        return self._active