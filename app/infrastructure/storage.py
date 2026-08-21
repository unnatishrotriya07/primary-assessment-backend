"""
MediaStore — object storage abstraction.

The app never calls boto3 directly; everything routes through `get_media_store()`.
This keeps the platform cloud-agnostic: swapping S3 for GCS / Azure Blob is a one-file
change. Two backends:

- `LocalMediaStore`  (dev, when PAUSE_S3=true)  → writes to `static/`, served by FastAPI.
- `S3MediaStore`     (staging/prod)             → private S3 bucket, IAM task-role creds,
                                                 objects read via presigned URLs.

Security: no `public-read` ACLs, ever. Reads use presigned URLs (short-TTL). For durable,
cacheable public delivery use CloudFront OAC instead (see aws_requirements.md).
"""
import os
import shutil
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.common.config import settings

# Dev-only toggle: route storage to local disk so a zero-AWS local setup still works.
PAUSE_S3 = os.getenv("PAUSE_S3", "true").lower() == "true"

# Presigned URL lifetime for object reads (seconds). Short enough to be safe,
# long enough for the MVP's stored picture_url references.
PRESIGN_EXPIRY_SECONDS = int(os.getenv("MEDIA_PRESIGN_EXPIRY_SECONDS", "604800"))


class MediaStore:
    """Upload/read/download objects behind a storage backend."""

    def upload(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def download(self, key: str, dest_path: str) -> bool:
        raise NotImplementedError

    def url(self, key: str) -> Optional[str]:
        """A fetchable URL for the object (absolute, or `/...` served by the app)."""
        raise NotImplementedError


class LocalMediaStore(MediaStore):
    """Writes to the local `static/` tree (dev fallback). URLs are `/static/...`."""

    def __init__(self, root: str = "static"):
        self.root = root

    def _path(self, key: str) -> str:
        clean = key.lstrip("/")
        return os.path.join(self.root, clean)

    def upload(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return key.lstrip("/")

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    def download(self, key: str, dest_path: str) -> bool:
        if not self.exists(key):
            return False
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(self._path(key), dest_path)
        return True

    def url(self, key: str) -> str:
        return f"/{self.root}/{key.lstrip('/')}"


class S3MediaStore(MediaStore):
    """Private S3 bucket. Credentials come from the ECS task role (no long-lived keys)."""

    def __init__(self, bucket: Optional[str] = None, region: Optional[str] = None):
        self.bucket = bucket or settings.AWS_STORAGE_BUCKET_NAME
        self.region = region or settings.AWS_REGION

    def _client(self):
        # If AWS_ACCESS_KEY_ID is absent, boto3 falls back to the instance/task role chain.
        return boto3.client("s3", region_name=self.region)

    def upload(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        clean_key = key.lstrip("/")
        self._client().put_object(
            Bucket=self.bucket,
            Key=clean_key,
            Body=content,
            ContentType=content_type,
        )
        return clean_key

    def exists(self, key: str) -> bool:
        try:
            self._client().head_object(Bucket=self.bucket, Key=key.lstrip("/"))
            return True
        except ClientError:
            return False

    def download(self, key: str, dest_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            self._client().download_file(self.bucket, key.lstrip("/"), dest_path)
            return True
        except ClientError:
            return False

    def url(self, key: str) -> str:
        return self._client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key.lstrip("/")},
            ExpiresIn=PRESIGN_EXPIRY_SECONDS,
        )


_store: Optional[MediaStore] = None


def get_media_store() -> MediaStore:
    """Return the active store, chosen once per process by `PAUSE_S3`."""
    global _store
    if _store is None:
        if PAUSE_S3:
            _store = LocalMediaStore()
        else:
            _store = S3MediaStore()
    return _store
