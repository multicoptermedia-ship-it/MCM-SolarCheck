"""HTTP composition boundary for the SolarCheck Online product."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from mcm_solarcheck.infrastructure.verification_http_server import build_verification_server
from mcm_solarcheck.online.product import OnlineProduct
from mcm_solarcheck.services.online_entitlement import OnlineProduct as EntitlementProduct
from mcm_solarcheck.services.online_credentials import PasswordCredentialService
from mcm_solarcheck.services.online_registration_ui import RegistrationServiceController
from mcm_solarcheck.services.online_session import InMemorySessionStore, OnlineSessionService
from mcm_solarcheck.services.online_verification_http import EmailVerificationEndpoint


def build_online_verification_server(
    product: OnlineProduct,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    now: Callable[[], datetime] | None = None,
    secure_cookies: bool = False,
    production: bool = False,
):
    """Compose the verification HTTP adapter from the authoritative online services."""
    if not isinstance(product, OnlineProduct):
        raise TypeError("product must be OnlineProduct")
    if production and not secure_cookies:
        raise ValueError("production HTTP requires secure session cookies")
    endpoint = EmailVerificationEndpoint(
        product.services.registration,
        product=EntitlementProduct.TRIAL,
        now=now,
    )
    registration_controller = RegistrationServiceController(
        product.services.registration,
        product=EntitlementProduct.TRIAL,
        now=now,
        credentials=(
            PasswordCredentialService(product.services.credentials)
            if hasattr(product.services, "credentials")
            else None
        ),
    )
    return build_verification_server(
        endpoint,
        host=host,
        port=port,
        registration_controller=registration_controller,
        login_service=getattr(product.services, "login", None),
        session_service=OnlineSessionService(
            getattr(product.services, "sessions", InMemorySessionStore()),
            now=now,
        ),
        secure_cookies=secure_cookies,
        customer_entry=product.require_customer_entry,
        project_service=getattr(product.services, "projects", None),
        project_pricing_service=getattr(product.services, "project_pricing", None),
        project_creation_service=getattr(product.services, "project_creation", None),
    )
