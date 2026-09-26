"""Deployment-aware entry pages for the SolarCheck desktop shell."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_policy import shell_policy


def make_entry_page(deployment: DeploymentMode) -> QWidget:
    """Build the deployment entry page without duplicating product policy."""
    policy = shell_policy(deployment)
    page = QWidget()
    layout = QVBoxLayout(page)

    if policy.show_login:
        page.setObjectName("login_page")
        heading = QLabel("MCM SolarCheck", page)
        heading.setObjectName("page_heading")
        layout.addWidget(heading)

        login_hint = QLabel("Anmelden, um SolarCheck Online zu verwenden.", page)
        login_hint.setObjectName("login_hint")
        layout.addWidget(login_hint)

        if policy.show_user_guide_hint:
            guide_hint = QLabel(
                "Die Bedienungsanleitung finden Sie jederzeit im Menü Hilfe.",
                page,
            )
            guide_hint.setObjectName("user_guide_hint")
            layout.addWidget(guide_hint)
    else:
        page.setObjectName("project_page")
        heading = QLabel("Projekt", page)
        heading.setObjectName("page_heading")
        layout.addWidget(heading)

    return page
