# Interrupted upload inspection

`UploadAttemptRecovery.inspect(project_directory)` classifies pending journal records without writing to the filesystem or journal. The supplied directory resolver must enforce customer/project ownership and safe paths. Results are `file_absent`, `file_present_unverified`, or `unsafe`.

File presence is not proof of upload integrity: there is no stored content hash or size in the journal. Symlinks and unsafe filenames are not trusted. No automatic deletion, retry, or state finalization is performed. A later production reconciliation process must verify file identity, handle concurrency and crash windows, and avoid changing customer data on uncertain evidence.
