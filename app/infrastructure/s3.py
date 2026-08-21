"""
Backward-compatible S3 helpers — thin wrappers over the MediaStore abstraction.

New code should call `get_media_store()` directly (app/infrastructure/storage.py).
These keep existing call sites working and route through LocalMediaStore in dev.
"""
from app.infrastructure.storage import MediaStore, PAUSE_S3, get_media_store

__all__ = ["upload_to_s3", "s3_file_exists", "download_from_s3", "PAUSE_S3", "get_media_store"]


def upload_to_s3(file_bytes: bytes, filename: str, content_type: str = "image/png") -> str:
    store: MediaStore = get_media_store()
    key = store.upload(filename, file_bytes, content_type)
    return store.url(key)


def s3_file_exists(filename: str) -> bool:
    return get_media_store().exists(filename)


def download_from_s3(filename: str, dest_path: str) -> bool:
    return get_media_store().download(filename, dest_path)
