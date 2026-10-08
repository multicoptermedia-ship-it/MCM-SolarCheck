"""Deployment-aware entry capabilities for online and offline SolarCheck shells."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mcm_solarcheck.services.product_entitlements import ProductProfileId


class DeploymentMode(str, Enum):
    ONLINE = "online"
    OFFLINE_DESKTOP = "offline_desktop"


@dataclass(frozen=True)
class EntryCapabilities:
    deployment: DeploymentMode
    login_required: bool
    trial_selection_available: bool
    commercial_quote_required: bool
    online_payment_required: bool


ONLINE_ENTRY = EntryCapabilities(
    deployment=DeploymentMode.ONLINE,
    login_required=True,
    trial_selection_available=True,
    commercial_quote_required=True,
    online_payment_required=True,
)

OFFLINE_ENTRY = EntryCapabilities(
    deployment=DeploymentMode.OFFLINE_DESKTOP,
    login_required=False,
    trial_selection_available=False,
    commercial_quote_required=False,
    online_payment_required=False,
)


def entry_capabilities(deployment: DeploymentMode) -> EntryCapabilities:
    if deployment is DeploymentMode.ONLINE:
        return ONLINE_ENTRY
    if deployment is DeploymentMode.OFFLINE_DESKTOP:
        return OFFLINE_ENTRY
    raise ValueError(f"unsupported deployment mode: {deployment!r}")


def validate_profile_for_deployment(
    deployment: DeploymentMode, profile_id: ProductProfileId
) -> None:
    """Reject product/deployment combinations that could mix online and offline entry."""
    if not isinstance(deployment, DeploymentMode):
        raise ValueError("deployment must be a DeploymentMode")
    if not isinstance(profile_id, ProductProfileId):
        raise ValueError("profile_id must be a ProductProfileId")

    if deployment is DeploymentMode.OFFLINE_DESKTOP:
        if profile_id is not ProductProfileId.OFFLINE_DESKTOP:
            raise ValueError("offline desktop requires offline_desktop product profile")
        return

    if profile_id is ProductProfileId.OFFLINE_DESKTOP:
        raise ValueError("online deployment cannot use offline_desktop product profile")
