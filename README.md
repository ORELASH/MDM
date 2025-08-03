# MultiDBManager v2.0 - Universal Database Management System

🚀 **Universal Multi-Database Administration Tool** with real-time user and role management capabilities across multiple database platforms.

---

## 🌟 Key Features

### 🔐 Multi-Database User Management
- **PostgreSQL**: Full role-based access control with inheritance
- **MySQL**: Native roles (8.0+) and privilege-based management (5.7)  
- **Redis**: ACL user management with permission categories
- **Amazon Redshift**: AWS-integrated user and role management

### 👥 Advanced Role Management
- **Bidirectional Control**: Manage from user perspective or role perspective
- **Real-time Operations**: Live SQL execution with immediate feedback
- **Visual Interface**: Intuitive drag-and-drop style role assignment
- **Comprehensive Permissions**: Granular control over database access

### 🖥️ Modern User Interface
- **Live Database Scanning**: Real data from actual database connections
- **Interactive Management**: 5-column layout with Edit, Permissions, Roles, and Toggle
- **SQL Transparency**: View executed commands for learning and auditing
- **Responsive Design**: Works across desktop and tablet devices

---

## 🚀 Quick Start

### Prerequisites
```bash
# Required Python packages
pip install streamlit psycopg2-binary pymysql redis pandas plotly

# Database servers (at least one)
- PostgreSQL 10+ / Amazon Redshift
- MySQL 5.7+ / MariaDB 10.2+  
- Redis 6.0+ (for ACL support)
```

### Installation
```bash
git clone <repository-url>
cd RedshiftManager
./run.sh
```

### First Connection
1. **Navigate to**: http://localhost:8501
2. **Go to**: "Servers" tab → "Add Server"  
3. **Select Template**: Choose your database type
4. **Configure**: Host, port, credentials
5. **Test & Scan**: Verify connection and discover users/roles

---

## 📊 Database Support Matrix

| Database | User Management | Role Management | Advanced Features |
|----------|----------------|-----------------|-------------------|
| **PostgreSQL 12-16** | ✅ Full Support | ✅ Native Roles | Role Inheritance, RLS |
| **Amazon Redshift** | ✅ Full Support | ✅ Native Roles | AWS IAM Integration |
| **MySQL 8.0+** | ✅ Full Support | ✅ Native Roles | Dynamic Privileges |
| **MySQL 5.7** | ✅ Full Support | ⚠️ Privilege-Based | Legacy Compatibility |
| **Redis 6.0+** | ✅ ACL Support | ⚠️ Permission Categories | Command Categories |
| **Redis <6.0** | ⚠️ Basic Auth | ❌ Limited | Password-only |

---

## 🛠️ Core Operations

### User Management
```sql
-- Create User (PostgreSQL/Redshift)
CREATE ROLE "new_user" WITH LOGIN PASSWORD 'secure_password';

-- Promote to Admin
ALTER ROLE "new_user" WITH CREATEROLE CREATEDB;

-- Grant Superuser
ALTER ROLE "new_user" WITH SUPERUSER;

-- Disable Account  
ALTER ROLE "new_user" WITH NOLOGIN;
```

### Role Management
```sql
-- Assign Role to User
GRANT "app_role" TO "username";

-- Remove Role from User  
REVOKE "app_role" FROM "username";

-- Create New Role
CREATE ROLE "custom_role";
```

### MySQL Specific
```sql
-- MySQL 8.0+ Role Management
CREATE ROLE 'application_role';
GRANT SELECT, INSERT ON database.* TO 'application_role';
GRANT 'application_role' TO 'username'@'localhost';

-- MySQL 5.7 Legacy Privileges
GRANT SELECT, INSERT, UPDATE ON database.* TO 'username'@'localhost';
```

### Redis ACL
```bash
# Create Redis User with Permissions
ACL SETUSER newuser on >password123 +@read +@write -@dangerous

# Modify User Permissions
ACL SETUSER existinguser +@admin

# Disable User
ACL SETUSER username off
```

