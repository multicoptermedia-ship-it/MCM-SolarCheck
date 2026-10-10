# Conservative local publication recovery prototype

`CanonicalPublicationRecoveryAssessment` performs an owner-scoped, read-only assessment. It checks the canonical journal destination, expected size and digest against the transfer, the durable destination reservation, and the injected fresh file verifier. A valid file with a `needs_review` journal entry is eligible for **explicit** reconciliation. Missing, corrupted, unavailable or mismatched files are never automatically approved.

`ExplicitPublicationReconciliation.reconcile_verified` can advance `needs_review` to `published` using the existing journal compare-and-swap only after a successful assessment. It never republishes or deletes a file and is not attached to customer-facing HTTP endpoints or a background scheduler.

**Security limits:** Assessment and journal transition are not a single transaction with the filesystem; a file can change between verification and state update. Authorization to invoke explicit reconciliation must be enforced by a future trusted operator workflow. The assessment accepts an injected reconciler; production must use the fresh descriptor-based canonical reconciler, not a stub. The `published` state is not a substitute for future byte verification. No automatic retries, IONOS SFTP actions or deployment are included.
