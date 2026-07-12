from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from kb_core.config import settings

logger = logging.getLogger("kb_core.storage")


class MinioClient:
    """MinIO 对象存储客户端."""

    def __init__(self):
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket

    async def ensure_bucket(self) -> None:
        if not await asyncio.to_thread(self.client.bucket_exists, self.bucket):
            await asyncio.to_thread(self.client.make_bucket, self.bucket)

    async def upload_file(
        self, object_path: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        def _upload():
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_path,
                data=BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return object_path

        return await asyncio.to_thread(_upload)

    async def download_file(self, object_path: str) -> bytes:
        def _download():
            response = self.client.get_object(self.bucket, object_path)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_download)

    async def delete_file(self, object_path: str) -> None:
        try:
            await asyncio.to_thread(self.client.remove_object, self.bucket, object_path)
        except S3Error:
            pass  # File not found is treated as success (already deleted)

    async def delete_by_prefix(self, prefix: str) -> int:
        """Delete all objects with the given prefix. Returns count of deleted objects."""
        try:
            objects = list(await asyncio.to_thread(
                self.client.list_objects, self.bucket, prefix=prefix, recursive=True,
            ))
        except S3Error:
            return 0
        if not objects:
            return 0
        names = [DeleteObject(o.object_name) for o in objects]

        def _remove():
            return list(self.client.remove_objects(self.bucket, names))

        errors = await asyncio.to_thread(_remove)
        deleted = len(names)
        for err in errors:
            logger.warning("MinIO delete error: %s", err)
            deleted -= 1
        if deleted > 0:
            logger.info("Deleted %d files with prefix: %s", deleted, prefix)
        return deleted

    async def file_exists(self, object_path: str) -> bool:
        try:
            await asyncio.to_thread(self.client.stat_object, self.bucket, object_path)
            return True
        except S3Error:
            return False
