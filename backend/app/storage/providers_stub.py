"""Future storage providers — interface-complete, not yet wired to a real
SDK. Selecting either via DOCUMENT_STORAGE_PROVIDER fails fast and loud at
get_storage_service() time rather than silently falling back to local disk
or pretending to work.

Implementing either for real needs an SDK dependency this project does not
currently install (boto3 for S3, azure-storage-blob for Azure Blob) plus
real credentials/bucket-or-container config — deliberately out of scope
for this sprint. See the sprint report's "Remaining limitations" section.
"""
from __future__ import annotations

from app.storage.base import StorageService


class S3StorageService(StorageService):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "S3 document storage is not yet implemented. Install boto3, "
            "configure DOCUMENT_STORAGE_S3_BUCKET/DOCUMENT_STORAGE_S3_REGION "
            "and AWS credentials, then implement save/get/delete/exists here."
        )

    def save(self, key: str, data: bytes) -> None:  # pragma: no cover
        raise NotImplementedError

    def get(self, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def delete(self, key: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def exists(self, key: str) -> bool:  # pragma: no cover
        raise NotImplementedError


class AzureBlobStorageService(StorageService):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "Azure Blob document storage is not yet implemented. Install "
            "azure-storage-blob, configure DOCUMENT_STORAGE_AZURE_CONTAINER/"
            "DOCUMENT_STORAGE_AZURE_CONNECTION_STRING, then implement "
            "save/get/delete/exists here."
        )

    def save(self, key: str, data: bytes) -> None:  # pragma: no cover
        raise NotImplementedError

    def get(self, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def delete(self, key: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def exists(self, key: str) -> bool:  # pragma: no cover
        raise NotImplementedError
