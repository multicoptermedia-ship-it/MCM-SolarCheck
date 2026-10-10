"""Server-selected destination for reserved local publication prototypes."""
from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.infrastructure.canonical_descriptor_publisher import CanonicalDescriptorPublisher
from mcm_solarcheck.services.canonical_local_destination import canonical_local_destination
from mcm_solarcheck.services.reserved_local_publication import ReservedLocalPublication


class CanonicalReservedLocalPublication:
    def __init__(self, root, transfers, journal, destinations, *, publisher=None, reconciler=None):
        self.root = Path(root)
        if not self.root.is_absolute() or not self.root.is_dir() or self.root.is_symlink():
            raise ValueError("root must be an existing absolute non-symlink directory")
        if publisher is None:
            publisher = CanonicalDescriptorPublisher(self.root)
        self.reserved = ReservedLocalPublication(
            transfers, journal, destinations, publisher=publisher, reconciler=reconciler
        )

    def destination_for(self, transfer_id, customer_id, project_id):
        return canonical_local_destination(self.root, customer_id, project_id, transfer_id)

    def publish(self, transfer_id, customer_id, project_id, *, source):
        final = self.destination_for(transfer_id, customer_id, project_id)
        # Do not create directories based on untrusted input. Provision private
        # customer/project directories in a separate authorized workflow.
        if not final.parent.is_dir() or final.parent.is_symlink():
            raise ValueError("customer/project destination directory not provisioned safely")
        return self.reserved.publish(
            transfer_id, customer_id, project_id, source=source, destination=final
        )
