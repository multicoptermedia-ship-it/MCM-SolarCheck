import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QStackedWidget, QWidget

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.gui.theme import APP_STYLE_SHEET, ANTHRACITE, WORK_SURFACE, ACCENT_GREEN
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def app() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


def test_online_shell_starts_at_login(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)

    assert window.current_route is ShellRoute.LOGIN


def test_offline_shell_starts_at_project_without_login_route(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)

    assert window.current_route is ShellRoute.PROJECT
    with pytest.raises(ValueError):
        window.show_route(ShellRoute.LOGIN)


@pytest.mark.parametrize(
    "command_id, expected_route",
    [
        (ShellCommandId.IMPORT, ShellRoute.IMPORT),
        (ShellCommandId.PROCESS, ShellRoute.PROCESSING),
        (ShellCommandId.PLANT_OVERVIEW, ShellRoute.PLANT_OVERVIEW),
        (ShellCommandId.REVIEW, ShellRoute.REVIEW),
        (ShellCommandId.REPORT, ShellRoute.REPORT),
        (ShellCommandId.EXPORT, ShellRoute.EXPORT),
    ],
)
def test_menu_actions_use_shared_navigation(
    app: QApplication, command_id: ShellCommandId, expected_route: ShellRoute
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)

    window.action(command_id).trigger()

    assert window.current_route is expected_route


def test_user_guide_command_is_exposed_in_help(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)

    assert window.action(ShellCommandId.USER_GUIDE).objectName() == "user_guide_action"


def test_online_entry_exposes_login_guide_and_provider_attribution(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)
    page = window.findChild(QStackedWidget).currentWidget()

    assert page.objectName() == "login_page"
    assert page.findChild(type(page), "project_page") is None
    assert page.findChild(QLabel, "login_hint") is not None
    guide = page.findChild(QLabel, "user_guide_hint")
    provider = page.findChild(QLabel, "provider_attribution")

    assert guide is not None
    assert "Hilfe" in guide.text()
    assert provider is not None
    assert provider.text() == "powered by MCM-Dronetech GmbH"


def test_offline_entry_has_no_online_login_or_provider_elements(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    page = window.findChild(QStackedWidget).currentWidget()
    assert page.objectName() == "project_page"
    assert page.findChild(QLabel, "login_hint") is None
    assert page.findChild(QLabel, "provider_attribution") is None
    assert page.findChild(QLabel, "user_guide_hint") is None


def test_shell_uses_central_theme_tokens(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)

    assert window.styleSheet() == APP_STYLE_SHEET
    assert ANTHRACITE in APP_STYLE_SHEET
    assert WORK_SURFACE in APP_STYLE_SHEET
    assert ACCENT_GREEN.startswith("#")


def test_workflow_navigation_uses_shared_route_order(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    navigation = window.findChild(QWidget, "workflow_navigation")
    assert navigation is not None

    expected = [
        ("project_navigation", "Projekt"),
        ("import_navigation", "Import"),
        ("processing_navigation", "Verarbeitung"),
        ("plant_overview_navigation", "Anlagenübersicht"),
        ("review_navigation", "Review"),
        ("report_navigation", "Bericht"),
        ("export_navigation", "Export"),
    ]
    buttons = navigation.findChildren(QPushButton)
    assert [(button.objectName(), button.text()) for button in buttons] == expected


def test_workflow_navigation_routes_through_shell(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    button = window.findChild(QPushButton, "review_navigation")

    assert button is not None
    button.click()

    assert window.current_route is ShellRoute.REVIEW


def test_current_workflow_location_has_non_color_accessible_state(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    review = window.findChild(QPushButton, "review_navigation")
    project = window.findChild(QPushButton, "project_navigation")

    assert review is not None
    assert project is not None
    review.click()

    assert review.property("current") is True
    assert review.accessibleName() == "Review, aktueller Bereich"
    assert project.property("current") is False
    assert project.accessibleName() == "Projekt"
