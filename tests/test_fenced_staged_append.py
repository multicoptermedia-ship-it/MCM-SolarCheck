import pytest

from mcm_solarcheck.services.fenced_staged_append import (
    FencedAppendUnsupported,
    FencedStagedAppender,
)


class FakeFencedRemote:
    def __init__(self):
        self.generation = 2
        self.data = b"abc"

    def append_chunks_if_generation_and_size(self, key, generation, offset, chunks):
        if generation != self.generation or offset != len(self.data):
            raise RuntimeError("stale worker or offset")
        self.data += b"".join(chunks)


def test_stale_generation_cannot_append():
    remote = FakeFencedRemote()
    appender = FencedStagedAppender(remote)
    with pytest.raises(RuntimeError):
        appender.append(".staging/a", generation=1, expected_offset=3, chunks=[b"def"])
    assert remote.data == b"abc"
    appender.append(".staging/a", generation=2, expected_offset=3, chunks=[b"def"])
    assert remote.data == b"abcdef"


def test_stale_offset_cannot_append():
    remote = FakeFencedRemote()
    with pytest.raises(RuntimeError):
        FencedStagedAppender(remote).append(
            ".staging/a", generation=2, expected_offset=2, chunks=[b"def"]
        )
    assert remote.data == b"abc"


def test_backend_without_fencing_fails_closed():
    with pytest.raises(FencedAppendUnsupported):
        FencedStagedAppender(object()).append(
            ".staging/a", generation=1, expected_offset=0, chunks=[b"data"]
        )
