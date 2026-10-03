"""Customer-facing shell composition for the SolarCheck Online product."""

from __future__ import annotations

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.online.product import OnlineProduct
from mcm_solarcheck.services.deployment import DeploymentMode


def build_online_window(
    product: OnlineProduct,
    *,
    project_service=None,
) -> SolarCheckMainWindow:
    """Build the online shell with the production entry gate wired by construction."""
    if not isinstance(product, OnlineProduct):
        raise TypeError("product must be OnlineProduct")
    return SolarCheckMainWindow(
        DeploymentMode.ONLINE,
        project_service=project_service,
        customer_entry=product,
    )
