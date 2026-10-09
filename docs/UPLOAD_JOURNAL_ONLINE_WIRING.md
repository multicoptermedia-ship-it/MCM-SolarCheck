# Online upload journal wiring

The normal online persistence factory now creates a SQLite upload attempt journal in the private state database. The composed online services expose it, and the online HTTP entrypoint passes it to the upload handler by default. Tests or alternative deployments may supply an explicit journal override.

The HTTP upload path records a pending attempt before filesystem storage and finalizes the journal on success or caught storage failure. An interrupted process may leave a pending attempt; inspect it using UploadAttemptRecovery. A pending record does not prove that a file is missing, and no automatic file deletion or retry is enabled.

**Remaining limitations:** SQLite journal and filesystem writes are not atomic; concurrent writes and post-write journal failures require idempotent reconciliation. Recovery is read-only, not scheduled or executed automatically. Consent updates occur separately and require further consistency work. Validate these paths in end-to-end integration tests before production deployment.
