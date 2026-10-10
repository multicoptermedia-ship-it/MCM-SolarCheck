# Coordinated local publication (prototype)

`LocalPublicationCoordinator` reads canonical transfer metadata scoped to customer and project, prepares an idempotent SQLite journal entry, conditionally claims the `prepared` state, publishes via exclusive local hard link, performs independent streaming readback of the final path, and only then transitions the journal to `published`. Existing final files are never overwritten. Failures move an active attempt to `needs_review` where possible; retries do not automatically repeat the publish.

`PublicationRecoveryAdvisor` classifies incomplete attempts read-only. Its `recorded_complete_unchecked` response does not prove that final bytes still exist or remain valid.

**Not production ready:** the SQLite journal and filesystem are separate failure domains. A crash after link creation and before durable journal commit is ambiguous; manual reconciliation remains necessary. The publisher requires trusted directories and source files, and hard-linked source/final bytes can still change if a writer retains access. No distributed fencing, immutable final storage, automatic safe retry, quota enforcement, canonical server-chosen final-path mapping, HTTP wiring, or IONOS SFTP semantics have been implemented. Do not treat journal state alone as customer-facing file availability. No real deployment or billable operation was performed.
