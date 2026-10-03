from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute, shell_navigation


EXPECTED_WORKFLOW = (
    ShellRoute.PROJECT,
    ShellRoute.IMPORT,
    ShellRoute.PROCESSING,
    ShellRoute.PLANT_OVERVIEW,
    ShellRoute.REVIEW,
    ShellRoute.REPORT,
    ShellRoute.EXPORT,
)


def test_online_navigation_starts_at_login_then_uses_shared_workflow() -> None:
    navigation = shell_navigation(DeploymentMode.ONLINE)

    assert navigation.initial_route is ShellRoute.LOGIN
    assert navigation.workflow_routes == EXPECTED_WORKFLOW


def test_offline_navigation_skips_login_and_uses_shared_workflow() -> None:
    navigation = shell_navigation(DeploymentMode.OFFLINE_DESKTOP)

    assert navigation.initial_route is ShellRoute.PROJECT
    assert navigation.workflow_routes == EXPECTED_WORKFLOW
    assert ShellRoute.LOGIN not in navigation.workflow_routes


def test_shared_workflow_route_order_matches_frozen_gui_contract() -> None:
    online = shell_navigation(DeploymentMode.ONLINE)
    offline = shell_navigation(DeploymentMode.OFFLINE_DESKTOP)

    assert online.workflow_routes == offline.workflow_routes == EXPECTED_WORKFLOW
    assert len(set(EXPECTED_WORKFLOW)) == len(EXPECTED_WORKFLOW)
