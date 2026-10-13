import os
from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.canonical_descriptor_publisher import CanonicalDescriptorPublisher


@pytest.mark.skipif(os.name != "posix", reason="POSIX required")
def test_adapter_publishes_under_canonical_destination(tmp_path):
    root = tmp_path / "storage"
    project = root / "customer" / "project"
    project.mkdir(parents=True)
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    destination = project / "transfer.bin"
    publisher = CanonicalDescriptorPublisher(root)
    publisher.publish(source, destination, expected_size=3,
                      expected_sha256=sha256(b"abc").hexdigest())
    assert destination.read_bytes() == b"abc"


@pytest.mark.skipif(os.name != "posix", reason="POSIX required")
def test_adapter_rejects_destination_outside_root(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    with pytest.raises(ValueError):
        CanonicalDescriptorPublisher(root).publish(
            source, tmp_path / "elsewhere" / "customer" / "project" / "transfer.bin",
            expected_size=3, expected_sha256=sha256(b"abc").hexdigest()
        )


@pytest.mark.skipif(os.name != "posix", reason="POSIX required")
def test_adapter_rejects_intermediate_symlink(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    outside = tmp_path / "outside"
    (outside / "project").mkdir(parents=True)
    (root / "customer").symlink_to(outside, target_is_directory=True)
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    with pytest.raises(OSError):
        CanonicalDescriptorPublisher(root).publish(
            source, root / "customer" / "project" / "transfer.bin",
            expected_size=3, expected_sha256=sha256(b"abc").hexdigest()
        )
    assert not (outside / "project" / "transfer.bin").exists()
