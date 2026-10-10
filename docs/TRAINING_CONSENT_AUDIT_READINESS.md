# Training consent audit readiness

The SQLite audit table remains append-only and now has an index for owner/project/latest-event lookups. TrainingConsentService.audit_events checks project ownership before returning the event history. It is an internal service method, not a customer-facing HTTP endpoint.

This block does not make upload and consent recording atomic. No training data copy lifecycle, revocation deletion, or 14-day project retention has been implemented. A successful upload response must not be treated as proof that consent events and stored files committed together. Future training ingestion must re-check active consent immediately before copying any image.
