import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
from typing import Dict, Any

from app.core.config import settings

class AESEncryption:
    def __init__(self):
        # Generate key from password
        password = settings.SECRET_KEY.encode()
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.cipher_suite = Fernet(key)
        self.salt = salt

    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """Encrypt sensitive data using AES-256"""
        json_data = json.dumps(data)
        encrypted_data = self.cipher_suite.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()

    def decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt sensitive data"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode())

    def encrypt_sensitive_fields(self, kyc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive KYC fields"""
        sensitive_fields = ['full_name', 'dob', 'address', 'email', 'phone']
        encrypted_fields = {}
        
        for field in sensitive_fields:
            if field in kyc_data and kyc_data[field]:
                encrypted_fields[field] = kyc_data[field]
        
        return {
            'encrypted_data': self.encrypt_data(encrypted_fields),
            'encrypted_fields': list(encrypted_fields.keys())
        }

# Global encryption instance
encryption = AESEncryption()
