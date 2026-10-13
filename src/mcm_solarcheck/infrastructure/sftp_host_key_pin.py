"""Strict offline-only SFTP host-key verification helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac


def ssh_sha256_fingerprint(public_key_blob: bytes) -> str:
    if not isinstance(public_key_blob, bytes) or not public_key_blob:
        raise ValueError("SSH public key blob required")
    digest = hashlib.sha256(public_key_blob).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def verify_ssh_host_key(public_key_blob: bytes, expected_fingerprint: str) -> None:
    if not isinstance(expected_fingerprint, str):
        raise ValueError("SSH host-key pin required")
    actual = ssh_sha256_fingerprint(public_key_blob)
    if not hmac.compare_digest(actual, expected_fingerprint):
        raise ValueError("SFTP host-key fingerprint mismatch")
