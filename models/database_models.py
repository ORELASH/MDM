"""
RedshiftManager Database Models
Complete SQLAlchemy models for all entities with encryption support.
"""

import os
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from contextlib import contextmanager
import logging

try:
    from sqlalchemy import (
        create_engine, Column, Integer, String, Text, DateTime, Boolean,
        ForeignKey, Table, Index, CheckConstraint, UniqueConstraint,
        Float, JSON, LargeBinary, Enum, event, TIMESTAMP
    )
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import (
        sessionmaker, relationship, Session, scoped_session,
        validates, reconstructor
    )
    from sqlalchemy.dialects.sqlite import DATETIME as SQLITE_DATETIME
    from sqlalchemy.dialects.postgresql import UUID, JSONB, BYTEA
    from sqlalchemy.dialects.mysql import LONGTEXT, MEDIUMTEXT, TINYTEXT
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.hybrid import hybrid_property
    from sqlalchemy import desc, asc, and_, or_, func
    from alembic import command
    from alembic.config import Config
    import uuid
except ImportError as e:
    logging.error(f"SQLAlchemy dependencies missing: {e}")
    raise ImportError("Required packages: SQLAlchemy>=2.0.0, alembic, psycopg2-binary, PyMySQL")

try:
    from .encryption_model import get_encryption_manager
    from .configuration_model import get_configuration_manager
except ImportError:
    # Handle development imports
    get_encryption_manager = None
    get_configuration_manager = None

# Configure logging
logger = logging.getLogger(__name__)

# Base model
Base = declarative_base()


class UserRoleType(PyEnum):
    """User role types."""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    GUEST = "guest"


