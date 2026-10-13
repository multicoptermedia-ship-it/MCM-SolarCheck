"""Read-only adapter for existing project application services."""
from __future__ import annotations

from typing import Protocol


class ProjectReader(Protocol):
    def projects(self): ...


def list_project_summaries(reader: ProjectReader) -> list[dict[str, str]]:
    """Convert persisted ProjectRecord values without inventing project data.

    Do not pass an unrestricted online service: online callers must use a
    separately authorized, customer-scoped reader.
    """
    return [
        {"id": str(project.project_id), "name": str(project.name)}
        for project in reader.projects()
    ]
