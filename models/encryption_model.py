"""
RedshiftManager Encryption Model
Advanced encryption and security management system with AES-256-GCM.
"""

import os
import base64
import hashlib
import secrets
import re
from typing import Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
import json
from datetime import datetime, timedelta

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    import bcrypt
except ImportError as e:
    logging.error(f"Cryptography dependencies missing: {e}")
    raise ImportError("Required cryptography packages not installed")

# Configure logging
logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ENTERPRISE = "enterprise"


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"


@dataclass
class EncryptionConfig:
    """Encryption configuration settings."""
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_size: int = 32  # 256 bits
    iv_size: int = 16   # 128 bits
    tag_size: int = 16  # 128 bits for GCM
    salt_size: int = 32 # 256 bits
    iterations: int = 100000  # PBKDF2 iterations
    security_level: SecurityLevel = SecurityLevel.HIGH
    key_rotation_days: int = 90
    backup_keys: bool = True
    hardware_security: bool = False


@dataclass
class PasswordPolicy:
    """Password policy configuration."""
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special: bool = True
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    max_login_attempts: int = 5
    lockout_duration: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    password_history: int = 10
    password_expiry_days: int = 90
    force_change_on_first_login: bool = True


class EncryptionManager:
    """Advanced encryption manager with AES-256-GCM support."""
    
    def __init__(self, config: Optional[EncryptionConfig] = None):
        self.config = config or EncryptionConfig()
        self._master_key: Optional[bytes] = None
        self._key_cache: Dict[str, bytes] = {}
        self._backend = default_backend()
        
        # Initialize master key
        self._initialize_master_key()
    
    def _initialize_master_key(self) -> None:
        """Initialize or load the master encryption key."""
        key_file = Path("data/.master.key")
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    encrypted_key = f.read()
                # In production, this would use hardware security module
                self._master_key = self._decrypt_master_key(encrypted_key)
            except Exception as e:
                logger.error(f"Failed to load master key: {e}")
                self._generate_master_key()
        else:
            self._generate_master_key()
    
    def _generate_master_key(self) -> None:
        """Generate a new master encryption key."""
        self._master_key = secrets.token_bytes(self.config.key_size)
        self._save_master_key()
    
    def _save_master_key(self) -> None:
        """Save the master key securely."""
        if not self._master_key:
            raise ValueError("No master key to save")
        
        key_file = Path("data/.master.key")
        key_file.parent.mkdir(exist_ok=True)
        
        # In production, encrypt with hardware security module
        encrypted_key = self._encrypt_master_key(self._master_key)
        
        with open(key_file, 'wb') as f:
            f.write(encrypted_key)
        
        # Set restrictive permissions
        os.chmod(key_file, 0o600)
    
    def _encrypt_master_key(self, key: bytes) -> bytes:
        """Encrypt master key (placeholder for HSM integration)."""
        # In production, this would use HSM or platform-specific secure storage
        return base64.b64encode(key)
    
    def _decrypt_master_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt master key (placeholder for HSM integration)."""
        # In production, this would use HSM or platform-specific secure storage
        return base64.b64decode(encrypted_key)
    
    def derive_key(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Derive encryption key from password using PBKDF2."""
        if salt is None:
            salt = secrets.token_bytes(self.config.salt_size)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.config.key_size,
            salt=salt,
            iterations=self.config.iterations,
            backend=self._backend
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def encrypt(self, data: Union[str, bytes], key: Optional[bytes] = None) -> Dict[str, str]:
        """Encrypt data using AES-256-GCM."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if key is None:
            key = self._master_key
        
        if not key:
            raise ValueError("No encryption key available")
        
        # Generate random IV
        iv = secrets.token_bytes(self.config.iv_size)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=self._backend
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Get authentication tag
        tag = encryptor.tag
        
        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'tag': base64.b64encode(tag).decode('utf-8'),
            'algorithm': self.config.algorithm.value,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def decrypt(self, encrypted_data: Dict[str, str], key: Optional[bytes] = None) -> bytes:
        """Decrypt data using AES-256-GCM."""
        if key is None:
            key = self._master_key
        
        if not key:
            raise ValueError("No decryption key available")
        
        try:
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            iv = base64.b64decode(encrypted_data['iv'])
            tag = base64.b64decode(encrypted_data['tag'])
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=self._backend
            )
            
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    def encrypt_string(self, text: str, key: Optional[bytes] = None) -> str:
        """Encrypt string and return as base64 JSON."""
        encrypted = self.encrypt(text, key)
        return base64.b64encode(json.dumps(encrypted).encode()).decode()
    
    def decrypt_string(self, encrypted_text: str, key: Optional[bytes] = None) -> str:
        """Decrypt base64 JSON string."""
        try:
            encrypted_data = json.loads(base64.b64decode(encrypted_text).decode())
            decrypted = self.decrypt(encrypted_data, key)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"String decryption failed: {e}")
            raise ValueError("Failed to decrypt string")
    
    def rotate_master_key(self) -> None:
        """Rotate the master encryption key."""
        old_key = self._master_key
        self._generate_master_key()
        
        # In production, re-encrypt all data with new key
        logger.info("Master key rotated successfully")
        
        if self.config.backup_keys and old_key:
            backup_file = Path(f"data/.master_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.key")
            with open(backup_file, 'wb') as f:
                f.write(self._encrypt_master_key(old_key))
            os.chmod(backup_file, 0o600)


class PasswordValidator:
    """Advanced password validation and management."""
    
    def __init__(self, policy: Optional[PasswordPolicy] = None):
        self.policy = policy or PasswordPolicy()
        self._failed_attempts: Dict[str, Dict[str, Any]] = {}
    
    def validate_password(self, password: str) -> Tuple[bool, list]:
        """Validate password against policy."""
        errors = []
        
        # Length check
        if len(password) < self.policy.min_length:
            errors.append(f"Password must be at least {self.policy.min_length} characters")
        
        if len(password) > self.policy.max_length:
            errors.append(f"Password must not exceed {self.policy.max_length} characters")
        
        # Character requirements
        if self.policy.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain uppercase letters")
        
        if self.policy.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain lowercase letters")
        
        if self.policy.require_digits and not re.search(r'\d', password):
            errors.append("Password must contain digits")
        
        if self.policy.require_special:
            special_pattern = f"[{re.escape(self.policy.special_chars)}]"
            if not re.search(special_pattern, password):
                errors.append("Password must contain special characters")
        
        # Common password patterns
        if self._is_common_pattern(password):
            errors.append("Password contains common patterns")
        
        return len(errors) == 0, errors
    
    def _is_common_pattern(self, password: str) -> bool:
        """Check for common password patterns."""
        common_patterns = [
            r'(.)\1{3,}',  # Repeated characters
            r'123456',     # Sequential numbers
            r'abcdef',     # Sequential letters
            r'qwerty',     # Keyboard patterns
            r'password',   # Common words
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                return True
        
        return False
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def check_login_attempt(self, username: str) -> bool:
        """Check if user is locked out due to failed attempts."""
        if username not in self._failed_attempts:
            return True
        
        user_data = self._failed_attempts[username]
        attempts = user_data.get('count', 0)
        last_attempt = user_data.get('last_attempt')
        
        if attempts >= self.policy.max_login_attempts:
            if last_attempt:
                lockout_end = last_attempt + self.policy.lockout_duration
                if datetime.now() < lockout_end:
                    return False
                else:
                    # Reset after lockout period
                    del self._failed_attempts[username]
        
        return True
    
    def record_failed_attempt(self, username: str) -> None:
        """Record a failed login attempt."""
        if username not in self._failed_attempts:
            self._failed_attempts[username] = {'count': 0}
        
        self._failed_attempts[username]['count'] += 1
        self._failed_attempts[username]['last_attempt'] = datetime.now()
    
    def reset_failed_attempts(self, username: str) -> None:
        """Reset failed attempts for successful login."""
        if username in self._failed_attempts:
            del self._failed_attempts[username]
    
    def generate_secure_password(self, length: Optional[int] = None) -> str:
        """Generate a secure password meeting policy requirements."""
        if length is None:
            length = max(16, self.policy.min_length)
        
        # Character sets
        lowercase = 'abcdefghijklmnopqrstuvwxyz'
        uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        digits = '0123456789'
        special = self.policy.special_chars
        
        # Ensure at least one from each required set
        password = []
        if self.policy.require_lowercase:
            password.append(secrets.choice(lowercase))
        if self.policy.require_uppercase:
            password.append(secrets.choice(uppercase))
        if self.policy.require_digits:
            password.append(secrets.choice(digits))
        if self.policy.require_special:
            password.append(secrets.choice(special))
        
        # Fill remaining length
        all_chars = lowercase + uppercase + digits + special
        remaining_length = length - len(password)
        password.extend(secrets.choice(all_chars) for _ in range(remaining_length))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)


# Global instances
_encryption_manager: Optional[EncryptionManager] = None
_password_validator: Optional[PasswordValidator] = None


def get_encryption_manager(config: Optional[EncryptionConfig] = None) -> EncryptionManager:
    """Get global encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager(config)
    return _encryption_manager


