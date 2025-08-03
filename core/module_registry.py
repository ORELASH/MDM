"""
Module Registry for RedshiftManager
Handles discovery, registration, and dependency management of modules.
"""

import os
import json
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
import importlib.util
from dataclasses import asdict
import logging

from .plugin_interface import ModuleManifest, ModuleType, ModuleStatus


class DependencyError(Exception):
    """Raised when module dependencies cannot be resolved"""
    pass


class ModuleRegistry:
    """
    Central registry for all modules in the system.
    Handles discovery, validation, and dependency resolution.
    """
    
    def __init__(self, core_version: str = "1.0.0"):
        self.core_version = core_version
        self.registered_modules: Dict[str, ModuleManifest] = {}
        self.module_paths: Dict[str, str] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.reverse_dependency_graph: Dict[str, Set[str]] = {}
        self.module_status: Dict[str, ModuleStatus] = {}
        self.logger = logging.getLogger("core.registry")
        
        # Default module paths
        self.search_paths = [
            Path(__file__).parent.parent / "modules",  # Built-in modules
            Path.home() / ".redshift_manager" / "modules",  # User modules
            Path.cwd() / "modules"  # Project modules
        ]
    
    def add_search_path(self, path: str):
        """Add a directory to search for modules"""
        search_path = Path(path)
        if search_path.exists() and search_path.is_dir():
            self.search_paths.append(search_path)
            self.logger.info(f"Added module search path: {path}")
        else:
            self.logger.warning(f"Invalid module search path: {path}")
    
    def discover_modules(self, force_refresh: bool = False) -> List[str]:
        """
        Discover modules in all search paths.
        Returns list of discovered module names.
        """
        discovered = []
        
        for search_path in self.search_paths:
            if not search_path.exists():
                continue
                
            self.logger.info(f"Scanning for modules in: {search_path}")
            
            for item in search_path.iterdir():
                if not item.is_dir():
                    continue
                
                module_json = item / "module.json"
                if not module_json.exists():
                    continue
                
                try:
                    manifest = ModuleManifest.from_json_file(str(module_json))
                    
                    # Check if already registered and skip if not forcing refresh
                    if manifest.name in self.registered_modules and not force_refresh:
                        continue
                    
                    # Validate module structure
                    if self._validate_module_structure(item, manifest):
                        self.register_module(manifest, str(item))
                        discovered.append(manifest.name)
                        self.logger.info(f"Discovered module: {manifest.name} v{manifest.version}")
                    else:
                        self.logger.warning(f"Invalid module structure: {item}")
                        
                except Exception as e:
                    self.logger.error(f"Error discovering module in {item}: {e}")
        
        self.logger.info(f"Discovery complete. Found {len(discovered)} modules.")
        return discovered
    
    def register_module(self, manifest: ModuleManifest, module_path: str):
        """Register a module in the registry"""
        try:
            # Validate manifest
            if not self._validate_manifest(manifest):
                raise ValueError(f"Invalid manifest for module {manifest.name}")
            
            # Check compatibility
            if not self._check_compatibility(manifest):
                raise ValueError(f"Module {manifest.name} is not compatible with core version {self.core_version}")
            
            # Register the module
            self.registered_modules[manifest.name] = manifest
            self.module_paths[manifest.name] = module_path
            self.module_status[manifest.name] = ModuleStatus.INACTIVE
            
            # Build dependency graph
            self._update_dependency_graph(manifest)
            
            self.logger.info(f"Registered module: {manifest.name} v{manifest.version}")
            
        except Exception as e:
            self.logger.error(f"Failed to register module {manifest.name}: {e}")
            raise
    
    def unregister_module(self, module_name: str):
        """Unregister a module from the registry"""
        if module_name not in self.registered_modules:
            self.logger.warning(f"Module {module_name} is not registered")
            return
        
        # Check if other modules depend on this one
        dependents = self.reverse_dependency_graph.get(module_name, set())
        if dependents:
            active_dependents = [name for name in dependents 
                               if self.module_status.get(name) == ModuleStatus.ACTIVE]
            if active_dependents:
                raise DependencyError(f"Cannot unregister {module_name}. "
                                    f"Active modules depend on it: {active_dependents}")
        
        # Remove from all tracking structures
        del self.registered_modules[module_name]
        del self.module_paths[module_name]
        del self.module_status[module_name]
        
        # Clean up dependency graph
        if module_name in self.dependency_graph:
            del self.dependency_graph[module_name]
        
        for deps in self.dependency_graph.values():
            deps.discard(module_name)
        
        if module_name in self.reverse_dependency_graph:
            del self.reverse_dependency_graph[module_name]
        
        for deps in self.reverse_dependency_graph.values():
            deps.discard(module_name)
        
        self.logger.info(f"Unregistered module: {module_name}")
    
    def get_module_manifest(self, module_name: str) -> Optional[ModuleManifest]:
        """Get manifest for a registered module"""
        return self.registered_modules.get(module_name)
    
    def get_module_path(self, module_name: str) -> Optional[str]:
        """Get file system path for a registered module"""
        return self.module_paths.get(module_name)
    
    def get_module_status(self, module_name: str) -> ModuleStatus:
        """Get current status of a module"""
        return self.module_status.get(module_name, ModuleStatus.UNKNOWN)
    
    def set_module_status(self, module_name: str, status: ModuleStatus):
        """Set status for a module"""
        if module_name in self.registered_modules:
            self.module_status[module_name] = status
            self.logger.debug(f"Module {module_name} status changed to {status.value}")
    
    def list_modules(self, module_type: Optional[ModuleType] = None, 
                    status: Optional[ModuleStatus] = None) -> List[str]:
        """List registered modules with optional filtering"""
        modules = []
        
        for name, manifest in self.registered_modules.items():
            # Filter by type if specified
            if module_type and manifest.module_type != module_type:
                continue
            
            # Filter by status if specified
            if status and self.module_status.get(name) != status:
                continue
            
            modules.append(name)
        
        return sorted(modules)
    
    def resolve_dependencies(self, module_name: str) -> List[str]:
        """
        Resolve dependencies for a module in correct loading order.
        Returns list of module names in dependency order.
        """
        if module_name not in self.registered_modules:
            raise ValueError(f"Module {module_name} is not registered")
        
        resolved = []
        visited = set()
        temp_visited = set()
        
        def visit(name):
            if name in temp_visited:
                raise DependencyError(f"Circular dependency detected involving {name}")
            
            if name in visited:
                return
            
            temp_visited.add(name)
            
            # Visit dependencies first
            dependencies = self.dependency_graph.get(name, set())
            for dep in dependencies:
                if dep not in self.registered_modules:
                    raise DependencyError(f"Required dependency {dep} is not available for {name}")
                visit(dep)
            
            temp_visited.remove(name)
            visited.add(name)
            resolved.append(name)
        
        visit(module_name)
        return resolved
    
    def get_dependents(self, module_name: str) -> Set[str]:
        """Get all modules that depend on the given module"""
        return self.reverse_dependency_graph.get(module_name, set()).copy()
    
    def get_load_order(self, module_names: List[str]) -> List[str]:
        """
        Get the correct loading order for multiple modules.
        Returns list of module names in dependency order.
        """
        all_modules = set()
        
        # Collect all modules and their dependencies
        for name in module_names:
            all_modules.update(self.resolve_dependencies(name))
        
        # Topological sort
        resolved = []
        visited = set()
        temp_visited = set()
        
        def visit(name):
            if name in temp_visited:
                raise DependencyError(f"Circular dependency detected involving {name}")
            
            if name in visited:
                return
            
            temp_visited.add(name)
            
            dependencies = self.dependency_graph.get(name, set())
            for dep in dependencies:
                if dep in all_modules:  # Only visit if it's in our set
                    visit(dep)
            
            temp_visited.remove(name)
            visited.add(name)
            resolved.append(name)
        
        for name in all_modules:
            if name not in visited:
                visit(name)
        
        return resolved
    
    def find_modules_by_capability(self, capability: str) -> List[str]:
        """Find modules that provide a specific capability"""
        modules = []
        for name, manifest in self.registered_modules.items():
            if capability in manifest.provides_capabilities:
                modules.append(name)
        return modules
    
    def validate_module_set(self, module_names: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that a set of modules can be loaded together.
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Check if all modules are registered
            for name in module_names:
                if name not in self.registered_modules:
                    errors.append(f"Module {name} is not registered")
            
            if errors:
                return False, errors
            
            # Try to resolve dependencies
            try:
                self.get_load_order(module_names)
            except DependencyError as e:
                errors.append(str(e))
            
            # Check capability conflicts (if any modules provide conflicting capabilities)
            provided_capabilities = {}
            for name in module_names:
                manifest = self.registered_modules[name]
                for capability in manifest.provides_capabilities:
                    if capability in provided_capabilities:
                        errors.append(f"Capability conflict: {capability} provided by both "
                                    f"{provided_capabilities[capability]} and {name}")
                    else:
                        provided_capabilities[capability] = name
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return len(errors) == 0, errors
    
    def export_registry(self) -> Dict:
        """Export registry state for backup/transfer"""
        return {
            'core_version': self.core_version,
            'modules': {
                name: asdict(manifest) 
                for name, manifest in self.registered_modules.items()
            },
            'module_paths': self.module_paths.copy(),
            'module_status': {
                name: status.value 
                for name, status in self.module_status.items()
            }
        }
    
    def import_registry(self, data: Dict):
        """Import registry state from backup/transfer"""
        try:
            self.core_version = data.get('core_version', self.core_version)
            
            # Clear current state
            self.registered_modules.clear()
            self.module_paths.clear()
            self.module_status.clear()
            self.dependency_graph.clear()
            self.reverse_dependency_graph.clear()
            
            # Import modules
            for name, manifest_data in data.get('modules', {}).items():
                manifest = ModuleManifest.from_dict(manifest_data)
                path = data.get('module_paths', {}).get(name, '')
                status_str = data.get('module_status', {}).get(name, 'inactive')
                status = ModuleStatus(status_str)
                
                self.registered_modules[name] = manifest
                self.module_paths[name] = path
                self.module_status[name] = status
                self._update_dependency_graph(manifest)
            
            self.logger.info(f"Imported registry with {len(self.registered_modules)} modules")
            
        except Exception as e:
            self.logger.error(f"Failed to import registry: {e}")
            raise
    
    def _validate_module_structure(self, module_path: Path, manifest: ModuleManifest) -> bool:
        """Validate that module has required structure"""
        required_files = ["__init__.py"]
        
        for file_name in required_files:
            if not (module_path / file_name).exists():
                self.logger.warning(f"Module {manifest.name} missing required file: {file_name}")
                return False
        
        return True
    
    def _validate_manifest(self, manifest: ModuleManifest) -> bool:
        """Validate module manifest"""
        if not manifest.name:
            return False
        
        if not manifest.version:
            return False
        
        # Check for valid module type
        if not isinstance(manifest.module_type, ModuleType):
            return False
        
        return True
    
    def _check_compatibility(self, manifest: ModuleManifest) -> bool:
        """Check if module is compatible with current core version"""
        # Simple version check - in real implementation you'd want semantic versioning
        core_version_parts = self.core_version.split('.')
        min_version_parts = manifest.core_version_min.split('.')
        
        # Compare major version
        if int(core_version_parts[0]) < int(min_version_parts[0]):
            return False
        
        # If major versions match, compare minor version
        if (int(core_version_parts[0]) == int(min_version_parts[0]) and 
            len(core_version_parts) > 1 and len(min_version_parts) > 1):
            if int(core_version_parts[1]) < int(min_version_parts[1]):
                return False
        
        # Check maximum version if specified
        if manifest.core_version_max:
            max_version_parts = manifest.core_version_max.split('.')
            if int(core_version_parts[0]) > int(max_version_parts[0]):
                return False
        
        return True
    
    def _update_dependency_graph(self, manifest: ModuleManifest):
        """Update dependency graphs for a module"""
        module_name = manifest.name
        
        # Initialize dependency set for this module
        self.dependency_graph[module_name] = set(manifest.required_modules)
        
        # Update reverse dependencies
        for dep in manifest.required_modules:
            if dep not in self.reverse_dependency_graph:
                self.reverse_dependency_graph[dep] = set()
            self.reverse_dependency_graph[dep].add(module_name)