import pytest

from mcm_solarcheck.services.deployment import (
    OFFLINE_ENTRY,
    ONLINE_ENTRY,
    DeploymentMode,
    entry_capabilities,
    validate_profile_for_deployment,
)
from mcm_solarcheck.services.product_entitlements import ProductProfileId


def test_online_entry_requires_online_commercial_boundary() -> None:
    assert ONLINE_ENTRY.login_required is True
    assert ONLINE_ENTRY.trial_selection_available is True
    assert ONLINE_ENTRY.commercial_quote_required is True
    assert ONLINE_ENTRY.online_payment_required is True


def test_offline_entry_has_no_online_commercial_boundary() -> None:
    assert OFFLINE_ENTRY.login_required is False
    assert OFFLINE_ENTRY.trial_selection_available is False
    assert OFFLINE_ENTRY.commercial_quote_required is False
    assert OFFLINE_ENTRY.online_payment_required is False


@pytest.mark.parametrize(
    "deployment, profile_id",
    [
        (DeploymentMode.ONLINE, ProductProfileId.PROMOTIONAL_TRIAL),
        (DeploymentMode.ONLINE, ProductProfileId.FULL_ONLINE),
        (DeploymentMode.OFFLINE_DESKTOP, ProductProfileId.OFFLINE_DESKTOP),
    ],
)
def test_valid_deployment_profile_combinations_are_accepted(
    deployment: DeploymentMode, profile_id: ProductProfileId
) -> None:
    validate_profile_for_deployment(deployment, profile_id)


@pytest.mark.parametrize(
    "deployment, profile_id",
    [
        (DeploymentMode.OFFLINE_DESKTOP, ProductProfileId.PROMOTIONAL_TRIAL),
        (DeploymentMode.OFFLINE_DESKTOP, ProductProfileId.FULL_ONLINE),
        (DeploymentMode.ONLINE, ProductProfileId.OFFLINE_DESKTOP),
    ],
)
def test_cross_deployment_profiles_are_rejected(
    deployment: DeploymentMode, profile_id: ProductProfileId
) -> None:
    with pytest.raises(ValueError):
        validate_profile_for_deployment(deployment, profile_id)


def test_entry_capabilities_resolve_explicit_deployment() -> None:
    assert entry_capabilities(DeploymentMode.ONLINE) is ONLINE_ENTRY
    assert entry_capabilities(DeploymentMode.OFFLINE_DESKTOP) is OFFLINE_ENTRY


@pytest.mark.parametrize(
    "deployment, profile_id",
    [
        ("online", ProductProfileId.FULL_ONLINE),
        (DeploymentMode.ONLINE, "full_online"),
    ],
)
def test_raw_strings_fail_closed(deployment: object, profile_id: object) -> None:
    with pytest.raises(ValueError):
        validate_profile_for_deployment(deployment, profile_id)  # type: ignore[arg-type]
