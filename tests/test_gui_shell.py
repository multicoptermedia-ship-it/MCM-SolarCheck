import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
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