---

## 🎯 User Interface Guide

### Main Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│ 🖥️ Server Management                                        │
├─────────────────────────────────────────────────────────────┤
│ [🔍 Servers] [➕ Add Server] [⚙️ Settings]                 │
├─────────────────────────────────────────────────────────────┤
│ 📋 Registered Servers                                       │
│                                                             │
│ production-server | 🟢 Connected | PostgreSQL              │
│ 📊 🐘 POSTGRESQL | 15 tables, 12 users, 8 roles           │
│ [🔍 Test] [📊 Scan] [✏️ Edit] [🗑️ Delete]                 │
│                                                             │
│ ┌─ 📊 Database Structure - production-server ─────────────┐ │
│ │ [📋 Tables] [👥 Users] [🔑 Roles]                      │ │
│ │                                                        │ │
│ │ 👥 Database Users                    [➕ Add New User]  │ │
│ │ ──────────────────────────────────────────────────────  │ │
│ │ 👤 john_doe | admin | 🟢 Active | 🔑 app_role, reader  │ │
│ │ [✏️ Edit] [🔑 Perms] [👥 Roles] [🔴 Disable]           │ │
│ └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### User Management Interface
- **✏️ Edit**: Modify user properties, password, type
- **🔑 Perms**: View current permissions and role memberships  
- **👥 Roles**: Add/remove role assignments
- **🔴/🟢 Toggle**: Enable/disable user account

### Role Management Interface  
- **👥 Members**: View and manage role members
- **➕ Add Member**: Assign users to roles
- **🗑️ Remove**: Remove users from roles

---

## 🔧 Configuration

### Server Templates
```yaml
PostgreSQL:
  host: localhost
  port: 5432
  database: postgres
  username: postgres
  
MySQL:
  host: localhost  
  port: 3306
  database: mysql
  username: root

Redis:
  host: localhost
  port: 6379
  database: "0"
  username: default

Redshift:
  host: cluster.region.redshift.amazonaws.com
  port: 5439  
  database: dev
  username: admin
```

### Environment Variables
```bash
# Optional: Set default database credentials
export POSTGRES_USER=admin
export POSTGRES_PASSWORD=secure123
export MYSQL_USER=root
export MYSQL_PASSWORD=secret456
export REDIS_PASSWORD=redis789
```

---

## 🔒 Security Best Practices

### Connection Security
- **Always use SSL/TLS** for production database connections
- **Rotate credentials regularly** using the built-in password change feature
- **Use dedicated service accounts** with minimal required privileges
- **Enable database audit logging** to track all changes

### User Management Security
- **Follow principle of least privilege** when assigning roles
- **Regular access reviews** using the permissions viewer
- **Strong password policies** (enforced at database level)
- **Account expiration dates** for temporary access

### Operational Security
```sql
-- Example: Create dedicated RedshiftManager service account
CREATE ROLE "redshift_manager" WITH LOGIN PASSWORD 'complex_password_123!';
GRANT CREATEROLE TO "redshift_manager";
GRANT SELECT ON pg_catalog.pg_roles TO "redshift_manager";
GRANT SELECT ON pg_catalog.pg_auth_members TO "redshift_manager";
```

---

## 📈 Performance Optimization

### Large Database Handling
- **Pagination**: For databases with 1000+ users
- **Filtering**: Search and filter capabilities
- **Connection pooling**: Reuse database connections
- **Caching**: Server-side result caching

### Recommended Hardware
```
Minimum Requirements:
- CPU: 2 cores
- RAM: 4GB  
- Storage: 1GB
- Network: 100Mbps

Recommended for Production:
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 10GB SSD
- Network: 1Gbps
```

---

## 🧪 Testing & Quality Assurance

### Automated Testing
```bash
# Run test suite
python -m pytest tests/

# Specific database tests
python -m pytest tests/test_postgresql.py
python -m pytest tests/test_mysql.py  
python -m pytest tests/test_redis.py
```

