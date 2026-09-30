"""Durable intent for crash-safe SEPA provider submission."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SepaSubmissionStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"


@dataclass(frozen=True)
class SepaSubmission:
    payment_id: str
    mandate_id: str
    user_id: str
    project_id: str
    provider_id: str
    idempotency_key: str
    status: SepaSubmissionStatus = SepaSubmissionStatus.PENDING
    provider_reference: str | None = None
    lease_token: str | None = None
    lease_until: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("payment_id", self.payment_id),
            ("mandate_id", self.mandate_id),
            ("user_id", self.user_id),
            ("project_id", self.project_id),
            ("provider_id", self.provider_id),
            ("idempotency_key", self.idempotency_key),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.status is SepaSubmissionStatus.SUBMITTED and not self.provider_reference:
            raise ValueError("submitted SEPA intent requires provider reference")
        if self.status is SepaSubmissionStatus.PENDING and self.provider_reference is not None:
            raise ValueError("pending SEPA intent cannot have provider reference")
        if self.status is SepaSubmissionStatus.SUBMITTED and (
            self.lease_token is not None or self.lease_until is not None
        ):
            raise ValueError("submitted SEPA intent cannot retain a lease")
        if self.status is SepaSubmissionStatus.PENDING and (
            (self.lease_token is None) != (self.lease_until is None)
        ):
            raise ValueError(
                "pending SEPA intent lease token and expiry must be set together"
            )

    def submitted(self, provider_reference: str) -> "SepaSubmission":
        if self.status is not SepaSubmissionStatus.PENDING:
            raise ValueError("SEPA intent is already submitted")
        if not isinstance(provider_reference, str) or not provider_reference.strip():
            raise ValueError("provider_reference must be non-empty")
        return SepaSubmission(
            self.payment_id,
            self.mandate_id,
            self.user_id,
            self.project_id,
            self.provider_id,
            self.idempotency_key,
            SepaSubmissionStatus.SUBMITTED,
            provider_reference.strip(),
            None,
            None,
        )
