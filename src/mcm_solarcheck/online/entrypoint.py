"""Customer-facing shell composition for the SolarCheck Online product."""

from __future__ import annotations

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.online.product import OnlineProduct
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.online_entitlement import OnlineProduct as EntitlementProduct
from mcm_solarcheck.services.online_registration_ui import RegistrationServiceController


def build_online_window(
    product: OnlineProduct,
    *,
    project_service=None,
    registration_controller=None,
) -> SolarCheckMainWindow:
    """Build the online shell with the production entry gate wired by construction."""
    if not isinstance(product, OnlineProduct):
        raise TypeError("product must be OnlineProduct")
    if registration_controller is None:
        registration_service = getattr(product.services, "registration", None)
        if registration_service is not None:
            registration_controller = RegistrationServiceController(
                registration_service,
                product=EntitlementProduct.TRIAL,
            )
    return SolarCheckMainWindow(
        DeploymentMode.ONLINE,
        project_service=project_service,
        customer_entry=product,
        on_register=(
            registration_controller.register
            if registration_controller is not None
            else None
        ),
        on_email_verification=(
            registration_controller.verify_email_token
            if registration_controller is not None
            else None
        ),
    )
