-- MultiDBManager SQLite Database Schema
-- Comprehensive schema for multi-database management system

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- ================================
-- CORE TABLES
-- ================================

-- Servers configuration
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    database_name TEXT NOT NULL,
    database_type TEXT NOT NULL CHECK (database_type IN ('postgresql', 'mysql', 'redis', 'redshift')),
    username TEXT,
    password TEXT, -- Should be encrypted in production
    environment TEXT DEFAULT 'Development',
    status TEXT DEFAULT 'Unknown',
    last_test_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Scanner settings as JSON for flexibility
    scanner_settings JSON,
    
    -- Connection metadata
    connection_metadata JSON
);

-- Users discovered from databases
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    normalized_username TEXT NOT NULL, -- For global user management
    user_type TEXT DEFAULT 'unknown',
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- User metadata and permissions as JSON
    metadata JSON,
    permissions_data JSON,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    UNIQUE(server_id, username)
);

-- Create index for fast global user lookups
CREATE INDEX IF NOT EXISTS idx_users_normalized ON users(normalized_username);
CREATE INDEX IF NOT EXISTS idx_users_server ON users(server_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Roles discovered from databases
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    role_name TEXT NOT NULL,
    description TEXT,
    permissions JSON,
    members_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    UNIQUE(server_id, role_name)
);

-- Groups discovered from databases
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    description TEXT,
    members JSON,
    roles JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    UNIQUE(server_id, group_name)
);

-- Tables discovered from databases
CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    schema_name TEXT DEFAULT 'public',
    row_count INTEGER DEFAULT 0,
    size_mb REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Table metadata
    metadata JSON,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    UNIQUE(server_id, schema_name, table_name)
);

-- ================================
-- OPERATIONAL HISTORY
-- ================================

-- Scan history for tracking database scans
CREATE TABLE IF NOT EXISTS scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    scan_type TEXT NOT NULL CHECK (scan_type IN ('full', 'users', 'roles', 'tables', 'permissions')),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    duration_ms INTEGER,
    
    -- Scan results and statistics
    results JSON,
    error_message TEXT,
    
    -- Counts for quick access
    users_found INTEGER DEFAULT 0,
    roles_found INTEGER DEFAULT 0,
    tables_found INTEGER DEFAULT 0,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scan_history_server ON scan_history(server_id);
CREATE INDEX IF NOT EXISTS idx_scan_history_type ON scan_history(scan_type);

-- User activity and changes tracking
CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('created', 'modified', 'deleted', 'login', 'logout', 'permission_change')),
    details JSON,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Manual vs automatic detection
    detected_manually BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_activity_server ON user_activity(server_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity(username);
CREATE INDEX IF NOT EXISTS idx_user_activity_timestamp ON user_activity(timestamp);

-- ================================
-- SECURITY AND PERMISSIONS
-- ================================

-- Security events and alerts
CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER,
    event_type TEXT NOT NULL CHECK (event_type IN ('unauthorized_access', 'permission_escalation', 'suspicious_activity', 'failed_login', 'manual_user_detected')),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    username TEXT,
    description TEXT NOT NULL,
    details JSON,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_security_events_server ON security_events(server_id);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity);
CREATE INDEX IF NOT EXISTS idx_security_events_resolved ON security_events(resolved);

-- Manual user detections for security monitoring
CREATE TABLE IF NOT EXISTS manual_user_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'locked', 'investigated')),
    action_taken TEXT,
    notes TEXT,
    
    -- Risk assessment
    risk_level TEXT DEFAULT 'medium' CHECK (risk_level IN ('low', 'medium', 'high')),
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
);

-- ================================
-- OPERATIONAL FEATURES
-- ================================

-- Backup operations
CREATE TABLE IF NOT EXISTS backup_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER,
    backup_type TEXT NOT NULL CHECK (backup_type IN ('full', 'incremental', 'users_only', 'permissions_only')),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    file_path TEXT,
    file_size_mb REAL,
    compression_ratio REAL,
    error_message TEXT,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE SET NULL
);

-- System configuration and settings
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    data_type TEXT DEFAULT 'string' CHECK (data_type IN ('string', 'integer', 'boolean', 'json')),
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(category, setting_key)
);

-- Session management for web interface
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_identifier TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    session_data JSON,
    
    -- Session metadata
    ip_address TEXT,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- ================================
-- VIEWS FOR COMMON QUERIES
-- ================================

-- Global users view - unified view across all servers
CREATE VIEW IF NOT EXISTS global_users AS
SELECT 
    u.id,
    u.username,
    u.normalized_username,
    u.user_type,
    u.is_active,
    u.last_login,
    s.name as server_name,
    s.database_type,
    s.environment,
    COUNT(DISTINCT s2.id) as appears_on_servers
