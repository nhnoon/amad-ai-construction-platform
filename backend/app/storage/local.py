"""Local-disk StorageService — the only provider actually wired up today.

Keys are always server-generated (app/ai/document_storage.py::
_generate_storage_key), never derived from user-supplied filenames, but
this implementation still defends against path traversal at the storage
layer itself — never trust the caller — by refusing to resolve any key
that would land outside the configured storage root.
"""
from __future__ import annotations

import os

from app.storage.base import StorageService


class PathTraversalError(ValueError):
    """Raised when a storage key would resolve outside the storage root."""


class LocalStorageService(StorageService):
    def __init__(self, root_dir: str):
        self._root = os.path.abspath(root_dir)
        os.makedirs(self._root, exist_ok=True)

    def _resolve(self, key: str) -> str:
        if not key or key.startswith(("/", "\\")):
            raise PathTraversalError(f"Invalid storage key: {key!r}")
        normalized = key.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise PathTraversalError(f"Invalid storage key: {key!r}")
        candidate = os.path.abspath(os.path.join(self._root, key))
        if os.path.commonpath([self._root, candidate]) != self._root:
            raise PathTraversalError(f"Storage key escapes storage root: {key!r}")
        return candidate

    def save(self, key: str, data: bytes) -> None:
        path = self._resolve(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Write to a temp file and atomically rename into place, so a
        # crash or concurrent read mid-write never observes a partial file.
        tmp_path = f"{path}.tmp-{os.getpid()}-{id(data)}"
        with open(tmp_path, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)

    def get(self, key: str) -> bytes:
        path = self._resolve(key)
        with open(path, "rb") as f:
            return f.read()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def exists(self, key: str) -> bool:
        path = self._resolve(key)
        return os.path.isfile(path)
