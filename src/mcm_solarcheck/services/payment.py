"""Provider-neutral payment lifecycle for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PaymentStatus(str, Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    VOIDED = "voided"


@dataclass(frozen=True)
class PaymentAmount:
    """Currency amount represented in integer minor units, never float."""

    minor_units: int
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.minor_units, int) or isinstance(self.minor_units, bool):
            raise ValueError("minor_units must be an integer")
        if self.minor_units <= 0:
            raise ValueError("minor_units must be positive")
        if (
            not isinstance(self.currency, str)
            or len(self.currency.strip()) != 3
            or not self.currency.strip().isalpha()
        ):
            raise ValueError("currency must be a three-letter code")
        object.__setattr__(self, "currency", self.currency.strip().upper())


@dataclass(frozen=True)
class OnlinePayment:
    """Server-owned payment state independent of a concrete provider."""

    payment_id: str
    user_id: str
    project_id: str
    job_id: str
    amount: PaymentAmount
    status: PaymentStatus = PaymentStatus.CREATED
    provider_reference: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("payment_id", self.payment_id),
            ("user_id", self.user_id),
            ("project_id", self.project_id),
            ("job_id", self.job_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    def authorize(self, provider_reference: str) -> "OnlinePayment":
        if self.status is not PaymentStatus.CREATED:
            raise ValueError("payment authorization requires created state")
        if not isinstance(provider_reference, str) or not provider_reference.strip():
            raise ValueError("provider_reference must be non-empty")
        return OnlinePayment(
            self.payment_id,
            self.user_id,
            self.project_id,
            self.job_id,
            self.amount,
            PaymentStatus.AUTHORIZED,
            provider_reference.strip(),
        )

    def capture(self) -> "OnlinePayment":
        if self.status is not PaymentStatus.AUTHORIZED:
            raise ValueError("payment capture requires authorized state")
        return OnlinePayment(
            self.payment_id,
            self.user_id,
            self.project_id,
            self.job_id,
            self.amount,
            PaymentStatus.CAPTURED,
            self.provider_reference,
        )

    def void(self) -> "OnlinePayment":
        if self.status is not PaymentStatus.AUTHORIZED:
            raise ValueError("payment void requires authorized state")
        return OnlinePayment(
            self.payment_id,
            self.user_id,
            self.project_id,
            self.job_id,
            self.amount,
            PaymentStatus.VOIDED,
            self.provider_reference,
        )


class OnlinePaymentStore(Protocol):
    """Persistent server-owned payment state transitions."""

    def create(self, payment: OnlinePayment) -> None:
        ...

    def get(self, payment_id: str) -> OnlinePayment:
        ...

    def authorize(
        self, payment_id: str, user_id: str, project_id: str, provider_reference: str
    ) -> OnlinePayment:
        ...

    def capture(
        self, payment_id: str, user_id: str, project_id: str
    ) -> OnlinePayment:
        ...

    def void(
        self, payment_id: str, user_id: str, project_id: str
    ) -> OnlinePayment:
        ...
