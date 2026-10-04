"""Application boundary for creating customer upload projects."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable


@dataclass(frozen=True)
class CreateProjectRequest:
    customer_id: str
    project_id: str
    name: str
    capacity_kwp: Decimal


@dataclass(frozen=True)
class CustomerProject:
    customer_id: str
    project_id: str
    name: str
    capacity_kwp: Decimal


class ProjectCreationService:
    def __init__(self, store_project: Callable[[CustomerProject], None]) -> None:
        self._store_project = store_project

    def create(self, request: CreateProjectRequest) -> CustomerProject:
        customer_id = request.customer_id.strip()
        project_id = request.project_id.strip()
        name = request.name.strip()
        if not customer_id:
            raise ValueError("customer_id is required")
        if not project_id:
            raise ValueError("project_id is required")
        if not name:
            raise ValueError("project name is required")
        if request.capacity_kwp <= 0:
            raise ValueError("capacity_kwp must be positive")

        project = CustomerProject(
            customer_id=customer_id,
            project_id=project_id,
            name=name,
            capacity_kwp=request.capacity_kwp,
        )
        self._store_project(project)
        return project