class ConnectionStatusType(PyEnum):
    """Connection status types."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class AuditActionType(PyEnum):
    """Audit action types."""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    EXPORT = "export"
    IMPORT = "import"
    BACKUP = "backup"
    RESTORE = "restore"
    CONFIG_CHANGE = "config_change"


# Association tables for many-to-many relationships
user_roles_table = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

cluster_users_table = Table(
    'cluster_users',
    Base.metadata,
    Column('cluster_id', Integer, ForeignKey('redshift_clusters.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
)


class TimestampMixin:
    """Mixin for timestamp fields."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EncryptedFieldMixin:
    """Mixin for encrypted fields support."""
    
    def _encrypt_field(self, value: str) -> str:
        """Encrypt a field value."""
        if get_encryption_manager and value:
            return get_encryption_manager().encrypt_string(value)
        return value
    
    def _decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a field value."""
        if get_encryption_manager and encrypted_value:
            try:
                return get_encryption_manager().decrypt_string(encrypted_value)
            except Exception as e:
                logger.warning(f"Failed to decrypt field: {e}")
                return encrypted_value
        return encrypted_value


class User(Base, TimestampMixin, EncryptedFieldMixin):
    """User model with role-based access control."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    force_password_change = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255))  # Encrypted
    preferred_language = Column(String(10), default='en')
    theme = Column(String(20), default='light')
    timezone = Column(String(50), default='UTC')
    
    # Relationships
    roles = relationship('Role', secondary=user_roles_table, back_populates='users')
    sessions = relationship('UserSession', back_populates='user', cascade='all, delete-orphan')
    audit_logs = relationship('AuditLog', back_populates='user')
    clusters = relationship('RedshiftCluster', secondary=cluster_users_table, back_populates='users')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('login_count >= 0', name='check_login_count_positive'),
        CheckConstraint('failed_login_attempts >= 0', name='check_failed_attempts_positive'),
        Index('idx_user_active_username', 'is_active', 'username'),
    )
    
    @hybrid_property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @hybrid_property
    def is_locked(self) -> bool:
        """Check if user is locked."""
        return self.locked_until and self.locked_until > datetime.utcnow()
    
    @hybrid_property
    def password_expired(self) -> bool:
        """Check if password is expired."""
        if not self.password_changed_at:
            return True
        
        # Get password expiry from config (default 90 days)
        expiry_days = 90
        if get_configuration_manager:
            expiry_days = get_configuration_manager().get('security.password_expiry_days', 90)
        
        expiry_date = self.password_changed_at + timedelta(days=expiry_days)
        return datetime.utcnow() > expiry_date
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")
        return email.lower()
    
    @validates('username')
    def validate_username(self, key, username):
        """Validate username."""
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not username.isalnum() and '_' not in username:
            raise ValueError("Username can only contain alphanumeric characters and underscores")
        return username.lower()
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has specific role."""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if user has specific permission."""
        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        return False
    
    def get_encrypted_two_factor_secret(self) -> Optional[str]:
        """Get encrypted two-factor secret."""
        return self.two_factor_secret
    
    def set_two_factor_secret(self, secret: str) -> None:
        """Set encrypted two-factor secret."""
        self.two_factor_secret = self._encrypt_field(secret)
    
    def get_two_factor_secret(self) -> Optional[str]:
        """Get decrypted two-factor secret."""
        if self.two_factor_secret:
            return self._decrypt_field(self.two_factor_secret)
        return None
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Role(Base, TimestampMixin):
    """Role model for RBAC."""
    
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200))
    description = Column(Text)
    is_system = Column(Boolean, default=False)  # System roles cannot be deleted
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON)  # JSON array of permission names
    
    # Relationships
    users = relationship('User', secondary=user_roles_table, back_populates='roles')
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if role has specific permission."""
        if not self.permissions:
            return False
        return permission_name in self.permissions
    
    def add_permission(self, permission_name: str) -> None:
        """Add permission to role."""
        if not self.permissions:
            self.permissions = []
        if permission_name not in self.permissions:
            self.permissions.append(permission_name)
    
    def remove_permission(self, permission_name: str) -> None:
        """Remove permission from role."""
        if self.permissions and permission_name in self.permissions:
            self.permissions.remove(permission_name)
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class RedshiftCluster(Base, TimestampMixin, EncryptedFieldMixin):
    """Redshift cluster configuration model."""
    
    __tablename__ = 'redshift_clusters'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    host = Column(String(500), nullable=False)
    port = Column(Integer, default=5439, nullable=False)
    database = Column(String(200), nullable=False)
    username = Column(String(200), nullable=False)
    password = Column(Text)  # Encrypted
    ssl_mode = Column(String(20), default='require')
    connection_timeout = Column(Integer, default=30)
    query_timeout = Column(Integer, default=300)
    max_connections = Column(Integer, default=10)
    description = Column(Text)
    status = Column(Enum(ConnectionStatusType), default=ConnectionStatusType.INACTIVE)
    last_connection_test = Column(DateTime)
    connection_test_result = Column(Text)
    is_active = Column(Boolean, default=True)
    environment = Column(String(50), default='development')  # dev, staging, production
    
    # AWS specific fields
    aws_region = Column(String(50))
    cluster_identifier = Column(String(200))
    node_type = Column(String(50))
    number_of_nodes = Column(Integer)
    
    # Relationships
    users = relationship('User', secondary=cluster_users_table, back_populates='clusters')
    query_history = relationship('QueryHistory', back_populates='cluster', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('port > 0 AND port <= 65535', name='check_valid_port'),
        CheckConstraint('connection_timeout > 0', name='check_positive_timeout'),
        CheckConstraint('max_connections > 0', name='check_positive_connections'),
        UniqueConstraint('name', name='uq_cluster_name'),
        Index('idx_cluster_status_active', 'status', 'is_active'),
    )
    
    @validates('host')
    def validate_host(self, key, host):
        """Validate host format."""
        if not host or len(host.strip()) == 0:
            raise ValueError("Host cannot be empty")
        return host.strip()
    
    @validates('database')
    def validate_database(self, key, database):
        """Validate database name."""
        if not database or len(database.strip()) == 0:
            raise ValueError("Database name cannot be empty")
        return database.strip()
    
    def get_connection_string(self, include_password: bool = False) -> str:
        """Generate connection string."""
        password = self.get_password() if include_password else "***"
        return f"postgresql://{self.username}:{password}@{self.host}:{self.port}/{self.database}"
    
    def set_password(self, password: str) -> None:
        """Set encrypted password."""
        self.password = self._encrypt_field(password)
    
    def get_password(self) -> Optional[str]:
        """Get decrypted password."""
        if self.password:
            return self._decrypt_field(self.password)
        return None
    
    def __repr__(self):
        return f"<RedshiftCluster(id={self.id}, name='{self.name}', host='{self.host}')>"


class UserSession(Base, TimestampMixin):
    """User session tracking."""
    
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_token = Column(String(500), unique=True, nullable=False, index=True)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Session metadata
    login_method = Column(String(50))  # password, 2fa, sso
    device_fingerprint = Column(String(500))
    location = Column(String(200))
    
    # Relationships
    user = relationship('User', back_populates='sessions')
    
    # Constraints
    __table_args__ = (
        Index('idx_session_token_active', 'session_token', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
        Index('idx_session_user_active', 'user_id', 'is_active'),
    )
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    @hybrid_property
    def is_valid(self) -> bool:
        """Check if session is valid."""
        return self.is_active and not self.is_expired
    
    def extend_session(self, hours: int = 24) -> None:
        """Extend session expiry."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity = datetime.utcnow()
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class AuditLog(Base, TimestampMixin):
    """Comprehensive audit logging."""
    
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), index=True)
    session_id = Column(Integer, ForeignKey('user_sessions.id', ondelete='SET NULL'))
    action = Column(Enum(AuditActionType), nullable=False, index=True)
    resource_type = Column(String(100))  # user, cluster, query, etc.
    resource_id = Column(String(100))
    details = Column(JSON)  # Action-specific details
    ip_address = Column(String(45))
    user_agent = Column(Text)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    execution_time = Column(Float)  # Seconds
    
    # Relationships
    user = relationship('User', back_populates='audit_logs')
    
    # Constraints
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_timestamp', 'created_at'),
        Index('idx_audit_success', 'success'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"


class QueryHistory(Base, TimestampMixin):
    """Query execution history."""
    
    __tablename__ = 'query_history'
    
    id = Column(Integer, primary_key=True)
    cluster_id = Column(Integer, ForeignKey('redshift_clusters.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), index=True)
    query_text = Column(Text, nullable=False)
    query_hash = Column(String(64), index=True)  # MD5 hash for duplicate detection
    execution_time = Column(Float)  # Seconds
    rows_affected = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    query_plan = Column(Text)
    
    # Query metadata
    query_type = Column(String(20))  # SELECT, INSERT, UPDATE, DELETE, etc.
    tables_accessed = Column(JSON)  # List of table names
    complexity_score = Column(Integer)  # 1-10 complexity rating
    
    # Relationships
    cluster = relationship('RedshiftCluster', back_populates='query_history')
    user = relationship('User')
    
    # Constraints
    __table_args__ = (
        Index('idx_query_cluster_user', 'cluster_id', 'user_id'),
        Index('idx_query_timestamp', 'created_at'),
        Index('idx_query_hash', 'query_hash'),
        Index('idx_query_type', 'query_type'),
        Index('idx_query_success', 'success'),
    )
    
    @validates('query_text')
    def validate_query_text(self, key, query_text):
        """Validate query text."""
        if not query_text or len(query_text.strip()) == 0:
            raise ValueError("Query text cannot be empty")
        return query_text.strip()
    
    def generate_query_hash(self) -> str:
        """Generate MD5 hash of normalized query."""
        import hashlib
        normalized = self.query_text.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def __repr__(self):
        return f"<QueryHistory(id={self.id}, cluster_id={self.cluster_id}, type='{self.query_type}')>"


class SystemSettings(Base, TimestampMixin):
    """System-wide settings storage."""
    
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(Text)
    data_type = Column(String(50), default='string')  # string, integer, boolean, json
    description = Column(Text)
    category = Column(String(100), index=True)
    is_encrypted = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)  # System settings cannot be deleted
    
    # Constraints
    __table_args__ = (
        Index('idx_settings_category', 'category'),
        Index('idx_settings_system', 'is_system'),
    )
    
    def get_typed_value(self) -> Any:
        """Get value converted to appropriate type."""
        if not self.value:
            return None
        
        try:
            if self.data_type == 'integer':
                return int(self.value)
            elif self.data_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes', 'on')
            elif self.data_type == 'json':
                return json.loads(self.value)
            else:
                return self.value
        except (ValueError, json.JSONDecodeError):
            return self.value
    
    def set_typed_value(self, value: Any) -> None:
        """Set value with type conversion."""
        if value is None:
            self.value = None
        elif isinstance(value, (dict, list)):
            self.value = json.dumps(value)
            self.data_type = 'json'
        elif isinstance(value, bool):
            self.value = str(value).lower()
            self.data_type = 'boolean'
        elif isinstance(value, int):
            self.value = str(value)
            self.data_type = 'integer'
        else:
            self.value = str(value)
            self.data_type = 'string'
    
    def __repr__(self):
        return f"<SystemSettings(key='{self.key}', value='{self.value}')>"


class DatabaseManager:
    """Database management and operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or self._get_database_url()
        self.engine = self._create_engine()
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
        # Set database-specific event listeners
        if 'sqlite' in self.database_url:
            event.listen(Engine, "connect", self._set_sqlite_pragma)
        elif 'postgresql' in self.database_url:
            event.listen(Engine, "connect", self._set_postgresql_settings)
        elif 'mysql' in self.database_url:
            event.listen(Engine, "connect", self._set_mysql_settings)
    
    def _get_database_url(self) -> str:
        """Get database URL from configuration."""
        try:
            if get_configuration_manager:
                config = get_configuration_manager()
                db_type = config.get('database.type', 'sqlite')
                
                if db_type == 'sqlite':
                    db_name = config.get('database.name', 'redshift_manager.db')
                    db_path = config.get('database.path', './data/')
                    return f"sqlite:///{db_path}{db_name}"
                    
                elif db_type == 'postgresql':
                    host = config.get('database.host', 'localhost')
                    port = config.get('database.port', 5432)
                    username = config.get('database.username', 'postgres')
                    password = config.get('database.password', '')
                    database = config.get('database.database', 'redshift_manager')
                    
                    # Handle password encoding for special characters
                    if password:
                        from urllib.parse import quote_plus
                        password = quote_plus(password)
                    
                    return f"postgresql://{username}:{password}@{host}:{port}/{database}"
                    
                elif db_type == 'mysql':
                    host = config.get('database.host', 'localhost')
                    port = config.get('database.port', 3306)
                    username = config.get('database.username', 'root')
                    password = config.get('database.password', '')
                    database = config.get('database.database', 'redshift_manager')
                    charset = config.get('database.charset', 'utf8mb4')
                    
                    # Handle password encoding for special characters
                    if password:
                        from urllib.parse import quote_plus
                        password = quote_plus(password)
                    
                    return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}"
                    
        except Exception as e:
            logger.warning(f"Failed to get database configuration: {e}, using default SQLite")
        
        # Default to SQLite
        return "sqlite:///data/redshift_manager.db"
    
    def _create_engine(self):
        """Create database engine with appropriate settings."""
        if 'sqlite' in self.database_url:
            # SQLite-specific settings
            return create_engine(
                self.database_url,
                poolclass=StaticPool,
                connect_args={
                    'check_same_thread': False,
                    'timeout': 30
                },
                echo=False
            )
        elif 'postgresql' in self.database_url:
            # PostgreSQL-specific settings
            return create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=False,
                connect_args={
                    "application_name": "RedshiftManager",
                    "options": "-c timezone=UTC"
                }
            )
        elif 'mysql' in self.database_url:
            # MySQL-specific settings
            return create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=False,
                connect_args={
                    "charset": "utf8mb4",
                    "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                    "autocommit": False
                }
            )
        else:
            # Generic database settings
            return create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False
            )
    
    def _set_sqlite_pragma(self, dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance and integrity."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
    
    def _set_postgresql_settings(self, dbapi_connection, connection_record):
        """Set PostgreSQL session settings for better performance."""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET timezone = 'UTC'")
            cursor.execute("SET statement_timeout = '300s'")
            cursor.execute("SET lock_timeout = '10s'")
            cursor.execute("SET idle_in_transaction_session_timeout = '600s'")
            dbapi_connection.commit()
        except Exception as e:
            logger.warning(f"Failed to set PostgreSQL settings: {e}")
            dbapi_connection.rollback()
        finally:
            cursor.close()
    
    def _set_mysql_settings(self, dbapi_connection, connection_record):
        """Set MySQL session settings for better performance and compatibility."""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
            cursor.execute("SET SESSION time_zone = '+00:00'")
            cursor.execute("SET SESSION wait_timeout = 28800")
            cursor.execute("SET SESSION interactive_timeout = 28800")
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 50")
            cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            dbapi_connection.commit()
        except Exception as e:
            logger.warning(f"Failed to set MySQL settings: {e}")
            dbapi_connection.rollback()
        finally:
            cursor.close()
    
    def create_all_tables(self) -> None:
        """Create all database tables."""
        try:
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            # Initialize default data
            self._create_default_data()
            
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def _create_default_data(self) -> None:
        """Create default roles and system settings."""
        session = self.Session()
        
        try:
            # Create default roles if they don't exist
            default_roles = [
                {
                    'name': 'admin',
                    'display_name': 'Administrator',
                    'description': 'Full system access',
                    'is_system': True,
                    'permissions': [
                        'user.create', 'user.read', 'user.update', 'user.delete',
                        'cluster.create', 'cluster.read', 'cluster.update', 'cluster.delete',
                        'query.execute', 'query.history', 'query.export',
                        'system.config', 'system.audit', 'system.backup'
                    ]
                },
                {
                    'name': 'manager',
                    'display_name': 'Manager',
                    'description': 'Manage clusters and users',
                    'is_system': True,
                    'permissions': [
                        'user.create', 'user.read', 'user.update',
                        'cluster.create', 'cluster.read', 'cluster.update',
                        'query.execute', 'query.history', 'query.export'
                    ]
                },
                {
                    'name': 'analyst',
                    'display_name': 'Data Analyst',
                    'description': 'Execute queries and export data',
                    'is_system': True,
                    'permissions': [
                        'cluster.read', 'query.execute', 'query.history', 'query.export'
                    ]
                },
                {
                    'name': 'viewer',
                    'display_name': 'Viewer',
                    'description': 'Read-only access',
                    'is_system': True,
                    'permissions': [
                        'cluster.read', 'query.history'
                    ]
                }
            ]
            
            for role_data in default_roles:
                existing_role = session.query(Role).filter_by(name=role_data['name']).first()
                if not existing_role:
                    role = Role(**role_data)
                    session.add(role)
            
            # Create default system settings
            default_settings = [
                {
                    'key': 'app.version',
                    'value': '1.0.0',
                    'description': 'Application version',
                    'category': 'system',
                    'is_system': True
                },
                {
                    'key': 'security.password_min_length',
                    'value': '12',
                    'data_type': 'integer',
                    'description': 'Minimum password length',
                    'category': 'security'
                },
                {
                    'key': 'security.session_timeout',
                    'value': '3600',
                    'data_type': 'integer',
                    'description': 'Session timeout in seconds',
                    'category': 'security'
                }
            ]
            
            for setting_data in default_settings:
                existing_setting = session.query(SystemSettings).filter_by(key=setting_data['key']).first()
                if not existing_setting:
                    setting = SystemSettings(**setting_data)
                    session.add(setting)
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create default data: {e}")
            raise
        finally:
            session.close()
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.Session()
    
    def close_session(self, session: Session) -> None:
        """Close database session."""
        session.close()
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def backup_database(self, backup_path: str) -> bool:
        """Backup database to file."""
        try:
            if 'sqlite' in self.database_url:
                import shutil
                db_path = self.database_url.replace('sqlite:///', '')
                shutil.copy2(db_path, backup_path)
                return True
            else:
                # For PostgreSQL, would use pg_dump
                logger.warning("PostgreSQL backup not implemented")
                return False
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup file."""
        try:
            if 'sqlite' in self.database_url:
                import shutil
                db_path = self.database_url.replace('sqlite:///', '')
                shutil.copy2(backup_path, db_path)
                return True
            else:
                # For PostgreSQL, would use pg_restore
                logger.warning("PostgreSQL restore not implemented")
                return False
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.session_scope() as session:
                stats = {
                    'users': session.query(func.count(User.id)).scalar(),
                    'roles': session.query(func.count(Role.id)).scalar(),
                    'clusters': session.query(func.count(RedshiftCluster.id)).scalar(),
                    'active_sessions': session.query(func.count(UserSession.id)).filter(
                        UserSession.is_active == True,
                        UserSession.expires_at > datetime.utcnow()
                    ).scalar(),
                    'audit_logs': session.query(func.count(AuditLog.id)).scalar(),
                    'query_history': session.query(func.count(QueryHistory.id)).scalar()
                }
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager(database_url: Optional[str] = None) -> DatabaseManager:
    """Get global database manager instance."""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager(database_url)
    return _database_manager


# Convenience functions
def init_database(database_url: Optional[str] = None) -> DatabaseManager:
    """Initialize database and create tables."""
    db_manager = get_database_manager(database_url)
    db_manager.create_all_tables()
    return db_manager


if __name__ == "__main__":
    # Example usage
    db_manager = init_database()
    
    with db_manager.session_scope() as session:
        # Create a test user
        admin_role = session.query(Role).filter_by(name='admin').first()
        
        if admin_role:
            test_user = User(
                username='admin',
                email='admin@redshiftmanager.com',
                password_hash='hashed_password_here',
                first_name='System',
                last_name='Administrator'
            )
            test_user.roles.append(admin_role)
            session.add(test_user)
            
            print("Test user created successfully")
        
        # Get database stats
        stats = db_manager.get_database_stats()
        print(f"Database stats: {stats}")