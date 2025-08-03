# RedshiftManager Models Package
"""
Data models and business logic for RedshiftManager.
"""

__version__ = "1.0.0"
__author__ = "RedshiftManager Team"

# Import main components for easy access
try:
    from .encryption_model import (
        get_encryption_manager,
        get_password_validator,
        PasswordPolicy,
        EncryptionConfig
    )
    from .configuration_model import (
        get_configuration_manager,
        ConfigLevel,
        SecurityLevel
    )
    from .redshift_connection_model import (
        get_connector,
        ConnectionConfig,
        QueryResult,
        RedshiftUserInfo
    )
    from .database_models import (
        get_database_manager,
        RedshiftCluster,
        User,
        Role,
        UserSession,
        AuditLog
    )
except ImportError as e:
    # Handle missing dependencies gracefully
    import logging
    logging.warning(f"Some models could not be imported: {e}")

__all__ = [
    'get_encryption_manager',
    'get_password_validator', 
    'get_configuration_manager',
    'get_connector',
    'get_database_manager',
    'PasswordPolicy',
    'EncryptionConfig',
    'ConfigLevel',
    'SecurityLevel',
    'ConnectionConfig',
    'QueryResult',
    'RedshiftUserInfo',
    'RedshiftCluster',
    'User',
    'Role',
    'UserSession',
    'AuditLog'
]