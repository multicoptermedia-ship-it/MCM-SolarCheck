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


class Services:
    def __init__(self, production: Production) -> None:
        self.production = production


def test_online_window_starts_at_login_and_blocks_inactive_workflow() -> None:
    application = QApplication.instance() or QApplication([])
    production = Production(False)
    product = OnlineProduct.compose(Services(production))
    window = build_online_window(product)

    assert application is not None
    assert window.current_route is ShellRoute.LOGIN

    with pytest.raises(RuntimeError, match="production inactive"):
        window.show_route(ShellRoute.PROJECT)

    assert window.current_route is ShellRoute.LOGIN


def test_online_window_allows_workflow_after_product_activation_state() -> None:
    application = QApplication.instance() or QApplication([])
    production = Production(True)
    product = OnlineProduct.compose(Services(production))
    window = build_online_window(product)

    window.show_route(ShellRoute.PROJECT)

    assert application is not None
    assert window.current_route is ShellRoute.PROJECT


def test_online_window_requires_explicit_online_product() -> None:
    with pytest.raises(TypeError, match="OnlineProduct"):
        build_online_window(object())
