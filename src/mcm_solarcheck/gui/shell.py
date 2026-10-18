"""PySide6 application shell for SolarCheck.

Widgets stay deliberately thin: deployment and workflow decisions are supplied
by service-layer contracts rather than reimplemented in Qt.
"""

from __future__ import annotations

from typing import Protocol

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from mcm_solarcheck.gui.entry_page import make_entry_page
from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.gui.project_page import make_project_page
from mcm_solarcheck.gui.theme import APP_STYLE_SHEET
from mcm_solarcheck.gui.workflow_navigation import WorkflowNavigation
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_commands import ShellCommandId, shell_commands
from mcm_solarcheck.services.shell_navigation import ShellRoute, shell_navigation


class CustomerEntry(Protocol):
    def require_customer_entry(self, user_id: str | None = None) -> None:
        ...


class SolarCheckMainWindow(QMainWindow):
    def __init__(
        self,
        deployment: DeploymentMode,
        *,
        project_service=None,
        customer_entry: CustomerEntry | None = None,
        on_register=None,
        on_email_verification=None,
    ) -> None:
        super().__init__()
        self._deployment = deployment
        self._project_service = project_service
        self._customer_entry = customer_entry
        self._on_register = on_register
        self._on_email_verification = on_email_verification
        self._navigation = shell_navigation(deployment)
        self._commands = shell_commands(deployment)
        self._actions: dict[ShellCommandId, QAction] = {}
        self._workflow_availability = None
        self._current_project_id = None
        self._verified_user_id = None
        self._last_import_attempt = None
        self._geotiff_result = None
        self._orthophoto_comparison = None
        self._orthophoto_comparison_error = None
        self._rgb_preview_status = None
        self._rgb_preview_path = None
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
            if route is ShellRoute.LOGIN:
                page = make_entry_page(
                    self._deployment,
                    on_register=self._on_register,
                    on_email_verification=self._on_email_verification,
                    on_verified_entry=self._enter_verified_customer,
                )
            elif route is ShellRoute.PROJECT:
                projects = self._project_service.projects() if self._project_service is not None else ()
                page = make_project_page(
                    projects=projects,
                    on_create_project=(
                        self._create_project
                        if self._project_service is not None
                        else None
                    ),
                    on_open_project=(
                        self._open_project
                        if self._project_service is not None
                        else None
                    ),
                )
            elif route is ShellRoute.IMPORT:
                page = make_import_page(current_project_id=self._current_project_id)
            else:
                page = self._make_placeholder_page(route)
            self._pages[route] = page
            self._stack.addWidget(page)

        self.show_route(self._navigation.initial_route)


    def _enter_verified_customer(self, user_id: str) -> None:
        if self._customer_entry is None:
            raise RuntimeError("online customer entry is unavailable")
        self._customer_entry.require_customer_entry(user_id)
        self._verified_user_id = user_id
        self._stack.setCurrentWidget(self._pages[ShellRoute.PROJECT])
        self._workflow_navigation.set_current_route(ShellRoute.PROJECT)

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

    def _create_project(self, project_id: str, name: str, profile=None) -> None:
        """Persist a new project and its explicit master data before refreshing."""
        if self._project_service is None:
            return
        if profile is None:
            project = self._project_service.create_project(project_id, name)
        else:
            project = self._project_service.create_project_with_profile(
                project_id, name, profile
            )
        self._refresh_project_page()
        self._open_project(project.project_id)

    def _refresh_project_page(self) -> None:
        """Rebuild project presentation exclusively from persisted service records."""
        old_page = self._pages[ShellRoute.PROJECT]
        new_page = make_project_page(
            projects=self._project_service.projects(),
            on_create_project=self._create_project,
            on_open_project=self._open_project,
        )
        self._pages[ShellRoute.PROJECT] = new_page
        index = self._stack.indexOf(old_page)
        self._stack.insertWidget(index, new_page)
        if self._stack.currentWidget() is old_page:
            self._stack.setCurrentWidget(new_page)
        self._stack.removeWidget(old_page)
        old_page.deleteLater()

    def _open_project(self, project_id: str | None) -> None:
        """Open a persisted project through the application service boundary."""
        if self._project_service is None or project_id is None:
            return
        state = self._project_service.open_project(project_id)
        if project_id != self._current_project_id:
            self._last_import_attempt = None
            self._geotiff_result = None
            self._orthophoto_comparison = None
            self._orthophoto_comparison_error = None
            self._rgb_preview_status = None
            self._rgb_preview_path = None
        self._current_project_id = project_id
        self._refresh_import_page()
        self.apply_workflow_state(state)

    def _refresh_import_page(self) -> None:
        """Rebuild import presentation from the active persisted project context."""
        old_page = self._pages[ShellRoute.IMPORT]
        summary_provider = (
            getattr(self._project_service, "import_summary", None)
            if self._project_service is not None
            else None
        )
        import_summary = (
            summary_provider(self._current_project_id)
            if callable(summary_provider) and self._current_project_id is not None
            else None
        )
        verification_provider = (
            getattr(self._project_service, "import_verification", None)
            if self._project_service is not None
            else None
        )
        import_verification = (
            verification_provider(self._current_project_id)
            if callable(verification_provider) and self._current_project_id is not None
            else None
        )
        artifacts_provider = getattr(self._project_service, 'project_geotiff_inspections', None)
        geotiff_artifacts = (
            artifacts_provider(self._current_project_id)
            if callable(artifacts_provider) and self._current_project_id is not None
            else ()
        )
        new_page = make_import_page(
            current_project_id=self._current_project_id,
            on_import_images=(
                self._request_image_import
                if self._project_service is not None
                else None
            ),
            import_summary=import_summary,
            import_verification=import_verification,
            import_attempt=self._last_import_attempt,
            on_preview_rgb_files=self._preview_selected_rgb_files,
            on_preview_rgb_folder=self._preview_rgb_folder,
            rgb_preview_status=self._rgb_preview_status,
            rgb_preview_path=self._rgb_preview_path,
            on_inspect_geotiff=(self._inspect_project_geotiff if self._project_service is not None else None),
            geotiff_result=self._geotiff_result,
            geotiff_artifacts=geotiff_artifacts,
            on_compare_orthophotos=(self._compare_project_orthophotos if self._project_service is not None else None),
            orthophoto_comparison=self._orthophoto_comparison,
            orthophoto_comparison_error=self._orthophoto_comparison_error,
            on_generate_orthophotos=(self._generate_project_orthophotos if callable(getattr(self._project_service, 'generate_imported_project_orthophotos', None)) else None),
            on_register_geotiff=(self._register_project_geotiff if callable(getattr(self._project_service, 'register_project_geotiff', None)) else None),
        )
        self._pages[ShellRoute.IMPORT] = new_page
        index = self._stack.indexOf(old_page)
        self._stack.insertWidget(index, new_page)
        if self._stack.currentWidget() is old_page:
            self._stack.setCurrentWidget(new_page)
        self._stack.removeWidget(old_page)
        old_page.deleteLater()

    def _preview_rgb_folder(self, directory: str) -> None:
        """Run bounded automatic DJI folder preview; never silently omit frames."""
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog
        from mcm_solarcheck.services.flight_visual_folder import preview_rgb_folder
        from mcm_solarcheck.services.flight_inventory import scan_flight
        from mcm_solarcheck.services.flight_image_inspection import inspect_flight_images, save_flight_inspection

        if self._current_project_id is None:
            return
        try:
            captures, ignored = scan_flight(directory)
            rgb_count = sum(rgb is not None for _, rgb, _ in captures)
            thermal_count = sum(thermal is not None for _, _, thermal in captures)
            pairs = sum(rgb is not None and thermal is not None for _, rgb, thermal in captures)
            summary = f"Flug: {rgb_count} RGB, {thermal_count} Thermal, {pairs} Paare; {len(ignored)} weitere Einträge. "
            inspection = inspect_flight_images(directory)
            inspection_summary = (
                f"Bildprüfung: {inspection['readable']} lesbar, "
                f"{inspection['unreadable']} unlesbar, "
                f"{inspection['oversized']} zu groß, "
                f"{inspection['missing']} fehlend. "
            )
            if rgb_count not in (3, 4) or inspection["unreadable"] or inspection["oversized"] or inspection["missing"]:
                inspection_destination = QFileDialog.getSaveFileName(
                    self, "Vollständige Bildprüfung als JSON speichern", "",
                    "JSON-Datei (*.json)"
                )[0]
                if inspection_destination:
                    try:
                        save_flight_inspection(directory, inspection_destination)
                        inspection_summary += "Bildprüfung lokal als JSON gespeichert. "
                    except (ValueError, OSError) as exc:
                        inspection_summary += f"JSON-Speicherung fehlgeschlagen: {exc}. "
                self._rgb_preview_path = None
                self._rgb_preview_status = (
                    summary + inspection_summary +
                    "Alle erkannten Aufnahmen geprüft; vollständige Bildzusammensetzung "
                    "noch nicht verfügbar. Keine fehlerhaften Bilder stillschweigend übersprungen."
                )
                self._refresh_import_page()
                return
        except (ValueError, OSError) as exc:
            self._rgb_preview_path = None
            self._rgb_preview_status = f"Fluginventar fehlgeschlagen: {exc}"
            self._refresh_import_page()
            return
        destination = QFileDialog.getSaveFileName(
            self, "Automatische RGB-Vorschau speichern", "", "PNG-Bild (*.png)"
        )[0]
        if not destination:
            return
        png = Path(destination)
        self._rgb_preview_path = None
        try:
            result = preview_rgb_folder(directory, png, png.with_suffix(".json"))
            self._rgb_preview_path = png
            self._rgb_preview_status = (
                summary + inspection_summary + "DJI-RGB-Bilder automatisch erkannt und verarbeitet. "
                "Nicht metrische Vorschau; kein verifiziertes Orthofoto. "
                "Große Flüge werden noch nicht vollständig unterstützt."
            )
        except (ValueError, OSError) as exc:
            self._rgb_preview_status = f"Automatische RGB-Auswertung nicht möglich: {exc}"
        self._refresh_import_page()

    def _preview_selected_rgb_files(self, paths) -> None:
        """Run existing offline RGB pipeline on selected local files."""
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog
        from mcm_solarcheck.services.flight_visual_files import preview_rgb_files

        if self._current_project_id is None:
            return
        if len(paths) not in (3, 4):
            self._rgb_preview_path = None
            self._rgb_preview_status = "Bitte 3–4 RGB-Bilder auswählen."
            self._refresh_import_page()
            return
        destination = QFileDialog.getSaveFileName(
            self, "Nicht metrische RGB-Vorschau speichern", "",
            "PNG-Bild (*.png)"
        )[0]
        if not destination:
            return
        png = Path(destination)
        quality = png.with_suffix(".json")
        self._rgb_preview_path = None
        try:
            result = preview_rgb_files(paths, png, quality)
            self._rgb_preview_path = png
            overlap = result.overlap_quality
            overlap_text = (
                f"Visuelle Abweichung im Überlappungsbereich: "
                f"{overlap.mean_overlap_disagreement:.1f}/255. "
                if overlap is not None and overlap.mean_overlap_disagreement is not None
                else "Keine auswertbare Überlappung. "
            )
            self._rgb_preview_status = (
                "Nicht metrische RGB-Vorschau und Qualitäts-JSON lokal erstellt. "
                + overlap_text + "Kein verifiziertes Orthofoto."
            )
        except (ValueError, OSError) as exc:
            self._rgb_preview_status = f"RGB-Vorschau fehlgeschlagen: {exc}"
        self._refresh_import_page()

    def _inspect_project_geotiff(self, source_path: str) -> None:
        """Display unapproved local GIS metadata without changing project workflow."""
        if self._project_service is None or self._current_project_id is None:
            return
        try:
            reference = self._project_service.inspect_project_geotiff(
                self._current_project_id, source_path
            )
            self._geotiff_result = (
                f"GIS-Metadaten vorhanden (nicht fachlich verifiziert): "
                f"CRS {reference.crs}; {reference.width} × {reference.height} Pixel; "
                f"Affine Transformation {reference.transform}; NoData {reference.nodata}"
            )
        except (ValueError, OSError, KeyError) as error:
            self._geotiff_result = f"GeoTIFF-Prüfung fehlgeschlagen: {error}"
        self._refresh_import_page()

    def _register_project_geotiff(self, source_path: str) -> None:
        """Explicitly register local GIS provenance, without approving the orthophoto."""
        if self._project_service is None or self._current_project_id is None:
            return
        try:
            self._project_service.register_project_geotiff(
                self._current_project_id, source_path, source_kind="unknown"
            )
            self._geotiff_result = "GeoTIFF-Metadaten registriert (nicht fachlich verifiziert)."
        except (ValueError, OSError, KeyError) as error:
            self._geotiff_result = f"GeoTIFF-Registrierung fehlgeschlagen: {error}"
        self._refresh_import_page()

    def _generate_project_orthophotos(self, job_path: str) -> None:
        """Run only an explicit local surveyed job; display result without approval."""
        if self._project_service is None or self._current_project_id is None:
            return
        from mcm_solarcheck.services.orthophoto_survey_job import load_surveyed_orthophoto_job
        try:
            arguments = load_surveyed_orthophoto_job(job_path)
            pair = self._project_service.generate_imported_project_orthophotos(
                self._current_project_id, *arguments, planar_surface_verified=True,
            )
            self._geotiff_result = (
                f"Native Orthofotos erzeugt: RGB {pair.rgb_geotiff}; "
                f"Thermal {pair.thermal_geotiff} (keine Temperaturkalibrierung bestätigt)."
            )
            self._compare_project_orthophotos(str(pair.rgb_geotiff), str(pair.thermal_geotiff))
            return
        except (ValueError, TypeError, OSError, KeyError, RuntimeError) as error:
            self._geotiff_result = f"Orthofoto-Erzeugung fehlgeschlagen: {error}"
        self._refresh_import_page()

    def _compare_project_orthophotos(self, rgb_path: str, thermal_path: str) -> None:
        """Show GIS-aligned local raster previews; never alter project approval."""
        if self._project_service is None or self._current_project_id is None:
            return
        from mcm_solarcheck.services.orthophoto_layer_alignment import (
            aligned_preview_arrays, inspect_orthophoto_layer_pair,
        )
        try:
            pair = inspect_orthophoto_layer_pair(rgb_path, thermal_path)
            preview = aligned_preview_arrays(pair)
            import numpy as np
            if not np.isfinite(preview[1]).any():
                raise ValueError("RGB- und Thermal-Orthofotos haben keine gemeinsame Rasterabdeckung")
            self._orthophoto_comparison = preview
            self._orthophoto_comparison_error = None
        except (ValueError, OSError, KeyError, RuntimeError) as error:
            self._orthophoto_comparison = None
            self._orthophoto_comparison_error = f"Orthofoto-Vergleich fehlgeschlagen: {error}"
        self._refresh_import_page()

    def _request_image_import(self, source_directory: str) -> None:
        """Route a selected directory through the guarded application import boundary."""
        if self._project_service is None or self._current_project_id is None:
            return
        attempt, _result, state = self._project_service.import_project_images(
            self._current_project_id,
            source_directory,
        )
        self._last_import_attempt = attempt
        self._refresh_import_page()
        self.apply_workflow_state(state)

    @property
    def current_project_id(self) -> str | None:
        return self._current_project_id

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
        if (
            self._deployment is DeploymentMode.ONLINE
            and route is not ShellRoute.LOGIN
            and self._customer_entry is not None
        ):
            if self._verified_user_id is None:
                raise PermissionError("verified online customer identity is required")
            self._customer_entry.require_customer_entry(self._verified_user_id)

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
                    self._workflow_navigation.explain_blocker(route)
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
