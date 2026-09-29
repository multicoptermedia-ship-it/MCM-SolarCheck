"""Provider-neutral payment method model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PaymentMethod(str, Enum):
    SEPA_DIRECT_DEBIT = "sepa_direct_debit"
    PAYPAL = "paypal"
    CARD = "card"


@dataclass(frozen=True)
class PaymentMethodCapabilities:
    method: PaymentMethod
    requires_mandate: bool
    supports_authorize_capture: bool
    supports_void: bool


def payment_method_capabilities(method: PaymentMethod) -> PaymentMethodCapabilities:
    if method is PaymentMethod.SEPA_DIRECT_DEBIT:
        return PaymentMethodCapabilities(method, True, False, False)
    return PaymentMethodCapabilities(method, False, True, True)
