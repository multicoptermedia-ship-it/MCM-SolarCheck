# Consent request origin checks

Consent withdrawal now requires a matching browser Origin and Host. Project uploads reject a supplied foreign Origin; requests with no Origin remain allowed for compatibility with existing upload clients. This is partial CSRF protection, not a complete CSRF-token mechanism. Host/proxy deployment configuration must be reviewed before production.

The upload-to-audit sequence is still not atomic. Files stored before a failed audit must not be used for training. No training copy ingestion is enabled. Next: explicit CSRF token/session binding, durable consent workflow and cleanup of consent-derived copies on withdrawal.
