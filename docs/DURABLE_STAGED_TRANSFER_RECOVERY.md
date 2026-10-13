# Durable staged-transfer recovery foundation

`SQLiteTransferManifest` records owner/project, final and random staging keys, expected byte count and SHA-256, state and UTC timestamps. Conditional transitions restrict state changes and owner access. `StagedTransferVerifier.inspect` reads staged content in bounded chunks and reports verified bytes, missing bytes, size/hash mismatch or unsafe chunk, without mutating manifests or publishing files.

**This is not automatic upload resumption.** No offset is trusted or appended. No HTTP or IONOS SFTP transport integration is enabled. A successful read-only verification is a snapshot, not a guarantee against concurrent remote mutation before publication.

Before actual resume/publish, implement authenticated resume tokens, durable offset checkpoints, readback verification of existing prefix, exclusive lease/fencing and immutable staging after verification. Publication must be exclusive and atomically coupled to a durable manifest or equivalent commit marker. A crash between remote publication and database transition requires explicit reconciliation. A later block must handle stale manifests, retention, deletion and audit.

Never use these manifest rows as permission to train AI on customer images; training consent is independent. No remote deployment or customer file changes were performed.
