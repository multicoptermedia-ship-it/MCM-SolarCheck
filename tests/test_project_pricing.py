from decimal import Decimal

import pytest

from mcm_solarcheck.domain.pricing import PriceTier, PricingRule
from mcm_solarcheck.services.project_pricing import (
    DiscountEligibility,
    ProjectPricingRequest,
    ProjectPricingService,
)


def pricing_rule() -> PricingRule:
    return PricingRule(
        version="2026-10-online",
        tiers=(
            PriceTier(Decimal("30"), Decimal("300")),
            PriceTier(None, Decimal("500")),
        ),
        planner_discount_rate=Decimal("0.10"),
        repeat_discount_rate=Decimal("0.05"),
        maximum_discount_rate=Decimal("0.12"),
        vat_rate=Decimal("0.19"),
    )


def test_project_pricing_resolves_capacity_from_customer_project_metadata() -> None:
    requested = []

    def capacity_for_project(customer_id: str, project_id: str) -> Decimal:
        requested.append((customer_id, project_id))
        return Decimal("50")

    service = ProjectPricingService(pricing_rule(), capacity_for_project)

    snapshot = service.price(ProjectPricingRequest("user-1", "P-1"))

    assert requested == [("user-1", "P-1")]
    assert snapshot.capacity_kwp == Decimal("50")
    assert snapshot.net_total == Decimal("500.00")
    assert snapshot.rule_version == "2026-10-online"


def test_project_pricing_request_rejects_client_owned_discount_flags() -> None:
    with pytest.raises(TypeError):
        ProjectPricingRequest(
            "user-1",
            "P-1",
            planner_verified=True,
        )


def test_project_pricing_rejects_missing_project_id_before_metadata_access() -> None:
    def capacity_for_project(customer_id: str, project_id: str) -> Decimal:
        raise AssertionError("project metadata must not be read without a project id")

    service = ProjectPricingService(pricing_rule(), capacity_for_project)

    with pytest.raises(ValueError):
        service.price(ProjectPricingRequest("user-1", "   "))


def test_project_pricing_rejects_missing_customer_id_before_metadata_access() -> None:
    def capacity_for_project(customer_id: str, project_id: str) -> Decimal:
        raise AssertionError("project metadata must not be read without a customer id")

    service = ProjectPricingService(pricing_rule(), capacity_for_project)

    with pytest.raises(ValueError):
        service.price(ProjectPricingRequest("   ", "P-1"))

def test_project_pricing_does_not_apply_configured_discounts_without_authority() -> None:
    service = ProjectPricingService(
        pricing_rule(),
        lambda customer_id, project_id: Decimal("50"),
    )

    snapshot = service.price(ProjectPricingRequest("user-1", "P-1"))

    assert snapshot.discount_rate == Decimal("0")
    assert snapshot.discount_amount == Decimal("0.00")
    assert snapshot.net_total == Decimal("500.00")

def test_server_verified_planner_eligibility_applies_discount() -> None:
    service = ProjectPricingService(
        pricing_rule(),
        lambda customer_id, project_id: Decimal("50"),
        lambda customer_id, project_id: DiscountEligibility(planner_verified=True),
    )

    snapshot = service.price(ProjectPricingRequest("user-1", "P-1"))

    assert snapshot.discount_rate == Decimal("0.10")
    assert snapshot.net_total == Decimal("450.00")

def test_server_verified_combined_eligibility_respects_discount_cap() -> None:
    service = ProjectPricingService(
        pricing_rule(),
        lambda customer_id, project_id: Decimal("50"),
        lambda customer_id, project_id: DiscountEligibility(
            planner_verified=True,
            repeat_verified=True,
        ),
    )

    snapshot = service.price(ProjectPricingRequest("user-1", "P-1"))

    assert snapshot.discount_rate == Decimal("0.12")
    assert snapshot.discount_amount == Decimal("60.00")
    assert snapshot.net_total == Decimal("440.00")


def test_invalid_discount_authority_result_fails_closed() -> None:
    service = ProjectPricingService(
        pricing_rule(),
        lambda customer_id, project_id: Decimal("50"),
        lambda customer_id, project_id: {"planner_verified": True},
    )

    with pytest.raises(TypeError, match="server-owned DiscountEligibility"):
        service.price(ProjectPricingRequest("user-1", "P-1"))
