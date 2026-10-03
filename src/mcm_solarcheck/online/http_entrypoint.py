"""HTTP composition boundary for the SolarCheck Online product."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from mcm_solarcheck.infrastructure.verification_http_server import build_verification_server
from mcm_solarcheck.online.product import OnlineProduct
from mcm_solarcheck.services.online_entitlement import OnlineProduct as EntitlementProduct
from mcm_solarcheck.services.online_credentials import PasswordCredentialService
from mcm_solarcheck.services.online_registration_ui import RegistrationServiceController
from mcm_solarcheck.services.online_verification_http import EmailVerificationEndpoint


def build_online_verification_server(
    product: OnlineProduct,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    now: Callable[[], datetime] | None = None,
):
    """Compose the verification HTTP adapter from the authoritative online services."""
    if not isinstance(product, OnlineProduct):
        raise TypeError("product must be OnlineProduct")
    endpoint = EmailVerificationEndpoint(
        product.services.registration,
        product=EntitlementProduct.TRIAL,
        now=now,
        credentials=PasswordCredentialService(product.services.credentials),
    )
    registration_controller = RegistrationServiceController(
        product.services.registration,
        product=EntitlementProduct.TRIAL,
        now=now,
    )
    return build_verification_server(
        endpoint,
        host=host,
        port=port,
        registration_controller=registration_controller,
    )
