"""Credential boundary for SolarCheck Online authentication."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Protocol

PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16


@dataclass(frozen=True)
class PasswordCredential:
    user_id: str
    salt_hex: str
    digest_hex: str
    iterations: int = PBKDF2_ITERATIONS


class CredentialStore(Protocol):
    def save(self, credential: PasswordCredential) -> None:
        ...

    def get(self, user_id: str) -> PasswordCredential:
        ...


class PasswordCredentialService:
    """Create and verify password proofs without persisting plaintext secrets."""

    def __init__(self, store: CredentialStore) -> None:
        self._store = store

    def set_password(self, user_id: str, password: str) -> None:
        user_id = _require_user_id(user_id)
        password_bytes = _require_password(password)
        salt = secrets.token_bytes(SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password_bytes, salt, PBKDF2_ITERATIONS
        )
        self._store.save(
            PasswordCredential(
                user_id=user_id,
                salt_hex=salt.hex(),
                digest_hex=digest.hex(),
            )
        )

    def verify_password(self, user_id: str, password: str) -> bool:
        user_id = _require_user_id(user_id)
        password_bytes = _require_password(password)
        try:
            credential = self._store.get(user_id)
        except KeyError:
            return False
        salt = bytes.fromhex(credential.salt_hex)
        expected = bytes.fromhex(credential.digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password_bytes, salt, credential.iterations
        )
        return hmac.compare_digest(actual, expected)


def _require_user_id(user_id: str) -> str:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user identity must be non-empty")
    return user_id.strip()


def _require_password(password: str) -> bytes:
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("password must contain at least 12 characters")
    return password.encode("utf-8")
