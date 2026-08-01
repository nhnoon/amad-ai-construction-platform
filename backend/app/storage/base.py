"""Storage abstraction — the one interface every document storage backend
implements (local disk today; S3/Azure Blob as future providers, see
app/storage/providers_stub.py). Nothing outside app/storage/ and
app/ai/document_storage.py should touch a filesystem path or cloud SDK
directly for document bytes — that boundary is what lets the backing
provider change later without touching any caller.

Keys are opaque strings assigned by the caller (app/ai/document_storage.py
always generates them server-side — see _generate_storage_key — never from
user input) and are provider-specific in shape (a relative path for local
disk, an object key for S3, a blob name for Azure) but always addressable
with just save/get/delete/exists.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class StorageService(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> None:
        """Persist `data` under `key`. Overwrites silently if `key` already
        exists — callers that care about not overwriting (e.g. versioning)
        must generate a fresh, never-reused key instead."""
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Return the bytes stored under `key`. Raises FileNotFoundError if
        nothing is stored under that key."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove whatever is stored under `key`. Safe to call when `key`
        does not exist (no-op, does not raise)."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether `key` currently has stored content."""
        raise NotImplementedError
