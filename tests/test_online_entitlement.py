from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mcm_solarcheck.services.online_entitlement import (
    OnlineEntitlement,
    OnlineEntitlementService,
    OnlineProduct,
)
from mcm_solarcheck.services.registration import OnlineRegistration


@pytest.mark.parametrize("product", [OnlineProduct.TRIAL, OnlineProduct.FULL])
def test_online_entitlement_requires_verified_email_identity(
    product: OnlineProduct,
) -> None:
    service = OnlineEntitlementService()
    entitlement = OnlineEntitlement("user-a", product)
    pending = OnlineRegistration(
        "user-a", "MCM Dronetech", "user@example.com"
    )

    with pytest.raises(PermissionError, match="verified"):
        service.activate(entitlement, pending)

    verified = pending.verify(
        datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    )
    activated = service.activate(entitlement, verified)

    assert activated.active
    assert activated.product is product
    assert service.activate(activated, verified) == activated


def test_online_entitlement_cannot_use_another_verified_identity() -> None:
    service = OnlineEntitlementService()
    verified = OnlineRegistration(
        "user-b", "Other Company", "other@example.com"
    ).verify(datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc))

    with pytest.raises(PermissionError, match="does not match"):
        service.activate(
            OnlineEntitlement("user-a", OnlineProduct.TRIAL),
            verified,
        )
