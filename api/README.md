# RedshiftManager REST API

## 📚 תיעוד API מקיף

### 🚀 התקנה והפעלה

#### הפעלת השרת
```bash
# הפעלה במצב פיתוח (עם hot reload)
./run_api.sh --dev

# הפעלה במצב production
./run_api.sh --host 0.0.0.0 --port 8000 --workers 4

# הפעלה ישירה עם Python
python api/server.py --dev
```

#### גישה לתיעוד
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 🔐 Authentication

### Login
```http
POST /auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "your_password"
}
```

**Response:**
```json
{
    "success": true,
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "username": "admin",
        "email": "admin@company.com",
        "role": "admin"
    },
    "message": "Login successful",
    "expires_in": 28800
}
```

### הרשאות (Headers)
כל בקשה מאובטחת דורשת:
```http
Authorization: Bearer YOUR_JWT_TOKEN
```

### רמות הרשאה
- **viewer**: גישה לקריאה בלבד
- **analyst**: גישה לביצוע queries ותצוגת נתונים
- **manager**: ניהול משתמשים וגישה מלאה למערכת
- **admin**: גישה מלאה כולל ניהול מערכת

---

## 👤 User Management

### Get Current User Info
```http
GET /auth/me
Authorization: Bearer YOUR_TOKEN
```

### Get All Users (Manager+)
```http
GET /users
Authorization: Bearer YOUR_TOKEN
```

### Create User (Admin Only)
```http
POST /users
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "username": "newuser",
    "email": "newuser@company.com",
    "password": "secure_password",
    "role": "analyst"
}
```

### Logout
```http
POST /auth/logout
Authorization: Bearer YOUR_TOKEN
```

---

## 🧩 Widget Management

### Get Available Widgets
```http
GET /widgets
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
[
    {
        "name": "connection_widget",
        "display_name": "Database Connection",
        "description": "Manage database connections",
        "category": "database",
        "enabled": true,
        "config": {}
    }
]
```

### Get User Widget Preferences
```http
GET /widgets/user-preferences
Authorization: Bearer YOUR_TOKEN
```

### Update Widget Preferences
```http
POST /widgets/user-preferences
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "enabled_widgets": ["connection_widget", "query_widget"],
    "widget_order": ["connection_widget", "query_widget"],
    "widget_configs": {
        "connection_widget": {
            "theme": "dark",
            "auto_connect": true
        }
    }
}
```

### Register External Widget (Admin)
```http
POST /widgets/register
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "name": "custom_widget",
    "class_path": "modules.custom.CustomWidget"
}
```

### Get Widget Configuration
```http
GET /widgets/{widget_name}/config
Authorization: Bearer YOUR_TOKEN
```

### Update Widget Configuration
```http
POST /widgets/{widget_name}/config
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "widget_name": "connection_widget",
    "config": {
        "theme": "dark",
        "auto_connect": true
    },
    "enabled": true
}
```

---

## 🗄️ Database Management

### Test Database Connection
```http
POST /database/test-connection
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "host": "redshift-cluster.amazonaws.com",
    "port": 5439,
    "database": "dev",
    "username": "user",
    "password": "pass",
    "db_type": "redshift",
    "ssl_mode": "require"
}
```

### Get Saved Connections
```http
GET /database/connections
Authorization: Bearer YOUR_TOKEN
```

### Save New Connection
```http
POST /database/connections
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "name": "production_redshift",
    "db_type": "redshift",
    "host": "redshift-cluster.amazonaws.com",
    "port": 5439,
    "database": "prod",
    "username": "analyst",
    "password": "secure_password",
    "ssl_mode": "require",
    "additional_params": {
        "connect_timeout": 30
    }
}
```

### Update Connection
```http
PUT /database/connections/{connection_name}
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "name": "production_redshift",
    "db_type": "redshift",
    "host": "new-cluster.amazonaws.com",
    "port": 5439,
    "database": "prod",
    "username": "analyst",
    "password": "new_password",
    "ssl_mode": "require"
}
```

### Delete Connection
```http
DELETE /database/connections/{connection_name}
Authorization: Bearer YOUR_TOKEN
```

