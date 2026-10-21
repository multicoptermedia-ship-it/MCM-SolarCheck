"""Executable composition for the SolarCheck Offline Desktop product."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from PySide6.QtWidgets import QApplication

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.offline.product import OfflineProduct
from mcm_solarcheck.services.offline_admin_credentials import default_admin_credential_path
from mcm_solarcheck.services.offline_admin_audit_sessions import OfflineAdminAuditSessions
from mcm_solarcheck.services.offline_report_training import OfflineReportTraining
from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit
from mcm_solarcheck.services.deployment import DeploymentMode

APP_NAME = "MCM-SolarCheck"


def default_database_path() -> Path:
    """Return the local per-user database used by the offline desktop product."""
    return Path.home() / "MCM-SolarCheck" / "solarcheck.sqlite3"


def build_offline_window(
    database_path: str | Path, *, training_configuration=None,
    training_launcher=None,
) -> SolarCheckMainWindow:
    """Offline shell; a reviewed trainer must be explicitly injected by the operator.

    The shipped desktop intentionally has neither model weights nor an
    automatically trusted training executable. No implicit downloads.
    """
    product = OfflineProduct()
    product.require_customer_entry()
    services = build_offline_services(database_path)
    # An operator may have explicitly provisioned locally generated OSS weights.
    # No config means no trainer and no optional AI imports/downloads.
    # A malformed existing config disables training without blocking inspections.
    if training_configuration is None and training_launcher is None:
        from mcm_solarcheck.offline.ai_setup import load_local_torchvision_training
        try:
            enabled = load_local_torchvision_training(database_path)
        except (ValueError, PermissionError, OSError, TypeError):
            enabled = None
        if enabled is not None:
            training_configuration, training_launcher = enabled
    # Credentials must be installed separately; no admin account is created
    # when the application or inspection database starts.
    admin = OfflineAdminAuditSessions(
        default_admin_credential_path(database_path),
        AuthorizedReportPreviewAudit(services.projects.database),
    )
    return SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP,
        project_service=services.projects,
        offline_admin_sessions=admin,
        offline_report_training=OfflineReportTraining(
            services.projects,
            training_configuration=training_configuration,
            training_launcher=training_launcher,
        ),
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
