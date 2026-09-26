"""Workflow navigation widgets for the SolarCheck desktop shell.

Navigation is structural only. Backend-derived availability will control enabled
state separately; this widget never invents completion or readiness.
"""

from collections.abc import Callable

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

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
        self._blocker_label = QLabel(self)
        self._blocker_label.setObjectName("workflow_blocker_explanation")
        self._blocker_label.setWordWrap(True)
        self._blocker_label.hide()
        layout = QVBoxLayout(self)
        for route in routes:
            button = QPushButton(_ROUTE_LABELS[route], self)
            button.setObjectName(f"{route.value}_navigation")
            button.clicked.connect(
                lambda checked=False, target=route: on_route_requested(target)
            )
            layout.addWidget(button)
            self._buttons[route] = button
        layout.addWidget(self._blocker_label)
        layout.addStretch(1)

    def button(self, route: ShellRoute) -> QPushButton:
        return self._buttons[route]

    def set_current_route(self, route: ShellRoute) -> None:
        for candidate, button in self._buttons.items():
            is_current = candidate is route
            button.setProperty("current", is_current)
            button.setAccessibleName(
                f"{button.text()}, aktueller Bereich" if is_current else button.text()
            )
            button.style().unpolish(button)
            button.style().polish(button)


    def explain_blocker(self, route: ShellRoute) -> None:
        button = self._buttons[route]
        if button.property("blocked") is not True:
            self._blocker_label.clear()
            self._blocker_label.hide()
            return
        blocker = button.toolTip()
        self._blocker_label.setText(
            f"{button.text()} ist blockiert: {blocker}"
        )
        self._blocker_label.show()
