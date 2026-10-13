# SSH/SFTP error classification: current scope

This batch introduces a conservative translator for known timeout, network, permission and optional Paramiko authentication exceptions. The handshake and authentication methods now translate selected errors without including their original messages in the new exception text. Python exception chaining retains original exceptions for trusted diagnostics, so never expose raw tracebacks to customers.

A new `StrictReadOnlySFTPSession` distinguishes ENOENT (directory absent) from permission and network errors. It is **not yet wired into the existing Paramiko driver**, which still uses its earlier permissive directory-inspection wrapper. Integration and fake-client regression tests remain next steps.

The translator deliberately leaves unknown exceptions unchanged. It does not classify every Paramiko exception or guarantee that errors never contain secrets at logging boundaries. No real IONOS network activity, credentials, writes, billing or deployment took place.
