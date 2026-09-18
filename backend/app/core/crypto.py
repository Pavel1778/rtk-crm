"""Cryptography utilities for PII encryption and masking."""

from cryptography.fernet import Fernet
from sqlalchemy import TypeDecorator, String
from typing import Optional
import base64
import os

from backend.app.core.config import settings


def get_encryption_key() -> bytes:
    """Get or generate encryption key."""
    key_str = settings.ENCRYPTION_KEY
    if not key_str:
        # Generate new key for development
        key = Fernet.generate_key()
        return key
    
    # Ensure key is valid base64 and 32 bytes
    try:
        key_bytes = base64.urlsafe_b64decode(key_str.encode())
        if len(key_bytes) != 32:
            raise ValueError("Key must be 32 bytes")
        return base64.urlsafe_b64encode(key_bytes)
    except Exception:
        # If invalid, generate new one
        return Fernet.generate_key()


class EncryptedString(TypeDecorator):
    """TypeDecorator for encrypting string values in database."""
    
    impl = String
    cache_ok = True
    
    def __init__(self, length: int = 255, **kwargs):
        super().__init__(length=length, **kwargs)
        self.cipher = Fernet(get_encryption_key())
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt value before storing in database."""
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        encrypted = self.cipher.encrypt(value.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt value after retrieving from database."""
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        decrypted = self.cipher.decrypt(value.encode('utf-8'))
        return decrypted.decode('utf-8')


def mask_pii(value: str) -> str:
    """Mask personally identifiable information for logging.
    
    Examples:
        "Иванов Иван" -> "И*** И***"
        "ivanov@example.com" -> "i***@example.com"
        "+7 (999) 123-45-67" -> "+7 (***) ***-**"
    """
    if not value:
        return value
    
    # Email masking
    if "@" in value and "." in value.split("@")[-1]:
        parts = value.split("@")
        name = parts[0]
        domain = parts[1]
        masked_name = name[0] + "***" if len(name) > 1 else name + "***"
        return f"{masked_name}@{domain}"
    
    # Phone masking (Russian format)
    if value.startswith("+7") or value.startswith("8"):
        return "+7 (***) ***-**"
    
    # Name masking (split by space)
    parts = value.split()
    masked_parts = []
    for part in parts:
        if len(part) > 1:
            masked_parts.append(part[0] + "***")
        else:
            masked_parts.append(part + "***")
    
    return " ".join(masked_parts)
