# Online LDAP Testing Services

## 1. FreeIPA Demo (Red Hat)
- **URL**: https://www.freeipa.org/page/Demo
- **Server**: ipa.demo1.freeipa.org
- **Port**: 636 (LDAPS)
- **Base DN**: dc=demo1,dc=freeipa,dc=org
- **Users**: admin / Secret123, testuser / password
- **Status**: Available for testing

## 2. ForumSys Public LDAP
- **Server**: ldap.forumsys.com
- **Port**: 389
- **Base DN**: dc=example,dc=com
- **Users**: 
  - cn=read-only-admin,dc=example,dc=com / password
  - uid=tesla,dc=example,dc=com / password
  - uid=einstein,dc=example,dc=com / password
- **Groups**: mathematicians, scientists
- **Status**: Free, public testing server

## 3. OpenLDAP Public Test Server
- **Server**: ldap.jumpcloud.com
- **Port**: 389
- **Base DN**: o=5be4c382c583e54de6a3ff52,dc=jumpcloud,dc=com
- **Note**: Requires registration at JumpCloud

## 4. Directory-as-a-Service (Testing)
- **AWS Directory Service**: 30-day free trial
- **Azure AD Domain Services**: Credit-based trial
- **Google Cloud Identity**: Free tier available

## Configuration for MultiDBManager

```python
# Example LDAP configuration for testing
LDAP_CONFIG = {
    'server': 'ldap.forumsys.com',
    'port': 389,
    'use_ssl': False,
    'base_dn': 'dc=example,dc=com',
    'bind_dn': 'cn=read-only-admin,dc=example,dc=com',
    'bind_password': 'password',
    'user_filter': '(uid={username})',
    'group_filter': '(member={user_dn})'
}
```