"""Offline-only project reader using the existing SQLite application service."""
from __future__ import annotations

from pathlib import Path

from shared_ui.project_adapter import list_project_summaries


def offline_project_list(database_path: str | Path) -> list[dict[str, str]]:
    from mcm_solarcheck.offline.composition import build_offline_services

    return list_project_summaries(build_offline_services(database_path).projects)