FROM users u
JOIN servers s ON u.server_id = s.id
LEFT JOIN users u2 ON u.normalized_username = u2.normalized_username AND u2.id != u.id
LEFT JOIN servers s2 ON u2.server_id = s2.id
GROUP BY u.id, u.username, u.normalized_username, u.user_type, u.is_active, u.last_login, s.name, s.database_type, s.environment;

-- Server summary view
CREATE VIEW IF NOT EXISTS server_summary AS
SELECT 
    s.id,
    s.name,
    s.host,
    s.database_type,
    s.environment,
    s.status,
    COUNT(DISTINCT u.id) as total_users,
    COUNT(DISTINCT CASE WHEN u.is_active THEN u.id END) as active_users,
    COUNT(DISTINCT r.id) as total_roles,
    COUNT(DISTINCT t.id) as total_tables,
    MAX(sh.completed_at) as last_scan_at
FROM servers s
LEFT JOIN users u ON s.id = u.server_id
LEFT JOIN roles r ON s.id = r.server_id
LEFT JOIN tables t ON s.id = t.server_id
LEFT JOIN scan_history sh ON s.id = sh.server_id AND sh.status = 'completed'
GROUP BY s.id, s.name, s.host, s.database_type, s.environment, s.status;

-- Recent activity view
CREATE VIEW IF NOT EXISTS recent_activity AS
SELECT 
    ua.id,
    ua.username,
    ua.action,
    ua.timestamp,
    s.name as server_name,
    s.database_type,
    ua.detected_manually,
    ua.details
FROM user_activity ua
JOIN servers s ON ua.server_id = s.id
ORDER BY ua.timestamp DESC;

-- Security dashboard view
CREATE VIEW IF NOT EXISTS security_dashboard AS
SELECT 
    se.id,
    se.event_type,
    se.severity,
    se.username,
    se.description,
    se.created_at,
    se.resolved,
    s.name as server_name,
    s.environment
FROM security_events se
LEFT JOIN servers s ON se.server_id = s.id
WHERE se.resolved = FALSE
ORDER BY 
    CASE se.severity 
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    se.created_at DESC;

-- ================================
-- INDEXES FOR PERFORMANCE
-- ================================

CREATE INDEX IF NOT EXISTS idx_servers_name ON servers(name);
CREATE INDEX IF NOT EXISTS idx_servers_type ON servers(database_type);
CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);

CREATE INDEX IF NOT EXISTS idx_roles_server ON roles(server_id);
CREATE INDEX IF NOT EXISTS idx_groups_server ON groups(server_id);
CREATE INDEX IF NOT EXISTS idx_tables_server ON tables(server_id);

CREATE INDEX IF NOT EXISTS idx_backup_operations_server ON backup_operations(server_id);
CREATE INDEX IF NOT EXISTS idx_backup_operations_status ON backup_operations(status);

-- ================================
-- TRIGGERS FOR DATA CONSISTENCY
-- ================================

-- Update server updated_at timestamp
CREATE TRIGGER update_servers_timestamp 
    AFTER UPDATE ON servers
BEGIN
    UPDATE servers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update user activity when users are modified
CREATE TRIGGER log_user_changes
    AFTER UPDATE ON users
    WHEN OLD.is_active != NEW.is_active OR OLD.user_type != NEW.user_type
BEGIN
    INSERT INTO user_activity (server_id, username, action, details)
    VALUES (NEW.server_id, NEW.username, 'modified', 
            json_object('old_active', OLD.is_active, 'new_active', NEW.is_active,
                       'old_type', OLD.user_type, 'new_type', NEW.user_type));
END;

-- Clean up expired sessions
CREATE TRIGGER cleanup_expired_sessions
    AFTER INSERT ON user_sessions
BEGIN
    DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
END;

-- ================================
-- INITIAL DATA
-- ================================

-- Default system settings
INSERT INTO system_settings (category, setting_key, setting_value, data_type, description) VALUES
('ui', 'theme', 'light', 'string', 'UI theme preference'),
('security', 'session_timeout_minutes', '60', 'integer', 'Session timeout in minutes'),
('security', 'max_failed_connections', '5', 'integer', 'Maximum failed connection attempts'),
('scanning', 'default_scan_interval_hours', '24', 'integer', 'Default scan interval in hours'),
('scanning', 'auto_detect_manual_users', 'true', 'boolean', 'Automatically detect manually created users'),
('alerts', 'email_notifications', 'false', 'boolean', 'Enable email notifications'),
('backup', 'auto_backup_enabled', 'false', 'boolean', 'Enable automatic backups'),
('backup', 'backup_retention_days', '30', 'integer', 'Backup retention period in days');

-- Create full-text search for users if needed
-- CREATE VIRTUAL TABLE users_fts USING fts5(username, metadata, content='users', content_rowid='id');

-- Performance optimization
ANALYZE;