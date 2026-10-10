from hashlib import sha256

import pytest

from mcm_solarcheck.services.immutable_part_writer import ImmutablePartWriter


class FakeRemote:
    def __init__(self):
        self.files = {}
        self.writes = 0

    def write_exclusive(self, key, data):
        if key in self.files:
            raise FileExistsError(key)
        self.files[key] = data
        self.writes += 1

    def read(self, key):
        return self.files[key]


def test_repeated_upload_is_idempotent():
    remote = FakeRemote()
    writer = ImmutablePartWriter(remote)
    first = writer.write("a" * 32, 0, b"abc")
    second = writer.write("a" * 32, 0, b"abc")
    assert first == second
    assert remote.writes == 1


def test_corrupted_existing_part_is_rejected():
    remote = FakeRemote()
    writer = ImmutablePartWriter(remote)
    key, digest = writer.write("a" * 32, 0, b"abc")
    remote.files[key] = b"abd"
    with pytest.raises(ValueError):
        writer.write("a" * 32, 0, b"abc")


def test_missing_exclusive_write_capability_fails_closed():
    with pytest.raises(RuntimeError):
        ImmutablePartWriter(object()).write("a" * 32, 0, b"abc")


def test_part_size_limit_is_enforced_before_remote_write():
    remote = FakeRemote()
    with pytest.raises(ValueError):
        ImmutablePartWriter(remote, max_part_bytes=2).write("a" * 32, 0, b"abc")
    assert remote.writes == 0
