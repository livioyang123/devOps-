"""
Encryption utilities for API keys and sensitive credentials
Implements AES-256 encryption for secure storage
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data using AES-256
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            encryption_key: Base64 encoded encryption key (32 bytes)
                          If not provided, uses key from settings
        """
        key = encryption_key or settings.encryption_key
        
        # Derive a proper Fernet key from the encryption key
        self.fernet = self._create_fernet(key)
    
    def _create_fernet(self, key: str) -> Fernet:
        """
        Create a Fernet instance from the encryption key
        
        Args:
            key: Encryption key string
            
        Returns:
            Fernet instance for encryption/decryption
        """
        # Use PBKDF2 to derive a proper 32-byte key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'devops-k8s-platform-salt',  # In production, use a random salt per installation
            iterations=100000,
            backend=default_backend()
        )
        
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(derived_key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string using AES-256
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64 encoded encrypted string
            
        Raises:
            Exception: If encryption fails
        """
        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise Exception(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt an encrypted string
        
        Args:
            encrypted_text: Base64 encoded encrypted string
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            Exception: If decryption fails
        """
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_text.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise Exception(f"Failed to decrypt data: {str(e)}")
    
    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt an API key for storage
        
        Args:
            api_key: API key to encrypt
            
        Returns:
            Encrypted API key
        """
        return self.encrypt(api_key)
    
    def decrypt_api_key(self, encrypted_api_key: str) -> str:
        """
        Decrypt an API key from storage
        
        Args:
            encrypted_api_key: Encrypted API key
            
        Returns:
            Decrypted API key
        """
        return self.decrypt(encrypted_api_key)
    
    def encrypt_credentials(self, credentials: str) -> str:
        """
        Encrypt Kubernetes credentials or other sensitive data
        
        Args:
            credentials: Credentials to encrypt (JSON string, kubeconfig, etc.)
            
        Returns:
            Encrypted credentials
        """
        return self.encrypt(credentials)
    
    def decrypt_credentials(self, encrypted_credentials: str) -> str:
        """
        Decrypt Kubernetes credentials or other sensitive data
        
        Args:
            encrypted_credentials: Encrypted credentials
            
        Returns:
            Decrypted credentials
        """
        return self.decrypt(encrypted_credentials)
    
    def mask_api_key(self, api_key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for display purposes
        
        Args:
            api_key: API key to mask
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked API key (e.g., "****abcd")
        """
        if len(api_key) <= visible_chars:
            return "*" * len(api_key)
        
        masked_length = len(api_key) - visible_chars
        return "*" * masked_length + api_key[-visible_chars:]


# Global encryption service instance
encryption_service = EncryptionService()


def encrypt_api_key(api_key: str) -> str:
    """
    Convenience function to encrypt an API key
    
    Args:
        api_key: API key to encrypt
        
    Returns:
        Encrypted API key
    """
    return encryption_service.encrypt_api_key(api_key)


def decrypt_api_key(encrypted_api_key: str) -> str:
    """
    Convenience function to decrypt an API key
    
    Args:
        encrypted_api_key: Encrypted API key
        
    Returns:
        Decrypted API key
    """
    return encryption_service.decrypt_api_key(encrypted_api_key)


def encrypt_credentials(credentials: str) -> str:
    """
    Convenience function to encrypt credentials
    
    Args:
        credentials: Credentials to encrypt
        
    Returns:
        Encrypted credentials
    """
    return encryption_service.encrypt_credentials(credentials)


def decrypt_credentials(encrypted_credentials: str) -> str:
    """
    Convenience function to decrypt credentials
    
    Args:
        encrypted_credentials: Encrypted credentials
        
    Returns:
        Decrypted credentials
    """
    return encryption_service.decrypt_credentials(encrypted_credentials)


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    Convenience function to mask an API key
    
    Args:
        api_key: API key to mask
        visible_chars: Number of characters to show at the end
        
    Returns:
        Masked API key
    """
    return encryption_service.mask_api_key(api_key, visible_chars)
