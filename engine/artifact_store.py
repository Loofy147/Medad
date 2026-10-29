"""Local content-addressed artifact byte storage with digest verification.

This is a single-host blob store. It does not authenticate callers or atomically
commit metadata in SQLite; callers should register the returned SHA-256 in the
transactional metadata store. Unreferenced blobs may remain after a metadata write
fails and can be garbage-collected by a separately reviewed maintenance task.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol
import os
import tempfile


class ArtifactIntegrityError(RuntimeError):
    """Raised when retained bytes do not match their content-addressed identity."""


class ArtifactByteStore(Protocol):
    def put_bytes(self, content: bytes, *, expected_sha256: str | None = None) -> dict[str, Any]: ...
    def get_bytes(self, digest: str) -> bytes: ...


def _normalize_digest(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError("sha256 must be a 64-character hexadecimal string")
    normalized = value.lower()
    if any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError("sha256 must be a 64-character hexadecimal string")
    return normalized


class LocalArtifactByteStore:
    """Immutable SHA-256-addressed files, suitable for local/single-host workflows."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, digest: str) -> Path:
        normalized = _normalize_digest(digest)
        return self.root / "sha256" / normalized[:2] / normalized

    def put_bytes(self, content: bytes, *, expected_sha256: str | None = None) -> dict[str, Any]:
        if not isinstance(content, bytes):
            raise TypeError("artifact content must be bytes")
        digest = sha256(content).hexdigest()
        if expected_sha256 is not None and _normalize_digest(expected_sha256) != digest:
            raise ArtifactIntegrityError("artifact bytes do not match the expected SHA-256 digest")

        destination = self._path_for(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            retained = self.get_bytes(digest)
            if retained != content:
                # A SHA-256 collision is extraordinarily unlikely; this also fails closed
                # if a path has been replaced with bytes that somehow hash to this key.
                raise ArtifactIntegrityError("existing content-addressed blob differs from supplied bytes")
            return self._metadata(digest, len(content))

        descriptor, temporary_name = tempfile.mkstemp(prefix=".medad-artifact-", dir=destination.parent)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            try:
                # Atomic visibility: readers see either no blob or the complete blob.
                os.link(temporary_name, destination)
            except FileExistsError:
                # Another writer won the same digest race; verify the winner.
                if self.get_bytes(digest) != content:
                    raise ArtifactIntegrityError("concurrent blob write produced inconsistent bytes")
            directory_fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass

        # Verify the persisted bytes, not just the in-memory input.
        retained = self.get_bytes(digest)
        if retained != content:
            raise ArtifactIntegrityError("persisted artifact bytes failed post-write verification")
        return self._metadata(digest, len(retained))

    def get_bytes(self, digest: str) -> bytes:
        normalized = _normalize_digest(digest)
        path = self._path_for(normalized)
        try:
            content = path.read_bytes()
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"artifact blob not found for sha256:{normalized}") from exc
        actual = sha256(content).hexdigest()
        if actual != normalized:
            raise ArtifactIntegrityError(
                f"retained artifact digest mismatch: expected {normalized}, got {actual}"
            )
        return content

    def verify(self, digest: str) -> dict[str, Any]:
        normalized = _normalize_digest(digest)
        content = self.get_bytes(normalized)
        return {
            "sha256": normalized,
            "byte_length": len(content),
            "verified": True,
            "verification": "RETAINED_BYTES_REHASHED",
            "storage_backend": "LOCAL_CONTENT_ADDRESSED_FILESYSTEM",
        }

    @staticmethod
    def _metadata(digest: str, byte_length: int) -> dict[str, Any]:
        return {
            "sha256": digest,
            "byte_length": byte_length,
            "verified": True,
            "verification": "WRITE_READBACK_SHA256_MATCH",
            "storage_backend": "LOCAL_CONTENT_ADDRESSED_FILESYSTEM",
        }
