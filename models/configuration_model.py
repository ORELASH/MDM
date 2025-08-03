"""
RedshiftManager Configuration Model
Hierarchical configuration management system with encryption support.
"""

import os
import json
import toml
import yaml
from typing import Any, Dict, List, Optional, Union, Type, get_type_hints
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging
from datetime import datetime
import configparser
from copy import deepcopy

try:
    from .encryption_model import get_encryption_manager, EncryptionManager
except ImportError:
    # Handle import during development
    encryption_manager = None

# Configure logging
logger = logging.getLogger(__name__)


class ConfigLevel(Enum):
    """Configuration hierarchy levels."""
    SYSTEM = "system"       # System-wide settings
    USER = "user"          # User-specific settings
    SESSION = "session"    # Session-specific settings
    RUNTIME = "runtime"    # Runtime overrides


class ConfigFormat(Enum):
    """Supported configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    INI = "ini"
    ENV = "env"


@dataclass
class ConfigValue:
    """Configuration value with metadata."""
    value: Any
    level: ConfigLevel
    encrypted: bool = False
    description: str = ""
    default: Any = None
    required: bool = False
    validator: Optional[callable] = None
    last_modified: datetime = field(default_factory=datetime.now)
    source_file: Optional[str] = None


@dataclass
class SecurityLevel:
    """Security configuration levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ENTERPRISE = "enterprise"


class ConfigurationValidator:
    """Configuration validation utilities."""
    
    @staticmethod
    def validate_port(value: Any) -> bool:
        """Validate port number."""
        try:
            port = int(value)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_url(value: Any) -> bool:
        """Validate URL format."""
        import re
        if not isinstance(value, str):
            return False
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(value) is not None
    
    @staticmethod
    def validate_email(value: Any) -> bool:
        """Validate email format."""
        import re
        if not isinstance(value, str):
            return False
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return email_pattern.match(value) is not None
    
    @staticmethod
    def validate_directory(value: Any) -> bool:
        """Validate directory path."""
        if not isinstance(value, str):
            return False
        try:
            path = Path(value)
            return path.exists() and path.is_dir()
        except Exception:
            return False


