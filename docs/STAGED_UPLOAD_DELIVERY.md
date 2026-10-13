# Staged upload delivery prototype

`StagedUploadDelivery` defines a provider-neutral sequence: write to a random private staging key, read back, check size and SHA-256, publish to final key, and clean up staging. The local adapter publishes without overwriting an existing final file. It is intentionally separate from the existing HTTP upload path and is **not enabled** in production.

This is not an IONOS SFTP implementation. A future SFTP adapter must confirm same-filesystem atomic rename semantics (if any), avoid overwrites, enforce private staging paths, verify remote bytes, recover interrupted transfers and ensure durable publication markers. A successful return from a remote server is not by itself proof of durable storage. The local adapter uses hard links and is suitable only for trusted local filesystems; its no-overwrite behavior is not portable to SFTP.

Known limitations: staging cleanup after process crashes needs a separate, audited sweeper; no persistent manifest or transaction with the job queue exists; remote worker download, retries, bandwidth measurements, credentials, access control and billing limits are not wired. No deployment or external transfer was performed.
