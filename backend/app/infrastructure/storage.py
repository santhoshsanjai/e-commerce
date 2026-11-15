from functools import lru_cache
from typing import Protocol

import boto3

from app.core.config import get_settings


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def public_url(self, key: str) -> str: ...


class S3Storage:
    """Product media bucket, served publicly through the CDN. Object keys live in PostgreSQL."""

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.media_bucket
        self._base_url = settings.media_public_base_url.rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def public_url(self, key: str) -> str:
        return f"{self._base_url}/{key}"


@lru_cache
def get_storage() -> ObjectStorage:
    return S3Storage()


class FileStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...


class S3FileStore:
    """Private bucket for courier exports and imports. Files are only served through the API,
    behind a permission check, so customer addresses never sit at a public URL. On AWS the bucket
    uses default encryption at rest and blocks all public access."""

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.private_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def get(self, key: str) -> bytes:
        body: bytes = self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()
        return body


@lru_cache
def get_file_store() -> FileStore:
    return S3FileStore()
