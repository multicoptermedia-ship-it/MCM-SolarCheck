"""Provider-neutral online registration and email verification domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class RegistrationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"


@dataclass(frozen=True)
class OnlineRegistration:
    """Required identity for test or full online use."""

    user_id: str
    display_name: str
    email: str
    status: RegistrationStatus = RegistrationStatus.PENDING
    verified_at: datetime | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("user_id", self.user_id),
            ("display_name", self.display_name),
            ("email", self.email),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        normalized = self.email.strip().lower()
        if normalized.count("@") != 1:
            raise ValueError("email must contain one @")
        local, domain = normalized.split("@")
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("email must be plausible")
        object.__setattr__(self, "email", normalized)
        if self.status is RegistrationStatus.VERIFIED:
            if self.verified_at is None:
                raise ValueError("verified registration requires verified_at")
            _require_utc(self.verified_at)
        elif self.verified_at is not None:
            raise ValueError("pending registration cannot have verified_at")

    def verify(self, now: datetime) -> "OnlineRegistration":
        """Mark this identity verified after successful email proof."""
        _require_utc(now)
        if self.status is RegistrationStatus.VERIFIED:
            return self
        return OnlineRegistration(
            self.user_id,
            self.display_name,
            self.email,
            RegistrationStatus.VERIFIED,
            now,
        )


@dataclass(frozen=True)
class EmailVerification:
    """Opaque verification secret with an explicit server-supplied lifetime."""

    token: str
    created_at: datetime
    duration: timedelta

    def __post_init__(self) -> None:
        if not isinstance(self.token, str) or not self.token.strip():
            raise ValueError("verification token must be non-empty")
        _require_utc(self.created_at)
        if self.duration <= timedelta(0):
            raise ValueError("verification duration must be positive")

    @property
    def expires_at(self) -> datetime:
        return self.created_at + self.duration

    def valid_at(self, now: datetime) -> bool:
        _require_utc(now)
        return now < self.expires_at


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("verification time must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise ValueError("verification time must be UTC")
