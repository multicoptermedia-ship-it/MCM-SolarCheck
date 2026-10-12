# Local YOLO staging contract (milestone 20)

A reviewed dataset and model-weight license are mandatory. Only a user-invoked local operation may stage a dataset. Copy the six expected split directories into a newly created destination; never follow source symlinks, never use hard links and never overwrite an existing destination. Bound file count, per-file size and total bytes. Check the approved source immediately before copying and verify the staged fingerprint afterwards. Reject a changed source and remove partial staging.

The destination is private and best-effort read-only, **not** a cryptographically immutable or concurrency-safe snapshot. It must not be placed inside the source. Do not run YOLO, download models, upload imagery, or initiate cloud jobs. Production workers still require sandboxing and an immutable mount with a fresh verification at consumption time.
