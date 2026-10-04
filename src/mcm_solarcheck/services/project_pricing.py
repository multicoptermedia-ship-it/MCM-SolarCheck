"""Application service for deterministic online project pricing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from mcm_solarcheck.domain.pricing import PriceSnapshot, PricingRule


@dataclass(frozen=True)
class ProjectPricingRequest:
    customer_id: str
    project_id: str
    planner_verified: bool = False
    repeat_verified: bool = False


class ProjectPricingService:
    def __init__(
        self,
        pricing_rule: PricingRule,
        capacity_for_project: Callable[[str, str], Decimal],
    ) -> None:
        self._pricing_rule = pricing_rule
        self._capacity_for_project = capacity_for_project

    def price(self, request: ProjectPricingRequest) -> PriceSnapshot:
        customer_id = request.customer_id.strip()
        project_id = request.project_id.strip()
        if not customer_id:
            raise ValueError("customer_id is required")
        if not project_id:
            raise ValueError("project_id is required")
        capacity_kwp = self._capacity_for_project(customer_id, project_id)
        return self._pricing_rule.price(
            capacity_kwp,
            planner_verified=request.planner_verified,
            repeat_verified=request.repeat_verified,
        )
