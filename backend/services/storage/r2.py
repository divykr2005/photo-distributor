import io
import logging
import os
from typing import BinaryIO, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from services.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class R2Storage(StorageBackend):
    """
    Cloudflare R2 storage backend.
    R2 is S3-compatible — only the endpoint_url differs from AWS S3.

    Required env vars:
        R2_ACCOUNT_ID       — Cloudflare account ID (found in R2 dashboard)
        R2_ACCESS_KEY_ID    — R2 API token Access Key ID
        R2_SECRET_ACCESS_KEY — R2 API token Secret Access Key
        R2_BUCKET_NAME      — Name of your R2 bucket
        R2_PUBLIC_URL       — (optional) Public bucket URL for direct serving
                              e.g. https://pub-xxxx.r2.dev  or a custom domain
    """

    def __init__(self):
        account_id = os.environ["R2_ACCOUNT_ID"]
        access_key = os.environ["R2_ACCESS_KEY_ID"]
        secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
        self.bucket = os.environ["R2_BUCKET_NAME"]
        self.public_url = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")

        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",  # R2 uses "auto" as the region
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    # ------------------------------------------------------------------
    # StorageBackend interface
    # ------------------------------------------------------------------

    def put(self, key: str, data: bytes | BinaryIO) -> str:
        """Upload bytes or a file-like object to R2. Returns the canonical key."""
        try:
            if isinstance(data, (bytes, bytearray)):
                self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
            else:
                self.client.upload_fileobj(data, self.bucket, key)
            logger.debug("R2 put: %s", key)
            return key
        except ClientError as e:
            logger.error("R2 put failed for key %s: %s", key, e)
            raise

    def get(self, key: str) -> Optional[bytes]:
        """Download and return the raw bytes for a key, or None if not found."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            logger.error("R2 get failed for key %s: %s", key, e)
            raise

    def get_path(self, key: str) -> Optional[str]:
        """
        R2 has no local filesystem path.
        Returns a public URL if R2_PUBLIC_URL is configured and the object exists,
        otherwise returns None (caller must fall back to streaming via get()).
        """
        if self.public_url and self.exists(key):
            return f"{self.public_url}/{key}"
        return None

    def delete(self, key: str) -> bool:
        """Delete an object. Returns True on success, False if key didn't exist."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.debug("R2 delete: %s", key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return False
            logger.error("R2 delete failed for key %s: %s", key, e)
            raise

    def exists(self, key: str) -> bool:
        """Check if an object exists in R2."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            logger.error("R2 exists check failed for key %s: %s", key, e)
            raise

    # ------------------------------------------------------------------
    # Extras — useful for serving
    # ------------------------------------------------------------------

    def get_stream(self, key: str) -> Optional[BinaryIO]:
        """
        Returns a streaming body (file-like) instead of loading the whole file
        into memory. Use this in media-serving endpoints for large originals.
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"]
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            raise

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate a time-limited pre-signed GET URL.
        Useful if you want to redirect the browser directly to R2
        instead of proxying bytes through your backend.
        expires_in: seconds until expiry (default 1 hour)
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
