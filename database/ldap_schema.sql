-- LDAP Integration Tables for MultiDBManager
-- These tables store LDAP user information and sync history

-- LDAP Users table
CREATE TABLE IF NOT EXISTS ldap_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    dn VARCHAR(500) NOT NULL,
    email VARCHAR(255),
    display_name VARCHAR(255),
    given_name VARCHAR(255),
    surname VARCHAR(255),
    groups_data TEXT, -- JSON array of groups
    is_active BOOLEAN DEFAULT 1,
    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LDAP Authentication Log
CREATE TABLE IF NOT EXISTS ldap_auth_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL,
    success BOOLEAN NOT NULL,
    message TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LDAP Synchronization Log
CREATE TABLE IF NOT EXISTS ldap_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_users INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    error_details TEXT,
    duration_seconds INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LDAP Configuration table
CREATE TABLE IF NOT EXISTS ldap_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_name VARCHAR(255) NOT NULL UNIQUE,
    server VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 389,
    use_ssl BOOLEAN DEFAULT 0,
    base_dn VARCHAR(500) NOT NULL,
    bind_dn VARCHAR(500),
    bind_password_encrypted TEXT,
    user_filter VARCHAR(500) DEFAULT '(uid={username})',
    group_filter VARCHAR(500) DEFAULT '(member={user_dn})',
    user_search_base VARCHAR(500),
    group_search_base VARCHAR(500),
    timeout_seconds INTEGER DEFAULT 10,
    auto_sync BOOLEAN DEFAULT 1,
    sync_interval_hours INTEGER DEFAULT 24,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User-Server mapping for LDAP users
CREATE TABLE IF NOT EXISTS ldap_user_servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ldap_user_id INTEGER NOT NULL,
    server_id INTEGER NOT NULL,
    database_username VARCHAR(255),
    permissions_granted TEXT, -- JSON of granted permissions
    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ldap_user_id) REFERENCES ldap_users(id) ON DELETE CASCADE,
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    UNIQUE(ldap_user_id, server_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ldap_users_username ON ldap_users(username);
CREATE INDEX IF NOT EXISTS idx_ldap_users_email ON ldap_users(email);
CREATE INDEX IF NOT EXISTS idx_ldap_users_last_sync ON ldap_users(last_sync);
CREATE INDEX IF NOT EXISTS idx_ldap_auth_log_username ON ldap_auth_log(username);
CREATE INDEX IF NOT EXISTS idx_ldap_auth_log_timestamp ON ldap_auth_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_ldap_sync_log_timestamp ON ldap_sync_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_ldap_user_servers_ldap_user ON ldap_user_servers(ldap_user_id);
CREATE INDEX IF NOT EXISTS idx_ldap_user_servers_server ON ldap_user_servers(server_id);

-- Views for easier querying
CREATE VIEW IF NOT EXISTS ldap_users_with_servers AS
SELECT 
    lu.id,
    lu.username,
    lu.email,
    lu.display_name,
    lu.is_active,
    lu.last_sync,
    COUNT(lus.server_id) as server_count,
    GROUP_CONCAT(s.name) as servers
FROM ldap_users lu
LEFT JOIN ldap_user_servers lus ON lu.id = lus.ldap_user_id
LEFT JOIN servers s ON lus.server_id = s.id
GROUP BY lu.id, lu.username, lu.email, lu.display_name, lu.is_active, lu.last_sync;

-- View for recent authentication activity
CREATE VIEW IF NOT EXISTS recent_ldap_auth_activity AS
SELECT 
    username,
    success,
    message,
    timestamp,
    CASE WHEN success = 1 THEN '✅ Success' ELSE '❌ Failed' END as status_icon
FROM ldap_auth_log
ORDER BY timestamp DESC
LIMIT 100;

-- View for sync statistics
CREATE VIEW IF NOT EXISTS ldap_sync_statistics AS
SELECT 
    DATE(timestamp) as sync_date,
    COUNT(*) as sync_count,
    SUM(synced_users) as total_synced,
    SUM(errors) as total_errors,
    AVG(duration_seconds) as avg_duration
FROM ldap_sync_log
GROUP BY DATE(timestamp)
ORDER BY sync_date DESC;

-- Insert default test configuration for ForumSys
INSERT OR REPLACE INTO ldap_config (
    config_name, server, port, use_ssl, base_dn, bind_dn, bind_password_encrypted,
    user_filter, group_filter, user_search_base, group_search_base,
    timeout_seconds, auto_sync, sync_interval_hours, is_active
) VALUES (
    'forumsys_test',
    'ldap.forumsys.com',
    389,
    0,
    'dc=example,dc=com',
    'cn=read-only-admin,dc=example,dc=com',
    'password', -- In production, this should be encrypted
    '(uid={username})',
    '(member={user_dn})',
    'dc=example,dc=com',
    'dc=example,dc=com',
    10,
    1,
    24,
    1
);

-- Triggers for updating timestamps
CREATE TRIGGER IF NOT EXISTS update_ldap_users_timestamp
    AFTER UPDATE ON ldap_users
BEGIN
    UPDATE ldap_users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_ldap_config_timestamp
    AFTER UPDATE ON ldap_config
BEGIN
    UPDATE ldap_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;