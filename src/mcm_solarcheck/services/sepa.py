"""Provider-neutral SEPA mandate lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class SepaMandateStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True)
class SepaMandate:
    mandate_id: str
    user_id: str
    provider_id: str
    provider_reference: str | None = None
    status: SepaMandateStatus = SepaMandateStatus.PENDING

    def __post_init__(self) -> None:
        for name, value in (
            ("mandate_id", self.mandate_id),
            ("user_id", self.user_id),
            ("provider_id", self.provider_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.status is SepaMandateStatus.ACTIVE and not self.provider_reference:
            raise ValueError("active mandate requires provider reference")

    def activate(self, provider_reference: str) -> "SepaMandate":
        if self.status is not SepaMandateStatus.PENDING:
            raise ValueError("mandate activation requires pending state")
        if not isinstance(provider_reference, str) or not provider_reference.strip():
            raise ValueError("provider_reference must be non-empty")
        return SepaMandate(
            self.mandate_id,
            self.user_id,
            self.provider_id,
            provider_reference.strip(),
            SepaMandateStatus.ACTIVE,
        )

    def revoke(self) -> "SepaMandate":
        if self.status is not SepaMandateStatus.ACTIVE:
            raise ValueError("mandate revocation requires active state")
        return SepaMandate(
            self.mandate_id,
            self.user_id,
            self.provider_id,
            self.provider_reference,
            SepaMandateStatus.REVOKED,
        )



class SepaMandatePersistence(Protocol):
    """Provider-neutral persistence for the SEPA mandate lifecycle."""

    def create(self, mandate: SepaMandate) -> None:
        ...

    def get(self, mandate_id: str) -> SepaMandate:
        ...

    def activate(
        self, mandate_id: str, user_id: str, provider_reference: str
    ) -> SepaMandate:
        ...

    def revoke(self, mandate_id: str, user_id: str) -> SepaMandate:
        ...
