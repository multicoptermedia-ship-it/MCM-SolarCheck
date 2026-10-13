"""Journal-aware read-only reconciliation using descriptor-pinned verification."""
from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.services.canonical_local_destination import canonical_local_destination
from mcm_solarcheck.services.descriptor_publication_verifier import DescriptorPublicationVerifier


class CanonicalPublicationReconciler:
    def __init__(self, journal, root, *, verifier=None):
        self.journal = journal
        self.root = Path(root)
        self.verifier = verifier or DescriptorPublicationVerifier(root)

    def inspect(self, transfer_id, customer_id, project_id):
        record = self.journal.get(transfer_id, customer_id, project_id)
        if record is None:
            return "not_found"
        expected_destination = canonical_local_destination(
            self.root, customer_id, project_id, transfer_id
        )
        if record["destination"] != str(expected_destination):
            return "invalid_destination"
        # Unlike the legacy reconciler, a recorded 'published' state does
        # not bypass a fresh read of the actual file bytes.
        return self.verifier.inspect(
            transfer_id, customer_id, project_id,
            expected_size=record["expected_size"],
            expected_sha256=record["expected_sha256"]
        )
