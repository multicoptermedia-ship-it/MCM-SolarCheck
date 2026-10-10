from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.exclusive_local_publisher import ExclusiveLocalPublisher


@pytest.mark.parametrize("expected_size,expected_hash", [
    (4, sha256(b"abc").hexdigest()),
    (3, sha256(b"bad").hexdigest()),
])
def test_bad_integrity_never_creates_final_name(tmp_path, expected_size, expected_hash):
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    target = tmp_path / "final.bin"
    with pytest.raises(ValueError):
        ExclusiveLocalPublisher().publish(
            source, target, expected_size=expected_size, expected_sha256=expected_hash
        )
    assert not target.exists()


def test_symlink_source_is_rejected(tmp_path):
    actual = tmp_path / "actual"
    actual.write_bytes(b"abc")
    source = tmp_path / ".assembly-link"
    source.symlink_to(actual)
    target = tmp_path / "final.bin"
    with pytest.raises((OSError, ValueError)):
        ExclusiveLocalPublisher().publish(
            source, target, expected_size=3, expected_sha256=sha256(b"abc").hexdigest()
        )
    assert not target.exists()


def test_unexpected_source_name_is_rejected(tmp_path):
    source = tmp_path / "random"
    source.write_bytes(b"abc")
    with pytest.raises(ValueError):
        ExclusiveLocalPublisher().publish(
            source, tmp_path / "final.bin", expected_size=3,
            expected_sha256=sha256(b"abc").hexdigest()
        )
