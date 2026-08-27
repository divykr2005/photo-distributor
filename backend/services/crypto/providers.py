import os
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class KeyProvider(ABC):
    @abstractmethod
    def unwrap_master_key(self) -> bytes:
        """Returns the 32-byte master key."""
        pass

class LocalKeyProvider(KeyProvider):
    """
    Retrieves the master key from environment variables.
    Intended for development and local testing.
    """
    def unwrap_master_key(self) -> bytes:
        # In a real scenario, this would be a 32-byte hex string or base64
        # We'll use a dummy key if not found, just for this example
        key_hex = os.getenv("MASTER_KEY_HEX", "0" * 64)
        if len(key_hex) != 64:
            raise ValueError("MASTER_KEY_HEX must be exactly 64 hex characters (32 bytes)")
        return bytes.fromhex(key_hex)

class KmsKeyProvider(KeyProvider):
    """
    Retrieves the master key from a KMS service.
    (Stub implementation as requested)
    """
    def __init__(self, key_id: str):
        self.key_id = key_id

    def unwrap_master_key(self) -> bytes:
        # In a real scenario, you'd call boto3.client('kms') to decrypt a stored encrypted master key
        logger.warning(f"KMS provider called for key {self.key_id}, returning dummy key")
        return bytes.fromhex("1" * 64)

def get_key_provider() -> KeyProvider:
    provider_type = os.getenv("KMS_PROVIDER", "local")
    if provider_type == "kms":
        key_id = os.getenv("KMS_KEY_ID", "default-key-id")
        return KmsKeyProvider(key_id)
    else:
        return LocalKeyProvider()
