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
    display_number: str | None = None


class ProjectCreationService:
    def __init__(
        self, store_project: Callable[[CustomerProject], None],
        *, create_numbered=None,
    ) -> None:
        self._store_project = store_project
        self._create_numbered = create_numbered

    def create_from_anlage(
        self, *, customer_id: str, anlage: str, capacity_kwp: Decimal,
    ) -> CustomerProject:
        """Authenticated server assigns both reference and immutable ID."""
        if not isinstance(customer_id, str) or not customer_id.strip():
            raise PermissionError("Authenticated customer required")
        if not isinstance(anlage, str) or not 3 <= len(anlage.strip()) <= 80:
            raise ValueError("Anlage must have 3 to 80 characters")
        if not isinstance(capacity_kwp, Decimal) or not capacity_kwp.is_finite() or capacity_kwp <= 0:
            raise ValueError("Positive finite installed capacity required")
        if self._create_numbered is None:
            raise RuntimeError("Automatic project numbering is not configured")
        project_id, reference = self._create_numbered(
            customer_id.strip(), anlage.strip(), capacity_kwp,
        )
        return CustomerProject(
            customer_id.strip(), project_id, anlage.strip(), capacity_kwp,
            reference,
        )


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
