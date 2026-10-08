"""Provider-neutral payment lifecycle for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from mcm_solarcheck.services.payment_methods import PaymentMethod


class PaymentStatus(str, Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    VOIDED = "voided"
    SETTLED = "settled"


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
    amount: PaymentAmount | None
    status: PaymentStatus = PaymentStatus.CREATED
    provider_reference: str | None = None
    method: PaymentMethod | None = None
    merchant_account_id: str | None = None
    merchant_account_version: int | None = None
    provider_id: str | None = None
    tariff_version: int | None = None
    plant_kwp: int | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("payment_id", self.payment_id),
            ("user_id", self.user_id),
            ("project_id", self.project_id),
            ("job_id", self.job_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.amount is None:
            raise ValueError("payment amount must be positive")
        if self.status is PaymentStatus.SETTLED and self.provider_reference is not None:
            raise ValueError("settled payment cannot have provider reference")
        if (self.merchant_account_id is None) != (self.merchant_account_version is None):
            raise ValueError("merchant account id and version must be configured together")
        if self.merchant_account_version is not None and self.merchant_account_version <= 0:
            raise ValueError("merchant account version must be positive")
        if self.provider_id is not None and (
            not isinstance(self.provider_id, str) or not self.provider_id.strip()
        ):
            raise ValueError("provider_id must be non-empty when configured")
        if (self.tariff_version is None) != (self.plant_kwp is None):
            raise ValueError("tariff version and plant size must be configured together")
        if self.tariff_version is not None and (
            not isinstance(self.tariff_version, int)
            or isinstance(self.tariff_version, bool)
            or self.tariff_version <= 0
        ):
            raise ValueError("tariff_version must be a positive integer")
        if self.plant_kwp is not None and (
            not isinstance(self.plant_kwp, int)
            or isinstance(self.plant_kwp, bool)
            or self.plant_kwp < 0
        ):
            raise ValueError("plant_kwp must be a non-negative integer")

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
            self.method,
            self.merchant_account_id,
            self.merchant_account_version,
            self.provider_id,
            self.tariff_version,
            self.plant_kwp,
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
            self.method,
            self.merchant_account_id,
            self.merchant_account_version,
            self.provider_id,
            self.tariff_version,
            self.plant_kwp,
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
            self.method,
            self.merchant_account_id,
            self.merchant_account_version,
            self.provider_id,
            self.tariff_version,
            self.plant_kwp,
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



class OnlinePaymentPersistence(OnlinePaymentStore, Protocol):
    """Full payment persistence contract required by online composition.

    Processing snapshots bind a payment to the exact payment method, merchant
    account version and provider selected at checkout. Concrete adapters must
    preserve that historical binding across later configuration changes.
    """

    def bind_processing_snapshot(
        self,
        payment_id: str,
        user_id: str,
        project_id: str,
        *,
        method: PaymentMethod,
        merchant_account_id: str,
        merchant_account_version: int,
        provider_id: str,
    ) -> OnlinePayment:
        ...
