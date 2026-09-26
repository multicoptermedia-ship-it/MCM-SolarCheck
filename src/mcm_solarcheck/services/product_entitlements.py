"""Backend-authoritative product capabilities for SolarCheck application shells.

These profiles describe product entitlement only. They never replace workflow,
review, provenance, report-release, or export validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProductProfileId(str, Enum):
    PROMOTIONAL_TRIAL = "promotional_trial"
    FULL_ONLINE = "full_online"


@dataclass(frozen=True)
class ProductCapabilities:
    profile_id: ProductProfileId
    max_plant_power_kwp: float | None
    report_download_allowed: bool
    export_allowed: bool

    def __post_init__(self) -> None:
        if self.max_plant_power_kwp is not None and self.max_plant_power_kwp <= 0:
            raise ValueError("max_plant_power_kwp must be positive when configured")

    def accepts_plant_power(self, plant_power_kwp: float) -> bool:
        if plant_power_kwp < 0:
            raise ValueError("plant_power_kwp must not be negative")
        return (
            self.max_plant_power_kwp is None
            or plant_power_kwp <= self.max_plant_power_kwp
        )

    def require_plant_power(self, plant_power_kwp: float) -> None:
        if not self.accepts_plant_power(plant_power_kwp):
            raise ProductEntitlementError(
                f"{self.profile_id.value} permits at most "
                f"{self.max_plant_power_kwp:g} kWp"
            )

    def require_report_download(self) -> None:
        if not self.report_download_allowed:
            raise ProductEntitlementError(
                f"{self.profile_id.value} does not permit report download"
            )

    def require_export(self) -> None:
        if not self.export_allowed:
            raise ProductEntitlementError(
                f"{self.profile_id.value} does not permit export"
            )


class ProductEntitlementError(PermissionError):
    """Raised when a product profile does not permit an application operation."""


PROMOTIONAL_TRIAL = ProductCapabilities(
    profile_id=ProductProfileId.PROMOTIONAL_TRIAL,
    max_plant_power_kwp=20.0,
    report_download_allowed=False,
    export_allowed=False,
)

FULL_ONLINE = ProductCapabilities(
    profile_id=ProductProfileId.FULL_ONLINE,
    max_plant_power_kwp=None,
    report_download_allowed=True,
    export_allowed=True,
)


def product_capabilities(profile_id: ProductProfileId) -> ProductCapabilities:
    if profile_id is ProductProfileId.PROMOTIONAL_TRIAL:
        return PROMOTIONAL_TRIAL
    if profile_id is ProductProfileId.FULL_ONLINE:
        return FULL_ONLINE
    raise ValueError(f"unsupported product profile: {profile_id!r}")
