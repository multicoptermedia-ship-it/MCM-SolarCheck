import pytest

from mcm_solarcheck.services.sepa import SepaMandate, SepaMandateStatus


def test_sepa_mandate_requires_provider_activation() -> None:
    mandate = SepaMandate("mandate-a", "user-a", "provider-a")

    assert mandate.status is SepaMandateStatus.PENDING

    active = mandate.activate("provider-mandate-a")
    assert active.status is SepaMandateStatus.ACTIVE
    assert active.provider_reference == "provider-mandate-a"


def test_revoked_mandate_cannot_be_reactivated() -> None:
    active = SepaMandate(
        "mandate-a", "user-a", "provider-a"
    ).activate("provider-mandate-a")

    revoked = active.revoke()
    assert revoked.status is SepaMandateStatus.REVOKED

    with pytest.raises(ValueError, match="pending"):
        revoked.activate("provider-mandate-b")
