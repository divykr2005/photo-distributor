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
    Retrieves the master key from the application settings.
    Intended for development and local testing.
    For production, replace with KmsKeyProvider.
    """
    def unwrap_master_key(self) -> bytes:
        from core.config import settings
        key_hex = settings.MASTER_KEY_HEX
        if len(key_hex) != 64:
            raise ValueError("MASTER_KEY_HEX must be exactly 64 hex characters (32 bytes)")
        if key_hex == "0" * 64:
            import os
            if os.getenv("ENVIRONMENT", "dev") == "prod":
                raise ValueError(
                    "MASTER_KEY_HEX is the all-zeros placeholder. "
                    "Set a real key before running in production."
                )
            logger.warning(
                "MASTER_KEY_HEX is the all-zeros placeholder — "
                "this is only acceptable in local development."
            )
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
