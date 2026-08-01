"""Provider selection — the one place that decides which StorageService
implementation backs the Document Storage System, driven by
settings.DOCUMENT_STORAGE_PROVIDER. Callers (app/ai/document_storage.py)
depend only on the StorageService interface, never on a concrete class."""
from __future__ import annotations

from app.config import settings
from app.storage.base import StorageService


def get_storage_service() -> StorageService:
    provider = settings.DOCUMENT_STORAGE_PROVIDER
    if provider == "local":
        from app.storage.local import LocalStorageService
        return LocalStorageService(settings.DOCUMENT_STORAGE_DIR)
    if provider == "s3":
        from app.storage.providers_stub import S3StorageService
        return S3StorageService()
    if provider == "azure_blob":
        from app.storage.providers_stub import AzureBlobStorageService
        return AzureBlobStorageService()
    raise ValueError(
        f"Unknown DOCUMENT_STORAGE_PROVIDER: {provider!r}. "
        "Supported: 'local' (implemented), 's3'/'azure_blob' (stubs)."
    )
