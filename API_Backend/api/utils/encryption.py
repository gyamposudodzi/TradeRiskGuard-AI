"""
Encryption utility for API keys and sensitive data
"""
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
from typing import Optional

class EncryptionService:
    """Service for encrypting/decrypting sensitive data"""
    
    def __init__(self):
        # Use environment variable for encryption key
        # In production, use a secure key management system
        self.secret_key = os.getenv("ENCRYPTION_SECRET", "default-secret-key-change-in-production")
        self.salt = b"tradeguard_deriv_salt"  # Should be random and stored securely in production
        
        # Derive key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """Decrypt an encrypted string"""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    def encrypt_dict(self, data: dict) -> str:
        """Encrypt a dictionary"""
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Optional[dict]:
        """Decrypt to dictionary"""
        decrypted = self.decrypt(encrypted_data)
        if decrypted:
            return json.loads(decrypted)
        return None

# Singleton instance
encryption_service = EncryptionService()