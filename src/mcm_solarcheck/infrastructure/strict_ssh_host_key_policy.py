"""Transport-independent SSH handshake policy.

The SSH implementation must invoke the host-key callback during key exchange,
before sending any user authentication or opening SFTP.
"""
from __future__ import annotations

from mcm_solarcheck.infrastructure.sftp_host_key_pin import verify_ssh_host_key


class StrictHostKeyPolicy:
    def __init__(self, expected_fingerprint: str):
        self.expected_fingerprint = expected_fingerprint
        self.verified = False

    def check(self, public_key_blob: bytes) -> None:
        verify_ssh_host_key(public_key_blob, self.expected_fingerprint)
        self.verified = True

    def require_verified(self) -> None:
        if not self.verified:
            raise PermissionError("SSH host key must be verified before authentication")
