from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class StorageBackend(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes | BinaryIO) -> str:
        """Store bytes or file-like data at key. Returns the canonical key."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        """Retrieve bytes at key. Returns None if key does not exist."""
        pass

    @abstractmethod
    def get_path(self, key: str) -> Optional[str]:
        """Return full filesystem path if available, or None."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete storage key. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if storage key exists."""
        pass
