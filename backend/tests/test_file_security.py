import asyncio
import os

import pytest

from utils.file_security import (
    FileSecurityError,
    read_upload_with_limit,
    sanitize_filename,
    stream_upload_to_tempfile,
    validate_extension,
    validate_file_path,
    validate_file_size,
    validate_general_upload,
    validate_general_upload_path,
    validate_mime_type,
)


class _ChunkedUpload:
    def __init__(self, chunks: list[bytes]):
        self.chunks = iter(chunks)
        self.requested_sizes: list[int] = []

    async def read(self, size: int) -> bytes:
        self.requested_sizes.append(size)
        return next(self.chunks)


class TestFileSecurity:
    """Tests for file security utilities."""

    def test_validate_extension_success(self):
        """Test valid extension."""
        assert validate_extension("test.jpg") == ".jpg"
        assert validate_extension("TEST.PDF") == ".pdf"  # Case insensitive

    def test_validate_extension_failure(self):
        """Test invalid extension."""
        with pytest.raises(FileSecurityError) as exc:
            validate_extension("test.exe")
        assert "not allowed" in str(exc.value)

        with pytest.raises(FileSecurityError) as exc:
            validate_extension("test")
        assert "must have an extension" in str(exc.value)

        with pytest.raises(FileSecurityError) as exc:
            validate_extension(None)
        assert "Filename is required" in str(exc.value)

    def test_validate_mime_type_success(self):
        """Test valid mime type."""
        # Should not raise
        validate_mime_type("image/jpeg", ".jpg")
        validate_mime_type("application/pdf", ".pdf")

    def test_validate_mime_type_failure(self):
        """Test invalid mime type."""
        # Extension mismatch
        with pytest.raises(FileSecurityError) as exc:
            validate_mime_type("image/jpeg", ".pdf")
        assert "does not match" in str(exc.value)

        # Invalid extension for mime
        with pytest.raises(FileSecurityError) as exc:
            validate_mime_type("application/x-dosexec", ".exe")
        assert "not allowed" in str(exc.value)

        # Missing content type
        with pytest.raises(FileSecurityError) as exc:
            validate_mime_type(None, ".jpg")
        assert "Content type is required" in str(exc.value)

    def test_validate_file_size(self):
        """Test file size validation."""
        content = b"12345"
        assert validate_file_size(content, max_size=10) == 5

        # Too large
        with pytest.raises(FileSecurityError) as exc:
            validate_file_size(content, max_size=2)
        assert "File too large" in str(exc.value)

        # Empty
        with pytest.raises(FileSecurityError) as exc:
            validate_file_size(b"")
        assert "Empty file" in str(exc.value)

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("test.txt") == "test.txt"
        assert sanitize_filename("../test.txt") == "test.txt"  # Traversal removed
        assert (
            sanitize_filename("test/file.txt") == "testfile.txt"
        )  # Separators removed by dangerous pattern check
        assert sanitize_filename("test\\file.txt") == "testfile.txt"
        assert sanitize_filename("weird<name>.txt") == "weirdname.txt"
        assert sanitize_filename("") == ""

        # Long filename truncation
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name)
        assert len(sanitized) == 255
        assert sanitized.endswith(".txt")

    def test_validate_file_path(self):
        """Test path traversal prevention."""
        import os

        base = os.path.abspath("/tmp/uploads")

        # Valid
        valid_path = os.path.join(base, "file.txt")
        assert validate_file_path(base, valid_path) == valid_path

        # Traversal attempt
        invalid_path = os.path.abspath("/tmp/secret.txt")
        if not invalid_path.startswith(base):  # Only if actually outside
            with pytest.raises(FileSecurityError) as exc:
                validate_file_path(base, invalid_path)
            assert "Invalid file path" in str(exc.value)

    def test_validate_general_upload(self):
        """Test high level upload validation."""
        # Success
        ext, size = validate_general_upload("test.txt", "text/plain", b"abc")
        assert ext == ".txt"
        assert size == 3

        # Failure
        with pytest.raises(FileSecurityError):
            validate_general_upload("test.exe", "application/octet-stream", b"abc")

    @pytest.mark.asyncio
    async def test_read_upload_with_limit_rejects_oversized_stream(self):
        upload = _ChunkedUpload([b"abc", b"def"])

        with pytest.raises(FileSecurityError, match="File too large"):
            await read_upload_with_limit(upload, max_size=5)

        assert upload.requested_sizes == [6, 6]

    @pytest.mark.asyncio
    async def test_read_upload_with_limit_returns_bounded_content(self):
        upload = _ChunkedUpload(
            [
                b"abc",
                b"",
            ]
        )

        assert await read_upload_with_limit(upload, max_size=5) == b"abc"
        assert upload.requested_sizes == [6, 6]

    @pytest.mark.asyncio
    async def test_stream_upload_to_tempfile_bounds_and_preserves_content(self):
        upload = _ChunkedUpload([b"abc", b"def", b""])

        path, size = await stream_upload_to_tempfile(upload, max_size=10)
        try:
            assert size == 6
            with open(path, "rb") as staged:
                assert staged.read() == b"abcdef"
        finally:
            os.remove(path)

    @pytest.mark.asyncio
    async def test_stream_upload_to_tempfile_cleans_up_when_cancelled(self, tmp_path, monkeypatch):
        staged_path = tmp_path / "cancelled-upload.tmp"
        file_descriptor = os.open(staged_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        monkeypatch.setattr(
            "utils.file_security.tempfile.mkstemp",
            lambda **_kwargs: (file_descriptor, str(staged_path)),
        )

        class _CancelledUpload:
            async def read(self, _size: int) -> bytes:
                raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await stream_upload_to_tempfile(_CancelledUpload(), max_size=10)

        assert not staged_path.exists()

    def test_path_validation_reads_metadata_without_loading_content(self, tmp_path):
        file_path = tmp_path / "notes.txt"
        file_path.write_bytes(b"abc")

        extension, size = validate_general_upload_path(
            "notes.txt",
            "text/plain",
            str(file_path),
            file_path.stat().st_size,
        )

        assert extension == ".txt"
        assert size == 3
