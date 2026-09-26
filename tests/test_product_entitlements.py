from __future__ import annotations

import pytest

from mcm_solarcheck.services.product_entitlements import (
    FULL_ONLINE,
    PROMOTIONAL_TRIAL,
    ProductEntitlementError,
    ProductProfileId,
    ProductOperation,
    product_capabilities,
    require_product_operation,
)


def test_promotional_trial_accepts_exactly_20_kwp() -> None:
    assert PROMOTIONAL_TRIAL.accepts_plant_power(20.0)


def test_promotional_trial_rejects_power_above_20_kwp() -> None:
    assert not PROMOTIONAL_TRIAL.accepts_plant_power(20.001)
    with pytest.raises(ProductEntitlementError, match="at most 20 kWp"):
        PROMOTIONAL_TRIAL.require_plant_power(20.001)


def test_promotional_trial_rejects_report_download_and_export() -> None:
    with pytest.raises(ProductEntitlementError, match="report download"):
        PROMOTIONAL_TRIAL.require_report_download()
    with pytest.raises(ProductEntitlementError, match="export"):
        PROMOTIONAL_TRIAL.require_export()


def test_full_online_has_no_product_power_ceiling_and_allows_outputs() -> None:
    assert FULL_ONLINE.accepts_plant_power(1_000_000.0)
    FULL_ONLINE.require_plant_power(1_000_000.0)
    FULL_ONLINE.require_report_download()
    FULL_ONLINE.require_export()


def test_negative_power_is_rejected_for_all_profiles() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        PROMOTIONAL_TRIAL.accepts_plant_power(-0.001)
    with pytest.raises(ValueError, match="must not be negative"):
        FULL_ONLINE.require_plant_power(-0.001)


def test_profile_lookup_returns_authoritative_capabilities() -> None:
    assert product_capabilities(ProductProfileId.PROMOTIONAL_TRIAL) is PROMOTIONAL_TRIAL
    assert product_capabilities(ProductProfileId.FULL_ONLINE) is FULL_ONLINE


def test_product_operation_boundary_blocks_trial_outputs() -> None:
    with pytest.raises(ProductEntitlementError, match="report download"):
        require_product_operation(PROMOTIONAL_TRIAL, ProductOperation.REPORT_DOWNLOAD)
    with pytest.raises(ProductEntitlementError, match="export"):
        require_product_operation(PROMOTIONAL_TRIAL, ProductOperation.EXPORT)


def test_product_operation_boundary_allows_full_online_outputs() -> None:
    require_product_operation(FULL_ONLINE, ProductOperation.REPORT_DOWNLOAD)
    require_product_operation(FULL_ONLINE, ProductOperation.EXPORT)


def test_product_operation_boundary_rejects_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="capabilities"):
        require_product_operation(None, ProductOperation.EXPORT)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="ProductOperation"):
        require_product_operation(FULL_ONLINE, "export")  # type: ignore[arg-type]