def get_password_validator(policy: Optional[PasswordPolicy] = None) -> PasswordValidator:
    """Get global password validator instance."""
    global _password_validator
    if _password_validator is None:
        _password_validator = PasswordValidator(policy)
    return _password_validator


# Convenience functions
def encrypt_data(data: Union[str, bytes], key: Optional[bytes] = None) -> Dict[str, str]:
    """Convenience function to encrypt data."""
    return get_encryption_manager().encrypt(data, key)


def decrypt_data(encrypted_data: Dict[str, str], key: Optional[bytes] = None) -> bytes:
    """Convenience function to decrypt data."""
    return get_encryption_manager().decrypt(encrypted_data, key)


def hash_password(password: str) -> str:
    """Convenience function to hash password."""
    return get_password_validator().hash_password(password)


def verify_password(password: str, hashed: str) -> bool:
    """Convenience function to verify password."""
    return get_password_validator().verify_password(password, hashed)


if __name__ == "__main__":
    # Example usage
    em = get_encryption_manager()
    pv = get_password_validator()
    
    # Test encryption
    test_data = "Sensitive database connection string"
    encrypted = em.encrypt_string(test_data)
    decrypted = em.decrypt_string(encrypted)
    print(f"Original: {test_data}")
    print(f"Decrypted: {decrypted}")
    print(f"Match: {test_data == decrypted}")
    
    # Test password validation
    password = "TestPassword123!"
    is_valid, errors = pv.validate_password(password)
    print(f"Password valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    
    # Test password hashing
    hashed = pv.hash_password(password)
    verified = pv.verify_password(password, hashed)
    print(f"Password verified: {verified}")