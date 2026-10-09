"""Read-only adapter for existing project application services.

Does not bypass online identity or customer ownership checks. Online must
supply an authorized, customer-scoped project service.
"""
from __future__ import annotations

from typing import Protocol


class ProjectReader(Protocol):
    def list_projects(self): ...


def list_project_summaries(reader: ProjectReader) -> list[dict]:
    """Normalize authorized project objects for the shared UI."""
    result = []
    for project in reader.list_projects():
        result.append({
            "id": str(project.id),
            "name": str(project.name),
        })
    return result
