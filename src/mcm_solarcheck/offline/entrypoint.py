"""Executable composition for the SolarCheck Offline Desktop product."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from PySide6.QtWidgets import QApplication

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.offline.product import OfflineProduct
from mcm_solarcheck.services.deployment import DeploymentMode

APP_NAME = "MCM-SolarCheck"


def default_database_path() -> Path:
    """Return the local per-user database used by the offline desktop product."""
    return Path.home() / "MCM-SolarCheck" / "solarcheck.sqlite3"


def build_offline_window(database_path: str | Path) -> SolarCheckMainWindow:
    """Compose the offline shell exclusively through the persisted project service."""
    product = OfflineProduct()
    product.require_customer_entry()
    services = build_offline_services(database_path)
    return SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP,
        project_service=services.projects,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    database_path: str | Path | None = None,
) -> int:
    """Start SolarCheck Offline without importing online product infrastructure."""
    application = QApplication(list(sys.argv if argv is None else argv))
    application.setApplicationName(APP_NAME)
    window = build_offline_window(
        default_database_path() if database_path is None else database_path
    )
    window.show()
    return application.exec()
