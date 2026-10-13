from io import BytesIO

import pytest

from mcm_solarcheck.infrastructure.sftp_resume_reader import ReadOnlySFTPResumeBackend


class FakeTransport:
    def __init__(self):
        self.paths = []

    def read_chunks(self, path, chunk_size):
        self.paths.append((path, chunk_size))
        yield b"ab"
        yield b"cd"


def test_read_only_sftp_resume_adapter():
    transport = FakeTransport()
    reader = ReadOnlySFTPResumeBackend(transport, root="/private")
    assert b"".join(reader.read_staging_chunks(".staging/abc", 2)) == b"abcd"
    assert transport.paths == [("/private/.staging/abc", 2)]


@pytest.mark.parametrize("chunk_size", [0, -1, True])
def test_invalid_chunk_size_rejected(chunk_size):
    reader = ReadOnlySFTPResumeBackend(FakeTransport(), root="/private")
    with pytest.raises(ValueError):
        reader.read_staging_chunks(".staging/abc", chunk_size)


def test_traversal_rejected():
    reader = ReadOnlySFTPResumeBackend(FakeTransport(), root="/private")
    with pytest.raises(ValueError):
        list(reader.read_staging_chunks(".staging/../outside", 2))
