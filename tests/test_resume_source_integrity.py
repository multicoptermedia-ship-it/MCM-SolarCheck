from hashlib import sha256
from io import BytesIO

from mcm_solarcheck.services.resume_source_integrity import verify_resume_source


def test_source_integrity_and_position_restoration():
    source = BytesIO(b"abcdef")
    source.seek(3)
    assert verify_resume_source(source, expected_size=6, expected_sha256=sha256(b"abcdef").hexdigest(), chunk_size=2)
    assert source.tell() == 3


def test_modified_source_is_rejected():
    source = BytesIO(b"abcxef")
    assert not verify_resume_source(source, expected_size=6, expected_sha256=sha256(b"abcdef").hexdigest(), chunk_size=2)


def test_truncated_and_extended_sources_are_rejected():
    digest = sha256(b"abcdef").hexdigest()
    assert not verify_resume_source(BytesIO(b"abc"), expected_size=6, expected_sha256=digest)
    assert not verify_resume_source(BytesIO(b"abcdefg"), expected_size=6, expected_sha256=digest)
