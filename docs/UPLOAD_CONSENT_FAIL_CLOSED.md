# Upload consent failure handling

Before the HTTP handler stores replacement project data, it now records a withdrawal event when consent persistence is configured. This invalidates any earlier project training permission. After successful storage, an explicit opt-in is recorded as a fresh grant; an unchecked upload remains withdrawn. If the initial audit write fails, storage does not begin. If upload storage or the final grant fails, the earlier grant stays invalidated.

Trade-off: a failed upload may revoke an earlier valid grant, and the operation is not atomic across SQLite and filesystem storage. The extra withdrawal is an auditable event, not a full transactional upload workflow. No training ingestion or training-copy cleanup is enabled. Do not treat this as complete durability or retention compliance; staging, retry reconciliation, and end-to-end failure injection are still needed.