### Execute Query
```http
POST /database/query
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "query": "SELECT * FROM users LIMIT 10",
    "connection_name": "production_redshift",
    "limit": 1000
}
```

**Response:**
```json
{
    "success": true,
    "columns": ["id", "username", "email", "created_at"],
    "rows": [
        [1, "john_doe", "john@company.com", "2024-01-01"],
        [2, "jane_smith", "jane@company.com", "2024-01-02"]
    ],
    "row_count": 2,
    "execution_time_ms": 245.7,
    "message": "Query executed successfully"
}
```

---

## 📊 System Monitoring

### Health Check
```http
GET /health
```

### System Status (Manager+)
```http
GET /system/status
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
    "success": true,
    "message": "System status retrieved",
    "data": {
        "api_status": "running",
        "active_sessions": 3,
        "total_users": 5,
        "widgets_available": 8,
        "uptime": "2h 15m",
        "version": "1.0.0"
    }
}
```

---

## 🔧 Error Handling

### Standard Error Response
```json
{
    "success": false,
    "message": "Error description",
    "timestamp": "2024-07-28T16:30:00.000Z"
}
```

### HTTP Status Codes
- **200**: Success
- **201**: Created
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **422**: Validation Error
- **429**: Rate Limit Exceeded
- **500**: Internal Server Error

### Rate Limiting
- **Limit**: 100 requests per minute per IP
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Reset timestamp

---

## 🛡️ Security Features

### Headers
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'
```

### CORS
- **Allowed Origins**: `http://localhost:8501`, `http://127.0.0.1:8501`
- **Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS
- **Credentials**: Enabled

### JWT Token
- **Algorithm**: HS256
- **Expiration**: 8 hours
- **Automatic Refresh**: Not implemented (logout/login required)

---

## 📝 Usage Examples

### Python Client Example
```python
import requests
import json

# Login
login_response = requests.post('http://localhost:8000/auth/login', json={
    'username': 'admin',
    'password': 'your_password'
})

token = login_response.json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Get widgets
widgets = requests.get('http://localhost:8000/widgets', headers=headers)
print(widgets.json())

# Test database connection
test_result = requests.post('http://localhost:8000/database/test-connection', 
    headers=headers,
    json={
        'host': 'localhost',
        'port': 5432,
        'database': 'testdb',
        'username': 'user',
        'password': 'pass',
        'db_type': 'postgresql'
    }
)

print(test_result.json())
```

### JavaScript/Fetch Example
```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        username: 'admin',
        password: 'your_password'
    })
});

const loginData = await loginResponse.json();
const token = loginData.token;

// Get user info
const userResponse = await fetch('http://localhost:8000/auth/me', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});

const userData = await userResponse.json();
console.log(userData);
```

### cURL Examples
```bash
# Login
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "your_password"}'

# Get widgets (replace TOKEN with actual JWT token)
curl -X GET "http://localhost:8000/widgets" \
     -H "Authorization: Bearer TOKEN"

# Execute query
curl -X POST "http://localhost:8000/database/query" \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
         "query": "SELECT COUNT(*) FROM users",
         "connection_name": "my_db",
         "limit": 1000
     }'
```

---

## 🚨 Production Deployment

### Environment Variables
```bash
export APP_ENV=production
export JWT_SECRET_KEY=your-super-secret-key-here
export CORS_ORIGINS=https://your-domain.com
export LOG_LEVEL=INFO
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "api/server.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Nginx Configuration
```nginx
upstream redshift_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.redshiftmanager.com;

    location / {
        proxy_pass http://redshift_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📋 Testing

### Health Check Test
```bash
curl http://localhost:8000/health
```

Expected: `{"status": "healthy", "timestamp": "...", "version": "1.0.0"}`

### Authentication Test
```bash
# Should return 401
curl http://localhost:8000/auth/me

# Should return user info after login
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"password"}'
```

---

## 🔄 API Versioning

Current Version: **1.0.0**

Future versions will use URL versioning:
- `/v1/auth/login`
- `/v2/auth/login`

---

## 📞 Support

- **GitHub Issues**: [RedshiftManager Issues](https://github.com/redshift-manager/issues)
- **Documentation**: Built-in Swagger UI at `/docs`
- **Logs**: Check `logs/` directory for detailed API logs