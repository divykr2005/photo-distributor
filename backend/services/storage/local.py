import os
import shutil
from typing import BinaryIO, Optional
from services.storage.base import StorageBackend
from core.config import settings


class LocalStorage(StorageBackend):
    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = root_dir or getattr(settings, "STORAGE_ROOT", None) or os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        os.makedirs(self.root_dir, exist_ok=True)

    def _get_full_path(self, key: str) -> str:
        # Sanitize key and prevent path traversal
        clean_key = os.path.normpath(key).lstrip("/\\")
        if clean_key.startswith("..") or ".." in clean_key.split(os.sep):
            raise ValueError(f"Invalid path traversal key: {key}")
        full_path = os.path.abspath(os.path.join(self.root_dir, clean_key))
        if not full_path.startswith(os.path.abspath(self.root_dir)):
            raise ValueError(f"Path traversal detected outside root: {key}")
        return full_path

    def put(self, key: str, data: bytes | BinaryIO) -> str:
        full_path = self._get_full_path(key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if isinstance(data, bytes):
            with open(full_path, "wb") as f:
                f.write(data)
        else:
            with open(full_path, "wb") as f:
                shutil.copyfileobj(data, f)

        return key

    def get(self, key: str) -> Optional[bytes]:
        full_path = self._get_full_path(key)
        if not os.path.exists(full_path):
            return None
        with open(full_path, "rb") as f:
            return f.read()

    def get_path(self, key: str) -> Optional[str]:
        full_path = self._get_full_path(key)
        if os.path.exists(full_path):
            return full_path
        return None

    def delete(self, key: str) -> bool:
        try:
            full_path = self._get_full_path(key)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
        except Exception:
            pass
        return False

    def exists(self, key: str) -> bool:
        try:
            full_path = self._get_full_path(key)
            return os.path.exists(full_path)
        except Exception:
            return False


def get_storage_backend() -> StorageBackend:
    backend = os.environ.get("STORAGE_BACKEND", "local").lower()
    if backend == "r2":
        from services.storage.r2 import R2Storage
        return R2Storage()
    # default: local filesystem
    return LocalStorage()
