import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from ..config import settings

logger = logging.getLogger(__name__)

class TokenManager:
    """Secure token encryption and decryption for OAuth tokens"""
    
    def __init__(self):
        """Initialize with encryption key from settings"""
        try:
            # Decode base64 encryption key
            key_bytes = base64.b64decode(settings.encryption_key.encode())
            self.fernet = Fernet(base64.urlsafe_b64encode(key_bytes[:32]))
            logger.info("TokenManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TokenManager: {str(e)}")
            raise ValueError("Invalid encryption key configuration")
    
    async def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token for secure storage
        
        Args:
            token: Plain text token to encrypt
            
        Returns:
            Base64 encoded encrypted token
        """
        try:
            if not token:
                raise ValueError("Token cannot be empty")
            
            encrypted_bytes = self.fernet.encrypt(token.encode('utf-8'))
            encrypted_token = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            logger.debug("Token encrypted successfully")
            return encrypted_token
            
        except Exception as e:
            logger.error(f"Token encryption failed: {str(e)}")
            raise ValueError("Failed to encrypt token")
    
    async def decrypt_token(self, encrypted_token: str) -> Optional[str]:
        """
        Decrypt a token from storage
        
        Args:
            encrypted_token: Base64 encoded encrypted token
            
        Returns:
            Decrypted plain text token or None if decryption fails
        """
        try:
            if not encrypted_token:
                return None
            
            encrypted_bytes = base64.b64decode(encrypted_token.encode('utf-8'))
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            token = decrypted_bytes.decode('utf-8')
            
            logger.debug("Token decrypted successfully")
            return token
            
        except InvalidToken:
            logger.error("Token decryption failed: Invalid token or key")
            return None
        except Exception as e:
            logger.error(f"Token decryption failed: {str(e)}")
            return None
    
    async def verify_token_integrity(self, encrypted_token: str) -> bool:
        """
        Verify if an encrypted token can be decrypted (integrity check)
        
        Args:
            encrypted_token: Base64 encoded encrypted token
            
        Returns:
            True if token is valid and can be decrypted
        """
        try:
            decrypted = await self.decrypt_token(encrypted_token)
            return decrypted is not None
        except Exception:
            return False