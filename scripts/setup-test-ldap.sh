#!/bin/bash

# MultiDBManager Test LDAP Setup Script
echo "🔧 Setting up test LDAP environment for MultiDBManager..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create config directory if it doesn't exist
mkdir -p config

echo "🚀 Starting test LDAP server..."
docker-compose -f docker-compose.test-ldap.yml up -d

echo "⏳ Waiting for LDAP server to be ready..."
sleep 15

# Check if LDAP is running
if docker ps | grep -q "test-ldap"; then
    echo "✅ LDAP server is running!"
    echo ""
    echo "📋 LDAP Connection Details:"
    echo "   Server: localhost:389"
    echo "   Base DN: dc=multidb,dc=local"
    echo "   Admin DN: cn=admin,dc=multidb,dc=local"
    echo "   Admin Password: admin123"
    echo ""
    echo "👥 Test Users:"
    echo "   john.doe / password123"
    echo "   jane.smith / password123"
    echo "   admin.user / admin123"
    echo ""
    echo "🏷️ Test Groups:"
    echo "   db_admins, db_users, analysts, developers"
    echo ""
    echo "🌐 Web Admin Interface:"
    echo "   http://localhost:8080"
    echo "   Login: cn=admin,dc=multidb,dc=local"
    echo "   Password: admin123"
    echo ""
    echo "🧪 To test LDAP connection:"
    echo "   ldapsearch -x -H ldap://localhost:389 -D 'cn=admin,dc=multidb,dc=local' -w admin123 -b 'dc=multidb,dc=local'"
else
    echo "❌ LDAP server failed to start. Check logs:"
    docker-compose -f docker-compose.test-ldap.yml logs
    exit 1
fi