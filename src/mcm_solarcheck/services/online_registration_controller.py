"""Presentation boundary for online registration and email verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RegistrationRequest:
    user_id: str
    display_name: str
    email: str
    street: str
    postal_code: str
    city: str


class OnlineRegistrationController(Protocol):
    """UI-facing port; server/service code owns verification and entitlement policy."""

    def register(self, request: RegistrationRequest) -> str:
        ...

    def verify_email_token(self, token: str) -> str:
        ...
