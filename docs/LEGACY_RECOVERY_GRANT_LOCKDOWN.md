# Legacy recovery grant writer lockdown

The legacy `SQLiteRecoveryGrants.set_grant` now raises `PermissionError` and cannot silently write an unaudited grant. The legacy `allowed` reader remains available for compatibility. All trusted grant mutations should use `AuthorizedGrantAdministration` composed with `SQLiteAuditedRecoveryGrants`.

Existing databases may contain historical grants without audit entries. Use `LegacyGrantReviewService.inspect()` to identify these for manual review. Do not synthesize historical audit entries or assume that missing history proves misconduct.

**Boundaries:** This blocks the Python legacy setter, not direct SQLite access or other unreviewed code paths. The new administration still depends on trusted authentication and a caller that constructs identities securely. There is no public administration endpoint, IONOS staging connection, or production deployment. Test both Python CI jobs after this change.
