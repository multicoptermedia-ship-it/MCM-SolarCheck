from hashlib import sha256

import pytest

from mcm_solarcheck.services.immutable_upload_parts import (
    immutable_part_key,
    validate_part_bytes,
)


def test_part_key_is_deterministic_and_scoped():
    transfer_id = "a" * 32
    digest = sha256(b"abc").hexdigest()
    assert immutable_part_key(transfer_id, 7, digest) == (
        f".staging/parts/{transfer_id}/000007-{digest}"
    )
    validate_part_bytes(b"abc", digest)


@pytest.mark.parametrize("transfer,number,digest", [
    ("../x", 0, "a" * 64),
    ("a" * 32, -1, "a" * 64),
    ("a" * 32, True, "a" * 64),
    ("a" * 32, 0, "not-a-hash"),
])
def test_invalid_part_identity_rejected(transfer, number, digest):
    with pytest.raises(ValueError):
        immutable_part_key(transfer, number, digest)


def test_corrupt_and_oversized_parts_rejected():
    digest = sha256(b"abc").hexdigest()
    with pytest.raises(ValueError):
        validate_part_bytes(b"abd", digest)
    with pytest.raises(ValueError):
        validate_part_bytes(b"abc", digest, max_part_bytes=2)
