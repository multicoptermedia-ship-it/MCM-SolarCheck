"""Publisher adapter for canonical paths and descriptor-relative POSIX writes."""
from __future__ import annotations

import os
from pathlib import Path

from mcm_solarcheck.infrastructure.descriptor_relative_publisher import DescriptorRelativePublisher
from mcm_solarcheck.infrastructure.private_directory_descriptors import open_private_directory_chain
from mcm_solarcheck.services.canonical_local_destination import canonical_local_destination


class CanonicalDescriptorPublisher:
    """Drop-in publisher for LocalPublicationCoordinator with a trusted storage root."""

    def __init__(self, root, *, publisher=None):
        self.root = Path(root)
        if not self.root.is_absolute() or self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("trusted existing absolute non-symlink root required")
        self.publisher = publisher or DescriptorRelativePublisher()

    def publish(self, source, destination, *, expected_size, expected_sha256):
        final = Path(destination)
        if final.suffix != ".bin":
            raise ValueError("unexpected destination suffix")
        try:
            relative = final.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("destination outside trusted root") from exc
        if len(relative.parts) != 3:
            raise ValueError("destination must be customer/project/transfer.bin")
        customer, project, filename = relative.parts
        transfer = filename[:-4]
        if final != canonical_local_destination(self.root, customer, project, transfer):
            raise ValueError("noncanonical destination")
        fd = open_private_directory_chain(self.root, customer, project)
        try:
            return self.publisher.publish(
                source, fd, filename, expected_size=expected_size,
                expected_sha256=expected_sha256
            )
        finally:
            os.close(fd)
