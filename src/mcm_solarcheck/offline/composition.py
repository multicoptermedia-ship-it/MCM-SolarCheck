"""Composition boundary for the SolarCheck Offline Desktop product."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.storage.sqlite import ProjectDatabase


@dataclass(frozen=True)
class OfflineServices:
    projects: ProjectApplicationService


def build_offline_services(database_path: str | Path) -> OfflineServices:
    """Compose offline services without importing online infrastructure."""
    database = ProjectDatabase(database_path)
    database.initialize()
    return OfflineServices(projects=ProjectApplicationService(database))