class ConfigurationManager:
    """Advanced hierarchical configuration management."""
    
    def __init__(self, 
                 app_name: str = "RedshiftManager",
                 config_dir: Optional[Path] = None,
                 encryption_manager: Optional[EncryptionManager] = None):
        self.app_name = app_name
        self.config_dir = config_dir or Path("config")
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration hierarchy
        self._configs: Dict[ConfigLevel, Dict[str, ConfigValue]] = {
            level: {} for level in ConfigLevel
        }
        
        # Encryption manager for sensitive values
        self._encryption_manager = encryption_manager or get_encryption_manager()
        
        # File watchers and change tracking
        self._file_timestamps: Dict[str, float] = {}
        self._change_listeners: List[callable] = []
        
        # Load configurations
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """Load all configuration files in hierarchy order."""
        # Load in priority order (lowest to highest)
        self._load_system_config()
        self._load_user_config()
        self._load_session_config()
        self._load_environment_variables()
    
    def _load_system_config(self) -> None:
        """Load system-wide configuration."""
        config_file = self.config_dir / "system.json"
        if config_file.exists():
            self._load_config_file(config_file, ConfigLevel.SYSTEM)
        else:
            # Create default system configuration
            self._create_default_system_config()
    
    def _load_user_config(self) -> None:
        """Load user-specific configuration."""
        user_config_dir = Path.home() / f".{self.app_name.lower()}"
        user_config_dir.mkdir(exist_ok=True)
        
        config_file = user_config_dir / "config.json"
        if config_file.exists():
            self._load_config_file(config_file, ConfigLevel.USER)
    
    def _load_session_config(self) -> None:
        """Load session-specific configuration."""
        session_file = self.config_dir / "session.json"
        if session_file.exists():
            self._load_config_file(session_file, ConfigLevel.SESSION)
    
    def _load_environment_variables(self) -> None:
        """Load configuration from environment variables."""
        prefix = f"{self.app_name.upper()}_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self._set_value(config_key, value, ConfigLevel.RUNTIME)
    
    def _load_config_file(self, file_path: Path, level: ConfigLevel) -> None:
        """Load configuration from file."""
        try:
            # Track file timestamp for change detection
            self._file_timestamps[str(file_path)] = file_path.stat().st_mtime
            
            # Determine file format
            format_type = self._detect_file_format(file_path)
            
            # Load and parse file
            with open(file_path, 'r', encoding='utf-8') as f:
                if format_type == ConfigFormat.JSON:
                    data = json.load(f)
                elif format_type == ConfigFormat.YAML:
                    data = yaml.safe_load(f)
                elif format_type == ConfigFormat.TOML:
                    data = toml.load(f)
                elif format_type == ConfigFormat.INI:
                    config = configparser.ConfigParser()
                    config.read(file_path)
                    data = {section: dict(config.items(section)) 
                           for section in config.sections()}
                else:
                    logger.warning(f"Unsupported config format: {file_path}")
                    return
            
            # Process loaded data
            self._process_config_data(data, level, str(file_path))
            
        except Exception as e:
            logger.error(f"Failed to load config file {file_path}: {e}")
    
    def _detect_file_format(self, file_path: Path) -> ConfigFormat:
        """Detect configuration file format."""
        suffix = file_path.suffix.lower()
        
        format_map = {
            '.json': ConfigFormat.JSON,
            '.yaml': ConfigFormat.YAML,
            '.yml': ConfigFormat.YAML,
            '.toml': ConfigFormat.TOML,
            '.ini': ConfigFormat.INI,
            '.cfg': ConfigFormat.INI,
            '.conf': ConfigFormat.INI
        }
        
        return format_map.get(suffix, ConfigFormat.JSON)
    
    def _process_config_data(self, data: Dict[str, Any], level: ConfigLevel, source_file: str) -> None:
        """Process loaded configuration data."""
        def process_dict(d: Dict[str, Any], prefix: str = "") -> None:
            for key, value in d.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, dict):
                    # Handle nested dictionaries
                    if '_meta' in value:
                        # Special metadata format
                        meta = value['_meta']
                        actual_value = value.get('value', None)
                        
                        config_value = ConfigValue(
                            value=actual_value,
                            level=level,
                            encrypted=meta.get('encrypted', False),
                            description=meta.get('description', ''),
                            default=meta.get('default'),
                            required=meta.get('required', False),
                            source_file=source_file
                        )
                        
                        # Decrypt if needed
                        if config_value.encrypted and isinstance(actual_value, str):
                            try:
                                config_value.value = self._encryption_manager.decrypt_string(actual_value)
                            except Exception as e:
                                logger.warning(f"Failed to decrypt config value {full_key}: {e}")
                        
                        self._configs[level][full_key] = config_value
                    else:
                        # Regular nested dictionary
                        process_dict(value, full_key)
                else:
                    # Simple value
                    self._set_value(full_key, value, level, source_file)
        
        process_dict(data)
    
    def _set_value(self, key: str, value: Any, level: ConfigLevel, source_file: Optional[str] = None) -> None:
        """Set configuration value."""
        config_value = ConfigValue(
            value=value,
            level=level,
            source_file=source_file
        )
        
        self._configs[level][key] = config_value
    
    def get(self, key: str, default: Any = None, level: Optional[ConfigLevel] = None) -> Any:
        """Get configuration value with hierarchy resolution."""
        if level:
            # Get from specific level
            return self._configs[level].get(key, ConfigValue(default, level)).value
        
        # Search hierarchy (highest priority first)
        for search_level in [ConfigLevel.RUNTIME, ConfigLevel.SESSION, 
                           ConfigLevel.USER, ConfigLevel.SYSTEM]:
            if key in self._configs[search_level]:
                return self._configs[search_level][key].value
        
        return default
    
    def set(self, key: str, value: Any, level: ConfigLevel = ConfigLevel.SESSION,
            encrypted: bool = False, description: str = "", persist: bool = True) -> None:
        """Set configuration value."""
        # Encrypt if requested
        actual_value = value
        if encrypted and isinstance(value, str):
            actual_value = self._encryption_manager.encrypt_string(value)
        
        config_value = ConfigValue(
            value=actual_value,
            level=level,
            encrypted=encrypted,
            description=description,
            last_modified=datetime.now()
        )
        
        self._configs[level][key] = config_value
        
        # Persist if requested
        if persist:
            self._save_config(level)
        
        # Notify listeners
        self._notify_change_listeners(key, value, level)
    
    def get_all(self, level: Optional[ConfigLevel] = None) -> Dict[str, Any]:
        """Get all configuration values."""
        if level:
            return {k: v.value for k, v in self._configs[level].items()}
        
        # Merge all levels (highest priority wins)
        result = {}
        for search_level in [ConfigLevel.SYSTEM, ConfigLevel.USER,
                           ConfigLevel.SESSION, ConfigLevel.RUNTIME]:
            for key, config_value in self._configs[search_level].items():
                result[key] = config_value.value
        
        return result
    
    def delete(self, key: str, level: Optional[ConfigLevel] = None) -> bool:
        """Delete configuration value."""
        if level:
            if key in self._configs[level]:
                del self._configs[level][key]
                self._save_config(level)
                return True
            return False
        
        # Delete from all levels
        deleted = False
        for search_level in ConfigLevel:
            if key in self._configs[search_level]:
                del self._configs[search_level][key]
                self._save_config(search_level)
                deleted = True
        
        return deleted
    
    def _save_config(self, level: ConfigLevel) -> None:
        """Save configuration level to file."""
        try:
            if level == ConfigLevel.SYSTEM:
                file_path = self.config_dir / "system.json"
            elif level == ConfigLevel.USER:
                user_config_dir = Path.home() / f".{self.app_name.lower()}"
                file_path = user_config_dir / "config.json"
            elif level == ConfigLevel.SESSION:
                file_path = self.config_dir / "session.json"
            else:
                # Runtime configs are not persisted
                return
            
            # Prepare data for saving
            data = {}
            for key, config_value in self._configs[level].items():
                # Handle nested keys
                keys = key.split('.')
                current = data
                
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                
                # Save with metadata
                if config_value.encrypted or config_value.description:
                    current[keys[-1]] = {
                        'value': config_value.value,
                        '_meta': {
                            'encrypted': config_value.encrypted,
                            'description': config_value.description,
                            'last_modified': config_value.last_modified.isoformat()
                        }
                    }
                else:
                    current[keys[-1]] = config_value.value
            
            # Write to file
            file_path.parent.mkdir(exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Set restrictive permissions for sensitive configs
            if level in [ConfigLevel.USER, ConfigLevel.SESSION]:
                os.chmod(file_path, 0o600)
                
        except Exception as e:
            logger.error(f"Failed to save config level {level}: {e}")
    
    def _create_default_system_config(self) -> None:
        """Create default system configuration."""
        defaults = {
            "application.name": "RedshiftManager",
            "application.version": "1.0.0",
            "application.environment": "development",
            "security.encryption_enabled": True,
            "security.password_min_length": 12,
            "security.session_timeout": 3600,
            "database.type": "sqlite",
            "database.name": "redshift_manager.db",
            "logging.level": "INFO",
            "logging.to_file": True,
            "ui.theme": "light",
            "ui.language": "en",
            "redshift.default_port": 5439,
            "redshift.ssl_mode": "require",
            "redshift.connection_timeout": 30
        }
        
        for key, value in defaults.items():
            self._set_value(key, value, ConfigLevel.SYSTEM)
        
        self._save_config(ConfigLevel.SYSTEM)
    
    def add_change_listener(self, callback: callable) -> None:
        """Add configuration change listener."""
        self._change_listeners.append(callback)
    
    def remove_change_listener(self, callback: callable) -> None:
        """Remove configuration change listener."""
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)
    
    def _notify_change_listeners(self, key: str, value: Any, level: ConfigLevel) -> None:
        """Notify change listeners."""
        for listener in self._change_listeners:
            try:
                listener(key, value, level)
            except Exception as e:
                logger.error(f"Error in change listener: {e}")
    
    def export_config(self, file_path: Path, level: Optional[ConfigLevel] = None,
                     include_encrypted: bool = False, format_type: ConfigFormat = ConfigFormat.JSON) -> None:
        """Export configuration to file."""
        try:
            if level:
                data = {k: v.value for k, v in self._configs[level].items()
                       if include_encrypted or not v.encrypted}
            else:
                data = self.get_all()
                if not include_encrypted:
                    # Filter out encrypted values
                    filtered_data = {}
                    for key, value in data.items():
                        is_encrypted = any(
                            self._configs[lvl].get(key, ConfigValue(None, lvl)).encrypted
                            for lvl in ConfigLevel
                        )
                        if not is_encrypted:
                            filtered_data[key] = value
                    data = filtered_data
            
            # Convert flat keys to nested structure
            nested_data = {}
            for key, value in data.items():
                keys = key.split('.')
                current = nested_data
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = value
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                if format_type == ConfigFormat.JSON:
                    json.dump(nested_data, f, indent=2, default=str)
                elif format_type == ConfigFormat.YAML:
                    yaml.dump(nested_data, f, default_flow_style=False)
                elif format_type == ConfigFormat.TOML:
                    toml.dump(nested_data, f)
                else:
                    raise ValueError(f"Unsupported export format: {format_type}")
            
            logger.info(f"Configuration exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
    
    def import_config(self, file_path: Path, level: ConfigLevel = ConfigLevel.USER,
                     merge: bool = True) -> None:
        """Import configuration from file."""
        try:
            if not merge:
                # Clear existing configuration
                self._configs[level].clear()
            
            # Load and merge
            self._load_config_file(file_path, level)
            
            logger.info(f"Configuration imported from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
    
    def validate_config(self) -> List[str]:
        """Validate current configuration."""
        errors = []
        
        # Define validation rules
        validators = {
            'redshift.default_port': ConfigurationValidator.validate_port,
            'security.password_min_length': lambda x: isinstance(x, int) and x >= 8,
            'security.session_timeout': lambda x: isinstance(x, int) and x > 0,
            'logging.level': lambda x: x in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            'ui.language': lambda x: isinstance(x, str) and len(x) == 2,
        }
        
        # Validate all configuration values
        all_config = self.get_all()
        for key, validator in validators.items():
            if key in all_config:
                if not validator(all_config[key]):
                    errors.append(f"Invalid value for {key}: {all_config[key]}")
        
        return errors
    
    def check_file_changes(self) -> List[str]:
        """Check for configuration file changes."""
        changed_files = []
        
        for file_path, old_timestamp in self._file_timestamps.items():
            try:
                current_timestamp = Path(file_path).stat().st_mtime
                if current_timestamp > old_timestamp:
                    changed_files.append(file_path)
            except FileNotFoundError:
                # File was deleted
                changed_files.append(file_path)
        
        return changed_files
    
    def reload_config(self) -> None:
        """Reload all configuration files."""
        # Clear current configuration
        for level in ConfigLevel:
            if level != ConfigLevel.RUNTIME:  # Preserve runtime overrides
                self._configs[level].clear()
        
        # Reload all configurations
        self._load_all_configs()
        
        logger.info("Configuration reloaded")


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_configuration_manager(app_name: str = "RedshiftManager",
                            config_dir: Optional[Path] = None) -> ConfigurationManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(app_name, config_dir)
    return _config_manager


# Convenience functions
def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value."""
    return get_configuration_manager().get(key, default)


def set_config(key: str, value: Any, level: ConfigLevel = ConfigLevel.SESSION,
               encrypted: bool = False) -> None:
    """Set configuration value."""
    return get_configuration_manager().set(key, value, level, encrypted)


if __name__ == "__main__":
    # Example usage
    cm = get_configuration_manager()
    
    # Set some configuration values
    cm.set("database.host", "localhost", ConfigLevel.USER)
    cm.set("database.password", "secret123", ConfigLevel.USER, encrypted=True)
    cm.set("ui.theme", "dark", ConfigLevel.SESSION)
    
    # Get configuration values
    print(f"Database host: {cm.get('database.host')}")
    print(f"Database password: {cm.get('database.password')}")
    print(f"UI theme: {cm.get('ui.theme')}")
    print(f"All config: {cm.get_all()}")
    
    # Validate configuration
    errors = cm.validate_config()
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("Configuration is valid")