### Manual Testing Checklist
- [ ] Connect to each supported database type
- [ ] Create user with different privilege levels
- [ ] Assign and revoke roles
- [ ] Test bulk operations with 100+ users
- [ ] Verify SQL injection protection
- [ ] Test connection failure recovery

---

## 🐛 Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Issue: "Connection refused"
Solution: Verify database is running and accepting connections
Check: firewall rules, pg_hba.conf (PostgreSQL), bind-address (MySQL)

# Issue: "Authentication failed"  
Solution: Verify username/password, check database user permissions
Check: User exists and has LOGIN privilege
```

#### Permission Errors
```bash
# Issue: "Permission denied to create role"
Solution: Service account needs CREATEROLE privilege
Fix: GRANT CREATEROLE TO "service_account";

# Issue: "Cannot view pg_roles"
Solution: Service account needs catalog access  
Fix: GRANT SELECT ON pg_catalog.pg_roles TO "service_account";
```

#### Performance Issues
```bash
# Issue: Slow scanning on large databases
Solution: Add database indexes, increase connection timeout
Optimize: CREATE INDEX ON pg_roles(rolname); (PostgreSQL)

# Issue: Memory usage high
Solution: Reduce concurrent operations, restart application
Monitor: System memory usage during scans
```

### Debug Mode
```bash
# Enable debug logging
export STREAMLIT_LOGGER_LEVEL=debug
streamlit run dashboard.py

# Database query logging
export POSTGRES_LOG_STATEMENT=all  # PostgreSQL
export MYSQL_GENERAL_LOG=ON        # MySQL
```

---

## 🚀 Advanced Features

### Custom SQL Execution
```python
# Execute custom queries (admin users only)
def execute_custom_query(server_info, query):
    success, result = execute_sql_command(server_info, query, fetch_results=True)
    return result
```

### Bulk Operations
```python
# Bulk user creation from CSV
import pandas as pd
users_df = pd.read_csv('users.csv')
for _, user in users_df.iterrows():
    create_user(user['username'], user['password'], user['role'])
```

### API Integration
```python
# REST API endpoints (future feature)
POST /api/users          # Create user
PUT  /api/users/{id}     # Update user  
GET  /api/roles/{id}     # Get role members
POST /api/roles/{id}/members  # Add member to role
```

---

## 📚 Additional Resources

### Documentation
- [CHANGELOG.md](CHANGELOG.md) - Version history and feature updates
- [TESTING_PLAN.md](TESTING_PLAN.md) - Comprehensive testing procedures
- [API_REFERENCE.md](API_REFERENCE.md) - Function and API documentation

### Database Documentation
- [PostgreSQL Roles](https://www.postgresql.org/docs/current/user-manag.html)
- [MySQL User Management](https://dev.mysql.com/doc/refman/8.0/en/access-control.html)
- [Redis ACL](https://redis.io/docs/management/security/acl/)
- [Amazon Redshift Users](https://docs.aws.amazon.com/redshift/latest/dg/r_Users.html)

### Community
- **Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share experiences  
- **Contributing**: Guidelines for code contributions
- **Security**: Responsible disclosure process

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:

- Code style and standards
- Testing requirements  
- Pull request process
- Community guidelines

### Development Setup
```bash
# Clone and setup development environment
git clone <repository-url>
cd RedshiftManager
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements-dev.txt
```

---

## 🙏 Acknowledgments

- **Streamlit** - Modern web application framework
- **psycopg2** - PostgreSQL adapter for Python
- **PyMySQL** - Pure Python MySQL client  
- **redis-py** - Redis Python client
- **Community Contributors** - Feature requests and bug reports

---

**RedshiftManager v2.0** - Empowering database administrators with modern, secure, and efficient user management tools.

*For support, questions, or feature requests, please open an issue on our GitHub repository.*