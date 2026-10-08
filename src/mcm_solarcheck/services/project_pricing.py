"""Application service for deterministic online project pricing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from mcm_solarcheck.domain.pricing import PriceSnapshot, PricingRule


@dataclass(frozen=True)
class DiscountEligibility:
    planner_verified: bool = False
    repeat_verified: bool = False


@dataclass(frozen=True)
class ProjectPricingRequest:
    customer_id: str
    project_id: str


class ProjectPricingService:
    def __init__(
        self,
        pricing_rule: PricingRule,
        capacity_for_project: Callable[[str, str], Decimal],
        discount_eligibility_for_project: Callable[[str, str], DiscountEligibility] | None = None,
    ) -> None:
        self._pricing_rule = pricing_rule
        self._capacity_for_project = capacity_for_project
        self._discount_eligibility_for_project = discount_eligibility_for_project

    def price(self, request: ProjectPricingRequest) -> PriceSnapshot:
        customer_id = request.customer_id.strip()
        project_id = request.project_id.strip()
        if not customer_id:
            raise ValueError("customer_id is required")
        if not project_id:
            raise ValueError("project_id is required")
        capacity_kwp = self._capacity_for_project(customer_id, project_id)
        eligibility = (
            self._discount_eligibility_for_project(customer_id, project_id)
            if self._discount_eligibility_for_project is not None
            else DiscountEligibility()
        )
        if not isinstance(eligibility, DiscountEligibility):
            raise TypeError("discount eligibility must be server-owned DiscountEligibility")
        return self._pricing_rule.price(
            capacity_kwp,
            planner_verified=eligibility.planner_verified,
            repeat_verified=eligibility.repeat_verified,
        )
