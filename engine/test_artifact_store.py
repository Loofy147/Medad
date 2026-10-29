import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from artifact_store import ArtifactIntegrityError, LocalArtifactByteStore


class LocalArtifactByteStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.store = LocalArtifactByteStore(self.root)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_write_and_read_verify_retained_bytes(self):
        content = b"medad artifact bytes\x00\xff"
        expected = sha256(content).hexdigest()
        stored = self.store.put_bytes(content, expected_sha256=expected)
        self.assertEqual(stored["sha256"], expected)
        self.assertEqual(stored["byte_length"], len(content))
        self.assertTrue(stored["verified"])
        self.assertEqual(self.store.get_bytes(expected), content)
        self.assertEqual(self.store.verify(expected)["verification"], "RETAINED_BYTES_REHASHED")

    def test_expected_digest_mismatch_writes_nothing(self):
        content = b"wrong bytes"
        with self.assertRaises(ArtifactIntegrityError):
            self.store.put_bytes(content, expected_sha256="0" * 64)
        blobs = list((self.root / "sha256").rglob("*")) if (self.root / "sha256").exists() else []
        self.assertEqual(blobs, [])

    def test_tampered_retained_blob_is_detected(self):
        content = b"original"
        metadata = self.store.put_bytes(content)
        digest = metadata["sha256"]
        path = self.root / "sha256" / digest[:2] / digest
        path.write_bytes(b"tampered")
        with self.assertRaisesRegex(ArtifactIntegrityError, "digest mismatch"):
            self.store.get_bytes(digest)
        with self.assertRaisesRegex(ArtifactIntegrityError, "digest mismatch"):
            self.store.verify(digest)

    def test_invalid_digest_and_non_bytes_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "64-character"):
            self.store.get_bytes("../outside")
        with self.assertRaises(TypeError):
            self.store.put_bytes("not bytes")

    def test_duplicate_write_is_idempotent_and_content_addressed(self):
        content = b"same bytes"
        first = self.store.put_bytes(content)
        second = self.store.put_bytes(content, expected_sha256=first["sha256"])
        self.assertEqual(first, second)
        self.assertEqual(len(list((self.root / "sha256").rglob("*.*"))), 1)


if __name__ == "__main__":
    unittest.main()
