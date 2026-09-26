"""PySide6 application shell for SolarCheck.

Widgets stay deliberately thin: deployment and workflow decisions are supplied
by service-layer contracts rather than reimplemented in Qt.
"""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from mcm_solarcheck.gui.entry_page import make_entry_page
from mcm_solarcheck.gui.theme import APP_STYLE_SHEET
from mcm_solarcheck.gui.workflow_navigation import WorkflowNavigation
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_commands import ShellCommandId, shell_commands
from mcm_solarcheck.services.shell_navigation import ShellRoute, shell_navigation


class SolarCheckMainWindow(QMainWindow):
    def __init__(self, deployment: DeploymentMode) -> None:
        super().__init__()
        self._deployment = deployment
        self._navigation = shell_navigation(deployment)
        self._commands = shell_commands(deployment)
        self._actions: dict[ShellCommandId, QAction] = {}
        self._workflow_availability = None
        self._command_routes = {
            ShellCommandId.NEW_PROJECT: ShellRoute.PROJECT,
            ShellCommandId.OPEN_PROJECT: ShellRoute.PROJECT,
            ShellCommandId.IMPORT: ShellRoute.IMPORT,
            ShellCommandId.PROCESS: ShellRoute.PROCESSING,
            ShellCommandId.PLANT_OVERVIEW: ShellRoute.PLANT_OVERVIEW,
            ShellCommandId.REVIEW: ShellRoute.REVIEW,
            ShellCommandId.REPORT: ShellRoute.REPORT,
            ShellCommandId.EXPORT: ShellRoute.EXPORT,
        }
        self._pages: dict[ShellRoute, QWidget] = {}

        self.setWindowTitle("MCM SolarCheck")
        self.setStyleSheet(APP_STYLE_SHEET)
        self._build_menu_bar()
        central = QWidget(self)
        central.setObjectName("application_workspace")
        central_layout = QHBoxLayout(central)
        self._workflow_navigation = WorkflowNavigation(
            self._navigation.workflow_routes, self.show_route, central
        )
        central_layout.addWidget(self._workflow_navigation)
        self._stack = QStackedWidget(central)
        central_layout.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        routes = list(self._navigation.workflow_routes)
        if self._navigation.initial_route is ShellRoute.LOGIN:
            routes.insert(0, ShellRoute.LOGIN)

        for route in routes:
            if route is self._navigation.initial_route and route in {
                ShellRoute.LOGIN,
                ShellRoute.PROJECT,
            }:
                page = make_entry_page(self._deployment)
            else:
                page = self._make_placeholder_page(route)
            self._pages[route] = page
            self._stack.addWidget(page)

        self.show_route(self._navigation.initial_route)


    def _build_menu_bar(self) -> None:
        menus = {
            "Project": self.menuBar().addMenu("Project"),
            "Processing": self.menuBar().addMenu("Processing"),
            "View": self.menuBar().addMenu("View"),
            "Review": self.menuBar().addMenu("Review"),
            "Report": self.menuBar().addMenu("Report"),
            "Export": self.menuBar().addMenu("Export"),
            "Help": self.menuBar().addMenu("Help"),
        }
        menu_for_command = {
            ShellCommandId.NEW_PROJECT: "Project",
            ShellCommandId.OPEN_PROJECT: "Project",
            ShellCommandId.IMPORT: "Project",
            ShellCommandId.PROCESS: "Processing",
            ShellCommandId.PLANT_OVERVIEW: "View",
            ShellCommandId.REVIEW: "Review",
            ShellCommandId.REPORT: "Report",
            ShellCommandId.EXPORT: "Export",
            ShellCommandId.USER_GUIDE: "Help",
        }
        for command in self._commands:
            action = QAction(command.label, self)
            action.setObjectName(f"{command.command_id.value}_action")
            menus[menu_for_command[command.command_id]].addAction(action)
            route = self._command_routes.get(command.command_id)
            if route is not None:
                action.triggered.connect(
                    lambda checked=False, target=route: self.show_route(target)
                )
            self._actions[command.command_id] = action

    def action(self, command_id: ShellCommandId) -> QAction:
        return self._actions[command_id]

    def apply_workflow_state(self, state) -> None:
        """Apply backend-derived action readiness without inventing GUI state."""
        from mcm_solarcheck.services.workflow import WorkflowAction, action_availability

        command_actions = {
            ShellCommandId.IMPORT: WorkflowAction.IMPORT,
            ShellCommandId.PROCESS: WorkflowAction.PROCESS,
            ShellCommandId.REVIEW: WorkflowAction.REVIEW,
            ShellCommandId.REPORT: WorkflowAction.PREPARE_REPORT,
            ShellCommandId.EXPORT: WorkflowAction.EXPORT,
        }
        for command_id, workflow_action in command_actions.items():
            availability = action_availability(state, workflow_action)
            action = self._actions[command_id]
            action.setEnabled(availability.allowed)
            action.setToolTip(
                "" if availability.allowed else "; ".join(availability.blockers)
            )
            route = self._command_routes[command_id]
            button = self._workflow_navigation.button(route)
            blocker_text = "; ".join(availability.blockers)
            button.setEnabled(True)
            button.setProperty("blocked", not availability.allowed)
            button.setToolTip("" if availability.allowed else blocker_text)
            button.setAccessibleDescription(
                "" if availability.allowed else f"Blockiert: {blocker_text}"
            )
        self._workflow_availability = state

    @property
    def current_route(self) -> ShellRoute:
        widget = self._stack.currentWidget()
        for route, page in self._pages.items():
            if page is widget:
                return route
        raise RuntimeError("current page is not registered")

    def show_route(self, route: ShellRoute) -> None:
        if self._workflow_availability is not None and route is not ShellRoute.LOGIN:
            from mcm_solarcheck.services.workflow import WorkflowAction, action_availability

            route_actions = {
                ShellRoute.IMPORT: WorkflowAction.IMPORT,
                ShellRoute.PROCESSING: WorkflowAction.PROCESS,
                ShellRoute.REVIEW: WorkflowAction.REVIEW,
                ShellRoute.REPORT: WorkflowAction.PREPARE_REPORT,
                ShellRoute.EXPORT: WorkflowAction.EXPORT,
            }
            workflow_action = route_actions.get(route)
            if workflow_action is not None:
                availability = action_availability(
                    self._workflow_availability, workflow_action
                )
                if not availability.allowed:
                    self._workflow_navigation.button(route).setFocus()
                    return
        try:
            page = self._pages[route]
        except KeyError as exc:
            raise ValueError(f"route is unavailable in this deployment: {route.value}") from exc
        self._stack.setCurrentWidget(page)
        if route is not ShellRoute.LOGIN:
            self._workflow_navigation.set_current_route(route)

    @staticmethod
    def _make_placeholder_page(route: ShellRoute) -> QWidget:
        page = QWidget()
        page.setObjectName(f"{route.value}_page")
        layout = QVBoxLayout(page)
        heading = QLabel(route.value.replace("_", " ").title(), page)
        heading.setObjectName("page_heading")
        layout.addWidget(heading)
        return page
