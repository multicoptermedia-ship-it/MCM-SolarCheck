from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.exclusive_local_publisher import ExclusiveLocalPublisher


def test_exclusive_publish_preserves_bytes_and_private_source(tmp_path):
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"verified payload")
    target_dir = tmp_path / "final"
    target_dir.mkdir()
    target = target_dir / "photo.bin"
    result = ExclusiveLocalPublisher(chunk_size=3).publish(
        source, target, expected_size=len(b"verified payload"),
        expected_sha256=sha256(b"verified payload").hexdigest()
    )
    assert result == target
    assert target.read_bytes() == b"verified payload"
    assert source.read_bytes() == b"verified payload"


def test_existing_final_file_is_never_overwritten(tmp_path):
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"new")
    target = tmp_path / "photo.bin"
    target.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        ExclusiveLocalPublisher().publish(
            source, target, expected_size=3, expected_sha256=sha256(b"new").hexdigest()
        )
    assert target.read_bytes() == b"existing"
    assert source.read_bytes() == b"new"
