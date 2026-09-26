"""Workflow navigation widgets for the SolarCheck desktop shell.

Navigation is structural only. Backend-derived availability will control enabled
state separately; this widget never invents completion or readiness.
"""

from collections.abc import Callable

from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from mcm_solarcheck.services.shell_navigation import ShellRoute

_ROUTE_LABELS = {
    ShellRoute.PROJECT: "Projekt",
    ShellRoute.IMPORT: "Import",
    ShellRoute.PROCESSING: "Verarbeitung",
    ShellRoute.PLANT_OVERVIEW: "Anlagenübersicht",
    ShellRoute.REVIEW: "Review",
    ShellRoute.REPORT: "Bericht",
    ShellRoute.EXPORT: "Export",
}


class WorkflowNavigation(QWidget):
    def __init__(
        self,
        routes: tuple[ShellRoute, ...],
        on_route_requested: Callable[[ShellRoute], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("workflow_navigation")
        self._buttons: dict[ShellRoute, QPushButton] = {}
        layout = QVBoxLayout(self)
        for route in routes:
            button = QPushButton(_ROUTE_LABELS[route], self)
            button.setObjectName(f"{route.value}_navigation")
            button.clicked.connect(
                lambda checked=False, target=route: on_route_requested(target)
            )
            layout.addWidget(button)
            self._buttons[route] = button
        layout.addStretch(1)

    def button(self, route: ShellRoute) -> QPushButton:
        return self._buttons[route]

    def set_current_route(self, route: ShellRoute) -> None:
        for candidate, button in self._buttons.items():
            button.setProperty("current", candidate is route)
