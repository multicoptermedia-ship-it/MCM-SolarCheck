from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from mcm_solarcheck.online.entrypoint import build_online_window
from mcm_solarcheck.online.product import OnlineProduct
from mcm_solarcheck.services.shell_navigation import ShellRoute


class Production:
    def __init__(self, active: bool = False) -> None:
        self.active = active

    def require_active(self) -> None:
        if not self.active:
            raise RuntimeError("production inactive")


class Entitlements:
    def __init__(self, active_users=()) -> None:
        self.active_users = set(active_users)

    def require_active(self, user_id: str) -> None:
        if user_id not in self.active_users:
            raise PermissionError("entitlement inactive")


class Services:
    def __init__(self, production: Production, *, projects=None, active_users=()) -> None:
        self.production = production
        self.projects = projects
        self.entitlements = Entitlements(active_users)


def test_online_window_starts_at_login_and_blocks_inactive_workflow() -> None:
    application = QApplication.instance() or QApplication([])
    production = Production(False)
    product = OnlineProduct.compose(Services(production))
    window = build_online_window(product)

    assert application is not None
    assert window.current_route is ShellRoute.LOGIN

    with pytest.raises(RuntimeError, match="production inactive"):
        window._enter_verified_customer("verified-user")

    assert window.current_route is ShellRoute.LOGIN


def test_online_window_allows_workflow_after_product_activation_state() -> None:
    application = QApplication.instance() or QApplication([])
    production = Production(True)
    product = OnlineProduct.compose(Services(production, active_users=("verified-user",)))
    window = build_online_window(product)

    window._enter_verified_customer("verified-user")

    assert application is not None
    assert window.current_route is ShellRoute.PROJECT


def test_online_window_requires_explicit_online_product() -> None:
    with pytest.raises(TypeError, match="OnlineProduct"):
        build_online_window(object())


def test_online_window_uses_composed_project_service_by_default() -> None:
    application = QApplication.instance() or QApplication([])

    class Projects:
        def projects(self):
            return ()

    projects = Projects()
    product = OnlineProduct.compose(Services(Production(True), projects=projects))
    window = build_online_window(product)

    assert application is not None
    assert window._project_service is projects


def test_online_window_allows_explicit_project_service_override() -> None:
    application = QApplication.instance() or QApplication([])

    class Projects:
        def projects(self):
            return ()

    composed = Projects()
    override = Projects()
    product = OnlineProduct.compose(Services(Production(True), projects=composed))
    window = build_online_window(product, project_service=override)

    assert application is not None
    assert window._project_service is override
