"""PySide6 application shell for SolarCheck.

Widgets stay deliberately thin: deployment and workflow decisions are supplied
by service-layer contracts rather than reimplemented in Qt.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute, shell_navigation


class SolarCheckMainWindow(QMainWindow):
    def __init__(self, deployment: DeploymentMode) -> None:
        super().__init__()
        self._navigation = shell_navigation(deployment)
        self._pages: dict[ShellRoute, QWidget] = {}

        self.setWindowTitle("MCM SolarCheck")
        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        routes = list(self._navigation.workflow_routes)
        if self._navigation.initial_route is ShellRoute.LOGIN:
            routes.insert(0, ShellRoute.LOGIN)

        for route in routes:
            page = self._make_placeholder_page(route)
            self._pages[route] = page
            self._stack.addWidget(page)

        self.show_route(self._navigation.initial_route)

    @property
    def current_route(self) -> ShellRoute:
        widget = self._stack.currentWidget()
        for route, page in self._pages.items():
            if page is widget:
                return route
        raise RuntimeError("current page is not registered")

    def show_route(self, route: ShellRoute) -> None:
        try:
            page = self._pages[route]
        except KeyError as exc:
            raise ValueError(f"route is unavailable in this deployment: {route.value}") from exc
        self._stack.setCurrentWidget(page)

    @staticmethod
    def _make_placeholder_page(route: ShellRoute) -> QWidget:
        page = QWidget()
        page.setObjectName(f"{route.value}_page")
        layout = QVBoxLayout(page)
        heading = QLabel(route.value.replace("_", " ").title(), page)
        heading.setObjectName("page_heading")
        layout.addWidget(heading)
        return page
