# PV YOLO training approval snapshot

`prepare_training_approval_snapshot` combines an actual read-only image/label audit, explicit site/flight group manifest, reviewed dataset provenance and license, class mapping, model-weight review reference and bounded training parameters. SHA-256 fingerprints cover file paths and bytes; the group manifest and complete approval evidence receive separate deterministic hashes. A second fingerprint immediately after audit detects changes observed during preparation.

`require_matching_training_approval` repeats the audit and compares the full approval snapshot. It rejects changed annotation content, image bytes, group assignment, dataset license evidence, mapping or training parameters. No image bytes are included in the returned metadata, no external service is contacted, and no training is started.

This is not an atomic immutable filesystem snapshot: concurrent writers can still race after verification. A future training worker must use an isolated immutable content-addressed copy and revalidate immediately before consuming it. The group identifiers are user-provided assertions, not independently verified site provenance. Human legal and model-weight review remain essential.
