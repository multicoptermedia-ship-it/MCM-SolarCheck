"""Workflow navigation widgets for the SolarCheck desktop shell.

Navigation is structural only. Backend-derived availability will control enabled
state separately; this widget never invents completion or readiness.
"""

from collections.abc import Callable

from PySide6.QtCore import Qt
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
        # Windows 10 must actually paint the dark sidebar background.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(240)
        self._statuses: dict[ShellRoute, QLabel] = {}
        self._buttons: dict[ShellRoute, QPushButton] = {}
        self._blocker_label = QLabel(self)
        self._blocker_label.setObjectName("workflow_blocker_explanation")
        self._blocker_label.setWordWrap(True)
        self._blocker_label.hide()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(3)
        for route in routes:
            button = QPushButton(_ROUTE_LABELS[route], self)
            button.setObjectName(f"{route.value}_navigation")
            button.clicked.connect(
                lambda checked=False, target=route: on_route_requested(target)
            )
            layout.addWidget(button)
            self._buttons[route] = button
            status = QLabel("Schritt anzeigen", self)
            status.setObjectName(f"{route.value}_navigation_status")
            status.setProperty("navigationStatus", True)
            status.setWordWrap(True)
            layout.addWidget(status)
            self._statuses[route] = status
        layout.addWidget(self._blocker_label)
        layout.addStretch(1)

    def button(self, route: ShellRoute) -> QPushButton:
        return self._buttons[route]

    def set_current_route(self, route: ShellRoute) -> None:
        self.clear_blocker_explanation()
        for candidate, button in self._buttons.items():
            is_current = candidate is route
            button.setProperty("current", is_current)
            button.setAccessibleName(
                f"{button.text()}, aktueller Bereich" if is_current else button.text()
            )
            button.style().unpolish(button)
            button.style().polish(button)
            self._statuses[candidate].setText(
                "Aktueller Bereich" if is_current
                else "Noch nicht bereit – für Erklärung anklicken"
                if button.property("blocked") is True
                else "Bereit zur Auswahl"
            )

    def set_availability(self, route: ShellRoute, available: bool) -> None:
        # Buttons remain clickable so blocked steps can explain prerequisites.
        button = self._buttons[route]
        self._statuses[route].setText(
            "Aktueller Bereich" if button.property("current") is True
            else "Bereit zur Auswahl" if available
            else "Noch nicht bereit – für Erklärung anklicken"
        )

    def clear_blocker_explanation(self) -> None:
        self._blocker_label.clear()
        self._blocker_label.hide()

    def explain_blocker(self, route: ShellRoute) -> None:
        button = self._buttons[route]
        if button.property("blocked") is not True:
            self.clear_blocker_explanation()
            return
        blocker = button.toolTip()
        self._blocker_label.setText(
            f"{button.text()} ist blockiert: {blocker}"
        )
        self._blocker_label.show()
