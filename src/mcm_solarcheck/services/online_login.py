"""Composed login service for SolarCheck Online."""

from __future__ import annotations

from typing import Protocol


class CredentialVerifier(Protocol):
    def verify_password(self, user_id: str, password: str) -> bool:
        ...


class VerifiedIdentity(Protocol):
    def require_verified_identity(self, user_id: str) -> str:
        ...


class OnlineLoginService:
    """Authenticate credentials and admit only an already verified identity."""

    def __init__(
        self,
        credentials: CredentialVerifier,
        identities: VerifiedIdentity,
    ) -> None:
        self._credentials = credentials
        self._identities = identities

    def login(self, user_id: str, password: str) -> str:
        try:
            credentials_valid = self._credentials.verify_password(user_id, password)
        except ValueError as exc:
            raise PermissionError("invalid online login") from exc
        if not credentials_valid:
            raise PermissionError("invalid online login")
        try:
            return self._identities.require_verified_identity(user_id)
        except (ValueError, PermissionError) as exc:
            raise PermissionError("invalid online login") from exc
