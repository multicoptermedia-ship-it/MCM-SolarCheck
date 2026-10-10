import os
from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.descriptor_relative_publisher import DescriptorRelativePublisher
from mcm_solarcheck.infrastructure.private_directory_descriptors import open_private_directory_chain


@pytest.mark.skipif(os.name != "posix", reason="POSIX only")
def test_descriptor_relative_publish_is_exclusive(tmp_path):
    root = tmp_path / "storage"
    project = root / "customer" / "project"
    project.mkdir(parents=True)
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    fd = open_private_directory_chain(root, "customer", "project")
    try:
        publisher = DescriptorRelativePublisher(chunk_size=2)
        assert publisher.publish(source, fd, "transfer.bin", expected_size=3,
                                 expected_sha256=sha256(b"abc").hexdigest()) == "transfer.bin"
        assert (project / "transfer.bin").read_bytes() == b"abc"
        with pytest.raises(FileExistsError):
            publisher.publish(source, fd, "transfer.bin", expected_size=3,
                              expected_sha256=sha256(b"abc").hexdigest())
    finally:
        os.close(fd)


@pytest.mark.skipif(os.name != "posix", reason="POSIX only")
def test_descriptor_publish_rejects_bad_hash(tmp_path):
    root = tmp_path / "storage"
    project = root / "customer" / "project"
    project.mkdir(parents=True)
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    fd = open_private_directory_chain(root, "customer", "project")
    try:
        with pytest.raises(ValueError):
            DescriptorRelativePublisher().publish(source, fd, "transfer.bin",
                                                  expected_size=3, expected_sha256=sha256(b"bad").hexdigest())
        assert not (project / "transfer.bin").exists()
    finally:
        os.close(fd)
