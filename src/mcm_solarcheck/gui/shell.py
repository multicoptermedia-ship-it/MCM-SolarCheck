"""PySide6 application shell for SolarCheck.

Widgets stay deliberately thin: deployment and workflow decisions are supplied
by service-layer contracts rather than reimplemented in Qt.
"""

from __future__ import annotations

from typing import Protocol
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from mcm_solarcheck.gui.entry_page import make_entry_page
from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.gui.project_page import make_project_page
from mcm_solarcheck.gui.processing_page import make_processing_page
from mcm_solarcheck.gui.plant_overview_page import make_plant_overview_page
from mcm_solarcheck.gui.report_page import make_report_page
from mcm_solarcheck.gui.export_page import make_export_page
from mcm_solarcheck.gui.review_page import MAX_REVIEW_PAGE_FINDINGS, make_review_page
from mcm_solarcheck.gui.review_history_panel import HISTORY_PAGE_SIZE
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
        offline_admin_sessions=None,
        offline_report_training=None,
    ) -> None:
        super().__init__()
        self._deployment = deployment
        self._project_service = project_service
        self._customer_entry = customer_entry
        self._on_register = on_register
        self._on_email_verification = on_email_verification
        self._offline_admin_sessions = (
            offline_admin_sessions if deployment is DeploymentMode.OFFLINE_DESKTOP
            else None
        )
        self._offline_report_training = (
            offline_report_training if deployment is DeploymentMode.OFFLINE_DESKTOP
            else None
        )
        self._navigation = shell_navigation(deployment)
        self._commands = shell_commands(deployment)
        self._actions: dict[ShellCommandId, QAction] = {}
        self._workflow_availability = None
        self._current_project_id = None
        self._last_profile_status = None
        self._verified_user_id = None
        self._last_import_attempt = None
        self._geotiff_result = None
        self._orthophoto_comparison = None
        self._orthophoto_comparison_error = None
        self._integrity_close_pending = False
        self._integrity_project_id = None
        self._rgb_integrity_status = None
        self._preflight_thread = None
        self._preflight_project_id = None
        self._preflight_close_pending = False
        self._preflight_status = None
        self._import_thread = None
        self._import_project_id = None
        self._import_close_pending = False
        self._import_status = None
        self._import_performance_snapshot = None
        self._import_metrics_status = None
        self._benchmark_comparison = None
        self._benchmark_comparison_status = None
        self._rgb_preview_status = None
        self._rgb_preview_path = None
        self._last_review_status = None
        self._review_offset = 0
        self._review_history_offset = 0
        self._review_generation = 0
        self._draft_report = None
        self._draft_request = None
        self._report_end_seen = False
        self._last_report_status = None
        self._last_export_status = None
        self._plant_overview_offset = 0
        self._pair_control_status = None
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
            elif route is ShellRoute.PROCESSING:
                page = make_processing_page(current_project_id=self._current_project_id)
            elif route is ShellRoute.PLANT_OVERVIEW:
                page = make_plant_overview_page(current_project_id=self._current_project_id)
            elif route is ShellRoute.REVIEW:
                page = make_review_page(current_project_id=self._current_project_id)
            elif route is ShellRoute.REPORT:
                page = make_report_page(current_project_id=self._current_project_id)
            elif route is ShellRoute.EXPORT:
                page = make_export_page(current_project_id=self._current_project_id)
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
        if (
            self._deployment is DeploymentMode.OFFLINE_DESKTOP
            and self._offline_admin_sessions is not None
        ):
            admin_menu = self.menuBar().addMenu("Administration")
            admin_action = QAction("Vertrauliches Berichtsprotokoll …", self)
            admin_action.setObjectName("open_report_admin_audit")
            admin_action.triggered.connect(self._open_report_admin_audit)
            admin_menu.addAction(admin_action)
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

    def _open_report_admin_audit(self) -> None:
        """Open a credential-gated dialog, never a normal workflow route."""
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or self._offline_admin_sessions is None
            or self._current_project_id is None
        ):
            return
        from mcm_solarcheck.gui.offline_admin_audit_dialog import OfflineAdminAuditDialog
        project = self._current_project_id
        dialog = OfflineAdminAuditDialog(
            self._offline_admin_sessions, project,
            active_project=lambda: self._current_project_id,
            parent=self,
        )
        try:
            dialog.exec()
        finally:
            dialog.close()

    def _create_project(self, project_id: str, name: str, profile=None) -> None:
        """Persist a new project and its explicit master data before refreshing."""
        if self._project_service is None:
            return
        if not project_id and profile is not None:
            creator = getattr(
                self._project_service, "create_numbered_offline_project", None
            )
            if not callable(creator):
                raise ValueError("Automatic project numbering unavailable")
            project = creator(profile)
        elif profile is None:
            project = self._project_service.create_project(project_id, name)
        else:
            # Backward-compatible service API for existing integration clients.
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
            current_project_id=self._current_project_id,
            profile=(
                self._project_service.project_profile(self._current_project_id)
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._current_project_id is not None
                and callable(getattr(self._project_service, "project_profile", None))
                else None
            ),
            on_edit_profile=(
                (lambda expected, updated, source=self._current_project_id:
                 self._update_project_profile(source, expected, updated))
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._current_project_id is not None
                and callable(getattr(
                    self._project_service, "update_project_profile_if_unchanged", None
                ))
                else None
            ),
            last_profile_status=(
                self._last_profile_status
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP else None
            ),
        )
        self._pages[ShellRoute.PROJECT] = new_page
        index = self._stack.indexOf(old_page)
        self._stack.insertWidget(index, new_page)
        if self._stack.currentWidget() is old_page:
            self._stack.setCurrentWidget(new_page)
        self._stack.removeWidget(old_page)
        old_page.deleteLater()

    def _update_project_profile(
        self, source_project: str, expected, updated,
    ) -> None:
        """Only an explicit offline edit from the current project can persist."""
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._project_service is None
        ):
            return
        update = getattr(
            self._project_service, "update_project_profile_if_unchanged", None
        )
        if not callable(update):
            return
        try:
            changed = update(source_project, expected, updated)
        except (KeyError, ValueError, TypeError, OSError):
            self._clear_prepared_draft()
            self._last_profile_status = (
                "Stammdaten nicht gespeichert. Projekt und gespeicherte Daten "
                "bitte erneut öffnen und prüfen."
            )
        else:
            if changed:
                self._clear_prepared_draft()
            self._last_profile_status = (
                "Projektstammdaten gespeichert. Einen Berichtsentwurf "
                "bitte neu vorbereiten."
                if changed else "Keine Änderung der Projektstammdaten."
            )
        self._refresh_project_page()
        self._refresh_report_page()
        self._refresh_export_page()

    def _open_project(self, project_id: str | None) -> None:
        """Open a persisted project through the application service boundary."""
        if self._project_service is None or project_id is None:
            return
        state = self._project_service.open_project(project_id)
        if project_id != self._current_project_id:
            # A running integrity scan belongs to the previous project. Its
            # callbacks must never publish results into the newly opened one.
            active_worker = getattr(self, "_integrity_worker", None)
            if active_worker is not None:
                active_worker.request_cancel()
                self._rgb_integrity_status = "Vorherige RGB-Prüfung wird beendet …"
            else:
                self._rgb_integrity_status = None
            active_preflight = self._preflight_thread
            if active_preflight is not None:
                active_preflight.request_cancel()
                self._preflight_status = "Vorprüfung des vorherigen Projekts wird beendet …"
            else:
                self._preflight_status = None
            self._import_performance_snapshot = None
            self._import_metrics_status = None
            self._benchmark_comparison = None
            self._benchmark_comparison_status = None
            import_thread = self._import_thread
            if import_thread is not None:
                import_thread.request_cancel()
                self._import_status = "Import des vorherigen Projekts wird beendet …"
            else:
                self._import_status = None
            self._last_import_attempt = None
            self._last_profile_status = None
            self._last_review_status = None
            self._review_offset = 0
            self._review_history_offset = 0
            self._plant_overview_offset = 0
            self._pair_control_status = None
            self._clear_prepared_draft()
            self._geotiff_result = None
            self._orthophoto_comparison = None
            self._orthophoto_comparison_error = None
            self._rgb_preview_status = None
            self._rgb_preview_path = None
        self._current_project_id = project_id
        self._refresh_project_page()
        self._refresh_import_page()
        self._refresh_processing_page()
        self._refresh_plant_overview_page()
        self._refresh_review_page()
        self._refresh_report_page()
        self._refresh_export_page()
        self.apply_workflow_state(state)

    def _load_plant_overview_page(self, source_project: str, offset: int) -> None:
        """Handle Qt navigation without applying stale project callbacks."""
        if (self._deployment is not DeploymentMode.OFFLINE_DESKTOP
                or source_project != self._current_project_id
                or type(offset) is not int or offset < 0):
            return
        self._plant_overview_offset = offset
        self._refresh_plant_overview_page()

    def _refresh_plant_overview_page(self) -> None:
        """Rebuild a bounded read-only site inventory from authoritative SQLite."""
        old_page = self._pages[ShellRoute.PLANT_OVERVIEW]
        provider = getattr(self._project_service, "plant_overview", None)
        project_id = self._current_project_id
        enabled = (
            self._deployment is DeploymentMode.OFFLINE_DESKTOP
            and project_id is not None and callable(provider)
        )
        overview = (
            provider(project_id, offset=self._plant_overview_offset, limit=100)
            if enabled else None
        )
        new_page = make_plant_overview_page(
            current_project_id=project_id if self._deployment is DeploymentMode.OFFLINE_DESKTOP else None,
            overview=overview,
            on_refresh=(
                (lambda checked=False, source=project_id:
                    self._load_plant_overview_page(source, self._plant_overview_offset))
                if enabled else None
            ),
            on_page_requested=(
                (lambda offset, source=project_id:
                    self._load_plant_overview_page(source, offset))
                if enabled else None
            ),
        )
        self._pages[ShellRoute.PLANT_OVERVIEW] = new_page
        index = self._stack.indexOf(old_page)
        self._stack.insertWidget(index, new_page)
        if self._stack.currentWidget() is old_page:
            self._stack.setCurrentWidget(new_page)
        self._stack.removeWidget(old_page)
        old_page.deleteLater()

    def _clear_prepared_draft(self) -> None:
        """Discard stale report previews and their export authorization context."""
        self._draft_report = None
        self._draft_request = None
        self._report_end_seen = False
        self._last_report_status = None
        self._last_export_status = None

    def _refresh_report_page(self) -> None:
        """Render offline report readiness from the existing service and product gate."""
        from mcm_solarcheck.services.product_entitlements import (
            OFFLINE_DESKTOP, ProductOperation,
        )

        old_page = self._pages[ShellRoute.REPORT]
        service = self._project_service
        project_id = self._current_project_id
        offline = self._deployment is DeploymentMode.OFFLINE_DESKTOP
        enabled = (
            offline and project_id is not None and service is not None
            and callable(getattr(service, "output_availability", None))
            and callable(getattr(service, "project_profile", None))
            and callable(getattr(service, "prepare_report", None))
        )
        availability = (
            service.output_availability(
                project_id, OFFLINE_DESKTOP, ProductOperation.REPORT_DOWNLOAD,
            ) if enabled else None
        )
        profile = service.project_profile(project_id) if enabled else None
        progress_provider = getattr(service, "review_progress", None)
        progress = (
            progress_provider(project_id)
            if enabled and callable(progress_provider) else None
        )
        draft = (
            self._draft_report
            if enabled and self._draft_request is not None
            and self._draft_request[0] == project_id else None
        )
        on_prepare = (
            (lambda report_id, started, source=project_id:
             self._prepare_report_draft(source, report_id, started))
            if enabled else None
        )
        approval = None
        if draft is not None and callable(getattr(service, "report_release_decision", None)):
            try:
                approval = service.report_release_decision(
                    project_id, self._draft_request[1], self._draft_request[2],
                    expected_draft=draft,
                )
            except (ValueError, PermissionError, OSError, KeyError, TypeError):
                approval = None
        on_approve = (
            (lambda approver, ack, note, train_opt_in=False, rights_reference="",
             source=project_id:
             self._approve_offline_report(
                 source, approver, ack, note, train_opt_in, rights_reference,
             ))
            if enabled and draft is not None
            and callable(getattr(service, "approve_offline_report", None))
            else None
        )
        on_preview = (
            (lambda source=project_id: self._preview_offline_report(source))
            if enabled and draft is not None
            and callable(getattr(service, "render_offline_draft_preview", None))
            else None
        )
        training_request = None
        if approval is not None and self._offline_report_training is not None:
            training_request = self._offline_report_training.state(
                project_id, approval.approval_id,
            )
        on_revoke_training = (
            (lambda source=project_id, target=approval.approval_id:
             self._revoke_offline_report_training(source, target))
            if training_request is not None and training_request.status != "revoked"
            and approval is not None else None
        )
        on_refresh_training = (
            (lambda source=project_id: self._refresh_report_page()
             if self._current_project_id == source else None)
            if training_request is not None else None
        )
        page = make_report_page(
            current_project_id=project_id if offline else None,
            availability=availability,
            profile=profile,
            draft=draft,
            on_prepare=on_prepare,
            last_status=self._last_report_status if offline else None,
            progress=progress, approval=approval, on_approve=on_approve,
            on_preview=on_preview, training_request=training_request,
            on_revoke_training=on_revoke_training,
            on_refresh_training=on_refresh_training,
        )
        self._pages[ShellRoute.REPORT] = page
        index = self._stack.indexOf(old_page)
        self._stack.insertWidget(index, page)
        if self._stack.currentWidget() is old_page:
            self._stack.setCurrentWidget(page)
        self._stack.removeWidget(old_page)
        old_page.deleteLater()

    def _refresh_export_page(self) -> None:
        """Present only the active project's explicit unreleased draft."""
        from mcm_solarcheck.services.product_entitlements import (
            OFFLINE_DESKTOP, ProductOperation,
        )

        old_page = self._pages[ShellRoute.EXPORT]
        service = self._project_service
        project_id = self._current_project_id
        offline = self._deployment is DeploymentMode.OFFLINE_DESKTOP
        enabled = (
            offline and project_id is not None and service is not None
            and callable(getattr(service, "output_availability", None))
            and callable(getattr(service, "export_offline_draft", None))
        )
        availability = (
            service.output_availability(
                project_id, OFFLINE_DESKTOP, ProductOperation.EXPORT,
            ) if enabled else None
        )
        draft = (
            self._draft_report
            if enabled and self._draft_request is not None
            and self._draft_request[0] == project_id else None
        )
        on_export = (
            (lambda format_name, source=project_id:
             self._export_offline_draft(source, format_name))
            if enabled else None
        )
        approval = None
        if draft is not None and callable(getattr(service, "report_release_decision", None)):
            try:
                approval = service.report_release_decision(
                    project_id, self._draft_request[1], self._draft_request[2],
                    expected_draft=draft,
                )
            except (ValueError, PermissionError, OSError, KeyError, TypeError):
                approval = None
        on_export_released = (
            (lambda format_name, source=project_id:
             self._export_offline_released(source, format_name))
            if enabled and callable(getattr(service, "export_offline_released", None))
            else None
        )
        page = make_export_page(
            current_project_id=project_id if offline else None,
            availability=availability, draft=draft,
            on_export=on_export,
            last_status=self._last_export_status if offline else None,
            approval=approval, on_export_released=on_export_released,
        )
        self._pages[ShellRoute.EXPORT] = page
        index = self._stack.indexOf(old_page)
        self._stack.insertWidget(index, page)
        if self._stack.currentWidget() is old_page:
            self._stack.setCurrentWidget(page)
        self._stack.removeWidget(old_page)
        old_page.deleteLater()

    def _prepare_report_draft(
        self, source_project: str, report_id: str, started_at,
    ) -> None:
        """Build a non-released snapshot only from the selected offline project."""
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._project_service is None
        ):
            return
        try:
            report = self._project_service.prepare_report(
                source_project, report_id, started_at, release_status="draft",
            )
            if report.project_id != source_project or report.release_status != "draft":
                raise ValueError("unzulässiger Bericht oder Freigabestatus")
        except (ValueError, PermissionError, OSError, KeyError, TypeError) as exc:
            self._clear_prepared_draft()
            self._last_report_status = f"Entwurf nicht vorbereitet: {exc}"
        else:
            self._draft_report = report
            self._draft_request = (source_project, report_id, started_at)
            self._report_end_seen = False
            self._last_report_status = (
                f"Berichtsentwurf {report.report_id} vorbereitet (draft). "
                "Noch keine Datei erzeugt oder freigegeben."
            )
            self._last_export_status = None
        self._refresh_report_page()
        self._refresh_export_page()

    def _preview_offline_report(self, source_project: str) -> None:
        """Show the actual draft PDF, never claim that it was read."""
        from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._project_service is None or self._draft_request is None
            or self._draft_request[0] != source_project
            or self._draft_report is None
        ):
            return
        request = self._draft_request
        snapshot = self._draft_report
        try:
            content = self._project_service.render_offline_draft_preview(
                source_project, request[1], request[2],
                capabilities=OFFLINE_DESKTOP, expected_draft=snapshot,
            )
            from mcm_solarcheck.gui.report_pdf_preview import ReportPdfPreviewDialog
            dialog = ReportPdfPreviewDialog(content, parent=self)
            dialog.exec()
            reached_end = dialog.reached_end
            dialog.close()
            if (
                reached_end
                and self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._current_project_id == source_project
                and self._draft_request == request
                and self._draft_report is snapshot
                and self._project_service.prepare_report(
                    source_project, request[1], request[2], release_status="draft",
                ) == snapshot
            ):
                self._report_end_seen = True
        except (ValueError, PermissionError, OSError, KeyError, TypeError, ImportError):
            self._last_report_status = (
                "Berichtsvorschau nicht verfügbar. Die fachliche Freigabe bleibt "
                "eine separate, ausdrückliche Handlung."
            )
            self._refresh_report_page()

    def _approve_offline_report(
        self, source_project: str, reviewer: str, acknowledge_unclear: bool,
        followup_note: str, train_opt_in: bool = False,
        rights_reference: str = "",
    ) -> None:
        """Sign the report separately from optional, local training opt-in."""
        from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._draft_request is None or self._draft_request[0] != source_project
            or self._draft_report is None or self._project_service is None
        ):
            return
        _, report_id, started = self._draft_request
        try:
            decision = self._project_service.approve_offline_report(
                source_project, report_id, started, capabilities=OFFLINE_DESKTOP,
                approved_by=reviewer, acknowledge_unclear=acknowledge_unclear,
                followup_note=followup_note, expected_draft=self._draft_report,
                reached_preview_end=self._report_end_seen,
            )
        except (ValueError, PermissionError, KeyError, TypeError, OSError):
            self._last_report_status = (
                "Freigabe nicht dokumentiert. Aktuellen Projektstand, "
                "fachliche Entscheidungen und Nachprüfungsbedarf prüfen."
            )
        else:
            self._last_report_status = (
                f"Explizite menschliche Freigabe dokumentiert "
                f"(Audit {decision.approval_id}). Keine Normkonformitätszusage."
            )
            if train_opt_in is True:
                if self._offline_report_training is None:
                    self._last_report_status += (
                        " Trainingsfreigabe nicht gespeichert: lokale "
                        "Trainingsverwaltung nicht verfügbar."
                    )
                else:
                    try:
                        result = self._offline_report_training.request(
                            project_id=source_project,
                            report=self._draft_report,
                            approval=decision,
                            authorized_by=reviewer,
                            rights_reference=rights_reference,
                            affirmative_opt_in=True,
                        )
                    except (ValueError, PermissionError, OSError, TypeError, KeyError):
                        self._last_report_status += (
                            " Trainingsfreigabe nicht übernommen; "
                            "Nutzungsnachweis und Datenstand überprüfen."
                        )
                    else:
                        self._last_report_status += (
                            " Trainingsfreigabe gesondert gespeichert. "
                            + (
                                "Lokaler Trainingslauf angestoßen. "
                                "Fortschritt unter Trainingsstatus aktualisieren."
                                if result.status == "training_running"
                                else (
                                    f"{result.sample_count} geprüfte Bilder "
                                    "lokal zur Trainingsvorbereitung bereitgestellt. "
                                    "Noch kein Training gestartet."
                                    if result.status == "staged_waiting_for_trainer"
                                    else "Trainingsbestand noch nicht bereit. "
                                         "Noch kein Training gestartet."
                                )
                            )
                        )
        self._refresh_report_page()
        self._refresh_export_page()

    def _revoke_offline_report_training(
        self, source_project: str, approval_id: int,
    ) -> None:
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or self._offline_report_training is None
            or source_project != self._current_project_id
            or self._draft_request is None
            or self._draft_request[0] != source_project
        ):
            return
        try:
            self._offline_report_training.revoke(source_project, approval_id)
        except (OSError, ValueError, PermissionError, KeyError, TypeError):
            self._last_report_status = "Trainingswiderruf fehlgeschlagen. Administrator prüfen lassen."
        else:
            self._last_report_status = (
                "Trainingsfreigabe widerrufen; neue Trainingsläufe aus diesem "
                "lokalen Datensatz bleiben gesperrt. Bereits trainierte Modelle "
                "könnten dadurch nicht rückwirkend verändert werden."
            )
        self._refresh_report_page()

    def _export_offline_released(
        self, source_project: str, format_name: str,
    ) -> None:
        """Recheck the matching explicit approval after the modal save dialog."""
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog
        from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._draft_request is None or self._draft_request[0] != source_project
            or self._draft_report is None or self._project_service is None
            or format_name not in ("pdf", "odt", "docx")
        ):
            return
        prepared_request = self._draft_request
        prepared_snapshot = self._draft_report
        if self._project_service.report_release_decision(
            source_project, prepared_request[1], prepared_request[2],
            expected_draft=prepared_snapshot,
        ) is None:
            self._last_export_status = (
                "Freigabeexport gesperrt: keine zum Bericht passende, aktuelle Freigabe."
            )
            self._refresh_export_page()
            return
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Fachlich freigegebenen Bericht lokal speichern",
            f"SolarCheck-freigegeben.{format_name}",
            f"Freigegebener Bericht (*.{format_name})",
        )
        if not chosen:
            return
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._draft_request != prepared_request
            or self._draft_report is not prepared_snapshot
        ):
            return
        try:
            destination = Path(chosen)
            if not destination.is_absolute() or destination.suffix.lower() != f".{format_name}":
                raise ValueError("invalid local release destination")
            self._project_service.export_offline_released(
                source_project, prepared_request[1], prepared_request[2],
                destination, capabilities=OFFLINE_DESKTOP,
                expected_draft=prepared_snapshot,
            )
        except (ValueError, PermissionError, OSError, KeyError, TypeError):
            self._last_export_status = (
                "Freigegebener Bericht nicht gespeichert. Freigabe, Projektstand "
                "und lokalen Zielpfad erneut prüfen; vorhandene Dateien bleiben unverändert."
            )
        else:
            self._last_export_status = (
                "Fachlich freigegebener Bericht lokal gespeichert (released). "
                "Keine automatische Normkonformität und keine externe Veröffentlichung."
            )
        self._refresh_report_page()
        self._refresh_export_page()

    def _export_offline_draft(self, source_project: str, format_name: str) -> None:
        """Rebuild on export and never publish a stale or released report."""
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog
        from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP

        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._draft_request is None
            or self._draft_request[0] != source_project
            or self._draft_report is None
            or format_name not in ("pdf", "odt", "docx")
        ):
            return
        # Remember the exact preview that was authorized before opening the
        # modal save dialog (which may run a nested Qt event loop).
        prepared_request = self._draft_request
        prepared_snapshot = self._draft_report
        _, report_id, started_at = prepared_request
        try:
            current = self._project_service.prepare_report(
                source_project, report_id, started_at, release_status="draft",
            )
            if current != self._draft_report:
                self._clear_prepared_draft()
                raise ValueError(
                    "Gespeicherte Befunde/Stammdaten haben sich geändert; "
                    "den Entwurf bitte neu vorbereiten"
                )
        except (ValueError, PermissionError, OSError, KeyError, TypeError):
            self._clear_prepared_draft()
            self._last_export_status = (
                "Export gesperrt: Berichtsdaten oder Freigaben bitte erneut "
                "prüfen und einen neuen Entwurf vorbereiten."
            )
            self._refresh_report_page()
            self._refresh_export_page()
            return

        selected, _filter = QFileDialog.getSaveFileName(
            self,
            "Lokalen Berichtsentwurf speichern (keine Freigabe)",
            f"SolarCheck-Berichtsentwurf.{format_name}",
            f"Berichtsentwurf (*.{format_name})",
        )
        if not selected:
            return
        # Qt's modal dialog may process a project change or another draft
        # preparation. Never export using an obsolete page callback.
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._draft_request != prepared_request
            or self._draft_report is not prepared_snapshot
        ):
            return
        # A reviewer or another local writer may have changed SQLite while
        # the file chooser was open. The original preview must still match.
        try:
            latest = self._project_service.prepare_report(
                source_project, report_id, started_at, release_status="draft",
            )
            if latest != prepared_snapshot:
                raise ValueError("stale report snapshot")
        except (ValueError, PermissionError, OSError, KeyError, TypeError):
            self._clear_prepared_draft()
            self._last_export_status = (
                "Export gesperrt: gespeicherte Befunde oder Stammdaten haben "
                "sich geändert. Bitte einen neuen Entwurf vorbereiten."
            )
            self._refresh_report_page()
            self._refresh_export_page()
            return
        try:
            destination = Path(selected)
            if not destination.is_absolute():
                raise ValueError("absolute local destination required")
            if destination.suffix.lower() != f".{format_name}":
                raise ValueError("Dateiendung stimmt nicht mit dem Exportformat überein")
            saved = self._project_service.export_offline_draft(
                source_project, report_id, started_at, destination,
                capabilities=OFFLINE_DESKTOP,
            )
        except (ValueError, PermissionError, OSError, KeyError, TypeError):
            self._last_export_status = (
                "Entwurf nicht gespeichert. Bitte ein neues Ziel im vorhandenen, "
                "beschreibbaren lokalen Ordner mit passender Dateiendung wählen. "
                "Bestehende Dateien bleiben unverändert."
            )
        else:
            self._last_export_status = (
                "Berichtsentwurf lokal gespeichert. Freigabestatus: draft; "
                "keine Veröffentlichung. Speicherort wurde nur im "
                "Dateidialog gewählt."
            )
        self._refresh_export_page()

    def _reload_review_page(self) -> None:
        """Reload pending findings and backend-derived workflow availability."""
        if self._current_project_id is None:
            return
        state_provider = getattr(self._project_service, "state", None)
        state = (
            state_provider(self._current_project_id)
            if callable(state_provider) else None
        )
        self._refresh_review_page()
        if state is not None:
            self.apply_workflow_state(state)

    def _load_review_page(
        self, source_project: str, offset: int,
        expected_generation: int | None = None,
    ) -> None:
        """Reject stale, online, negative or unaligned Qt navigation requests."""
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or type(offset) is not int or offset < 0
            or offset % MAX_REVIEW_PAGE_FINDINGS != 0
            or (expected_generation is not None
                and expected_generation != self._review_generation)
        ):
            return
        self._review_offset = offset
        self._refresh_review_page()

    def _load_review_history_page(
        self, source_project: str, offset: int,
        expected_generation: int | None = None,
    ) -> None:
        """Block older Qt history controls and cross-project navigation."""
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or type(offset) is not int or offset < 0
            or offset % HISTORY_PAGE_SIZE != 0
            or (expected_generation is not None
                and expected_generation != self._review_generation)
        ):
            return
        self._review_history_offset = offset
        self._refresh_review_page()

    def _preview_review_images(
        self, source_project: str, finding_id: str, local_folder: str,
        expected_generation: int | None = None,
    ):
        """Read hashed thumbnails only for the active offline review page.

        Errors never echo selected or persisted customer paths into Qt.
        """
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or self._project_service is None
            or source_project != self._current_project_id
            or (expected_generation is not None
                and expected_generation != self._review_generation)
        ):
            return None
        provider = getattr(
            self._project_service, "preview_review_image_evidence", None,
        )
        if not callable(provider):
            return None
        try:
            # A stale widget from another review page cannot read another
            # finding. The IDs and page boundary originate from SQLite.
            active = self._project_service.pending_review_findings(
                source_project, limit=MAX_REVIEW_PAGE_FINDINGS,
                offset=self._review_offset,
            )
            if finding_id not in (item.finding_id for item in active):
                return None
            images = provider(source_project, finding_id, local_folder)
        except (KeyError, PermissionError, ValueError, TypeError, OSError):
            from mcm_solarcheck.services.review_image_preview import ReviewImageEvidence
            images = ReviewImageEvidence(None, None, "unavailable", "unavailable")
        if (
            source_project != self._current_project_id
            or (expected_generation is not None
                and expected_generation != self._review_generation)
        ):
            return None
        return images

    def _refresh_review_page(self) -> None:
        """Build one project-specific page of persisted, unreviewed findings."""
        old_page = self._pages[ShellRoute.REVIEW]
        overview_provider = getattr(self._project_service, "processing_overview", None)
        queue_provider = getattr(self._project_service, "pending_review_findings", None)
        history_provider = getattr(self._project_service, "expert_review_history", None)
        progress_provider = getattr(self._project_service, "review_progress", None)
        action_provider = getattr(self._project_service, "review_pending_finding", None)
        preview_provider = getattr(
            self._project_service, "preview_review_image_evidence", None,
        )
        # Online access requires a separate ownership-scoped adapter; do not
        # expose this local expert-review action through an online shell.
        offline = self._deployment is DeploymentMode.OFFLINE_DESKTOP
        project_id = self._current_project_id
        enabled = (
            offline and project_id is not None
            and callable(overview_provider) and callable(queue_provider)
        )
        overview = overview_provider(project_id) if enabled else None
        progress = (
            progress_provider(project_id)
            if enabled and callable(progress_provider) else None
        )
        # Reviews shrink the queue. Do not leave the reviewer on an empty page.
        total = overview.summary.unreviewed_findings if overview is not None else 0
        if total == 0:
            self._review_offset = 0
        elif self._review_offset >= total:
            self._review_offset = (
                (total - 1) // MAX_REVIEW_PAGE_FINDINGS
            ) * MAX_REVIEW_PAGE_FINDINGS
        pending = (
            queue_provider(
                project_id, limit=MAX_REVIEW_PAGE_FINDINGS,
                offset=self._review_offset,
            )
            if enabled else ()
        )
        history = None
        if enabled and callable(history_provider):
            history = history_provider(
                project_id, limit=HISTORY_PAGE_SIZE,
                offset=self._review_history_offset,
            )
            if history.total == 0:
                self._review_history_offset = 0
            elif self._review_history_offset >= history.total:
                self._review_history_offset = (
                    (history.total - 1) // HISTORY_PAGE_SIZE
                ) * HISTORY_PAGE_SIZE
            if history.offset != self._review_history_offset:
                history = history_provider(
                    project_id, limit=HISTORY_PAGE_SIZE,
                    offset=self._review_history_offset,
                )
        # Each redraw revokes all callbacks belonging to the old Qt page,
        # even if a new page has the same project and finding identifiers.
        self._review_generation += 1
        generation = self._review_generation
        on_review = (
            (lambda finding_id, status, reviewer, note,
             source_project=project_id, generation=generation:
             self._review_pending_finding(
                 source_project, finding_id, status, reviewer, note,
                 expected_generation=generation,
             ))
            if enabled and callable(action_provider) else None
        )
        # Numbered offline projects use a human-readable label. For legacy
        # projects retain the old opaque identifier without exposing a name.
        project_record = next((
            p for p in self._project_service.projects()
            if p.project_id == project_id
        ), None) if enabled else None
        project_label = (
            f"{project_record.display_number} · {project_record.name}"
            if project_record is not None
            and getattr(project_record, "display_number", None)
            else None
        )
        new_page = make_review_page(
            current_project_id=project_id if offline else None,
            project_label=project_label,
            overview=overview, pending=pending,
            on_review=on_review,
            on_refresh=self._reload_review_page if enabled else None,
            on_page_requested=(
                (lambda offset, source=project_id, generation=generation:
                 self._load_review_page(source, offset, generation))
                if enabled else None
            ),
            offset=self._review_offset if enabled else 0,
            on_preview_images=(
                (lambda finding_id, folder, source=project_id,
                 generation=generation:
                 self._preview_review_images(
                     source, finding_id, folder, generation,
                 ))
                if enabled and callable(preview_provider) else None
            ),
            last_review_status=self._last_review_status if offline else None,
            history=history,
            progress=progress,
            on_history_page_requested=(
                (lambda offset, source=project_id, generation=generation:
                 self._load_review_history_page(source, offset, generation))
                if enabled and callable(history_provider) else None
            ),
        )
        self._pages[ShellRoute.REVIEW] = new_page
        index = self._stack.indexOf(old_page)
        self._stack.insertWidget(index, new_page)
        if self._stack.currentWidget() is old_page:
            self._stack.setCurrentWidget(new_page)
        self._stack.removeWidget(old_page)
        old_page.deleteLater()

    def _review_pending_finding(
        self, source_project: str, finding_id: str, status, reviewer: str,
        note: str | None,
        expected_generation: int | None = None,
    ) -> None:
        """Persist only an active project/page's deliberately chosen decision."""
        if (self._deployment is not DeploymentMode.OFFLINE_DESKTOP
                or source_project != self._current_project_id
                or self._project_service is None
                or (expected_generation is not None
                    and expected_generation != self._review_generation)):
            return
        review_action = getattr(self._project_service, "review_pending_finding", None)
        if not callable(review_action):
            return
        try:
            if expected_generation is not None:
                current = self._project_service.pending_review_findings(
                    source_project, limit=MAX_REVIEW_PAGE_FINDINGS,
                    offset=self._review_offset,
                )
                if finding_id not in (item.finding_id for item in current):
                    return
            _finding, audit, state = review_action(
                source_project, finding_id, status=status,
                reviewer=reviewer, note=note,
            )
        except (KeyError, ValueError, TypeError):
            self._last_review_status = (
                "Entscheidung nicht gespeichert. Bitte den aktuellen "
                "Projektstand und den Befund erneut laden und prüfen."
            )
            self._refresh_review_page()
            return
        self._last_review_status = (
            f"Fachliche Entscheidung für {audit.finding_id} protokolliert "
            f"({audit.status.value}). Keine automatische Berichtsfreigabe."
        )
        self._clear_prepared_draft()
        self._refresh_review_page()
        self._refresh_processing_page()
        self._refresh_plant_overview_page()
        self._refresh_report_page()
        self._refresh_export_page()
        self.apply_workflow_state(state)

    def _reload_processing_page(self) -> None:
        """Refresh read-only processing evidence and backend-derived navigation."""
        if self._current_project_id is None:
            return
        state_provider = getattr(self._project_service, "state", None)
        state = (
            state_provider(self._current_project_id)
            if callable(state_provider) else None
        )
        self._refresh_processing_page()
        if state is not None:
            self.apply_workflow_state(state)

    def _check_pair_control_points(self, control_file: str) -> None:
        """Only inspect a local expert file for the active offline project.

        Result stays ephemeral: no calibration, report, approval or stored
        pixel transform is changed. Never display private filenames/coordinates.
        """
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or self._current_project_id is None
            or not callable(getattr(
                self._project_service, "check_offline_pair_control_points", None
            ))
        ):
            return
        try:
            result = self._project_service.check_offline_pair_control_points(
                self._current_project_id, control_file,
            )
        except (ValueError, TypeError, OSError, KeyError, PermissionError):
            self._pair_control_status = (
                "Kontrollpunktprüfung abgelehnt: Datei, Projektzuordnung oder "
                "Eingabewerte ungültig. Keine Daten verändert."
            )
        else:
            if result.status == "holdout_passed_unapproved":
                self._pair_control_status = (
                    f"Kontrollpunkt-Holdout bestanden: {result.fit_inliers} "
                    f"Anpassungs-Inlier, {result.holdout_points} Kontrollpunkte, "
                    f"RMS {result.holdout_rms_px:.2f} Pixel. "
                    "Nur technischer, nicht freigegebener Kandidat; "
                    "keine automatische Überlagerung."
                )
            else:
                self._pair_control_status = (
                    "Kontrollpunkt-Holdout nicht bestanden "
                    f"({result.reason}). Keine Überlagerung oder Freigabe."
                )
        self._refresh_processing_page()

    def _refresh_processing_page(self) -> None:
        """Render the selected project's persisted evidence through its service."""
        old_page = self._pages[ShellRoute.PROCESSING]
        overview_provider = getattr(self._project_service, "processing_overview", None)
        overview = (
            overview_provider(self._current_project_id)
            if callable(overview_provider) and self._current_project_id is not None
            else None
        )
        project_record = next((
            p for p in self._project_service.projects()
            if p.project_id == self._current_project_id
        ), None) if self._project_service is not None else None
        project_label = (
            f"{project_record.display_number} · {project_record.name}"
            if project_record is not None
            and getattr(project_record, "display_number", None)
            else None
        )
        run_provider = getattr(
            self._project_service, "latest_offline_processing_run", None,
        )
        processing_run = (
            run_provider(self._current_project_id)
            if callable(run_provider) and self._current_project_id is not None
            and self._deployment is DeploymentMode.OFFLINE_DESKTOP
            else None
        )
        new_page = make_processing_page(
            current_project_id=self._current_project_id,
            project_label=project_label,
            processing_run=processing_run,
            overview=overview,
            registration_check_status=self._pair_control_status,
            on_check_registration=(
                self._check_pair_control_points
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and callable(getattr(
                    self._project_service, "check_offline_pair_control_points", None
                ))
                else None
            ),
            on_refresh=(
                self._reload_processing_page
                if callable(overview_provider) else None
            ),
        )
        self._pages[ShellRoute.PROCESSING] = new_page
        index = self._stack.indexOf(old_page)
        self._stack.insertWidget(index, new_page)
        if self._stack.currentWidget() is old_page:
            self._stack.setCurrentWidget(new_page)
        self._stack.removeWidget(old_page)
        old_page.deleteLater()

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
        project_record = next((
            p for p in self._project_service.projects()
            if p.project_id == self._current_project_id
        ), None) if self._project_service is not None else None
        # Legacy projects without a SC display number retain the previous
        # internal-ID context. Do not accidentally show customer data just
        # because an older project record has no user-facing number.
        project_label = (
            f"{project_record.display_number} · {project_record.name}"
            if project_record is not None
            and getattr(project_record, "display_number", None)
            else None
        )
        new_page = make_import_page(
            current_project_id=self._current_project_id,
            project_label=project_label,
            on_import_flight_folder=(
                self._request_flight_folder_import
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._project_service is not None
                and self._current_project_id is not None
                and self._import_thread is None
                and not self._import_close_pending else None
            ),
            on_import_additional_original_files=(
                self._request_additional_files_import
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._project_service is not None
                and self._current_project_id is not None
                and self._import_thread is None
                and not self._import_close_pending else None
            ),
            on_import_original_files=(
                self._request_original_files_import
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._project_service is not None
                and self._import_thread is None
                and not self._import_close_pending
                else None
            ),
            on_import_original_zips=(
                self._request_original_zip_import
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._project_service is not None
                and self._import_thread is None
                and not self._import_close_pending
                else None
            ),
            on_reconcile_pairs=(
                self._reconcile_stored_pairs
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._project_service is not None
                and self._import_thread is None
                and callable(getattr(self._project_service, "reconcile_imported_pairs", None))
                else None
            ),
            on_import_images=(
                self._request_image_import
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._project_service is not None
                and self._import_thread is None
                and not self._import_close_pending
                else None
            ),
            on_cancel_image_import=(
                self._cancel_image_import
                if self._import_thread is not None else None
            ),
            image_import_status=self._import_status,
            import_metrics_text=(
                self._import_metrics_text()
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP else None
            ),
            on_save_import_metrics=(
                (lambda destination, source=self._current_project_id:
                    self._save_import_metrics(source, destination))
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._current_project_id is not None
                and self._import_performance_snapshot is not None
                and self._import_thread is None
                and not self._import_close_pending else None
            ),
            on_compare_benchmark_reports=(
                (lambda paths, source=self._current_project_id:
                    self._compare_benchmark_reports(source, paths))
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._current_project_id is not None
                and self._import_thread is None
                and not self._import_close_pending else None
            ),
            benchmark_comparison_text=(
                self._benchmark_comparison_text()
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP else None
            ),
            on_save_benchmark_comparison=(
                (lambda destination, source=self._current_project_id:
                    self._save_benchmark_comparison(source, destination))
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._current_project_id is not None
                and self._benchmark_comparison is not None
                and self._import_thread is None else None
            ),
            import_summary=import_summary,
            import_verification=import_verification,
            pair_audit=(
                self._project_service.pair_evidence_overview(self._current_project_id)
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._current_project_id is not None
                and callable(getattr(self._project_service, "pair_evidence_overview", None))
                else None
            ),
            import_attempt=self._last_import_attempt,
            on_preview_rgb_files=self._preview_selected_rgb_files,
            on_preview_rgb_folder=self._preview_rgb_folder,
            on_start_flight_preflight=(
                self._start_flight_preflight
                if self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and self._preflight_thread is None
                and not self._preflight_close_pending else None
            ),
            on_cancel_flight_preflight=(
                self._cancel_flight_preflight
                if self._preflight_thread is not None else None
            ),
            flight_preflight_status=self._preflight_status,
            on_inspect_rgb_integrity=(
                self._inspect_rgb_integrity
                if getattr(self, "_integrity_thread", None) is None
                and not self._integrity_close_pending
                else None
            ),
            rgb_integrity_status=self._rgb_integrity_status,
            on_cancel_rgb_integrity=self._cancel_rgb_integrity if getattr(self, '_integrity_thread', None) is not None else None,
            on_run_rgb_links=self._run_full_flight_rgb_links,
            on_export_rgb_segments=self._export_full_flight_rgb_segments,
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

    def _start_flight_preflight(self, source_folder: str) -> None:
        """Start one read-only DJI directory scan outside the GUI thread."""
        from mcm_solarcheck.gui.flight_preflight_worker import FlightPreflightThread

        if (self._deployment is not DeploymentMode.OFFLINE_DESKTOP
                or self._current_project_id is None
                or self._preflight_thread is not None
                or self._preflight_close_pending
                or self._integrity_close_pending):
            return
        thread = FlightPreflightThread(source_folder, self)
        self._preflight_thread = thread
        self._preflight_project_id = self._current_project_id
        self._preflight_status = "DJI-Ordner-Vorprüfung läuft (nur Dateinamen/Größen) …"
        self._refresh_import_page()
        thread.progress.connect(
            self._preflight_progress, Qt.ConnectionType.QueuedConnection,
        )
        thread.result_ready.connect(
            self._preflight_finished, Qt.ConnectionType.QueuedConnection,
        )
        thread.failed.connect(
            self._preflight_failed, Qt.ConnectionType.QueuedConnection,
        )
        thread.cancelled.connect(
            self._preflight_cancelled, Qt.ConnectionType.QueuedConnection,
        )
        thread.finished.connect(
            self._preflight_thread_stopped, Qt.ConnectionType.QueuedConnection,
        )
        thread.start()

    def _preflight_result_is_current(self) -> bool:
        return (
            self._preflight_project_id is not None
            and self._preflight_project_id == self._current_project_id
            and not self._preflight_close_pending
        )

    @Slot(int)
    def _preflight_progress(self, entries: int) -> None:
        if not self._preflight_result_is_current():
            return
        self._preflight_status = (
            f"DJI-Ordner-Vorprüfung läuft: {entries} Einträge erfasst "
            "(Dateimetadaten, keine Bilddekodierung)."
        )
        self._refresh_import_page()

    @Slot(object)
    def _preflight_finished(self, result) -> None:
        if not self._preflight_result_is_current():
            return
        from mcm_solarcheck.gui.flight_preflight_worker import format_flight_preflight

        self._preflight_status = format_flight_preflight(result)
        self._refresh_import_page()

    @Slot(str)
    def _preflight_failed(self, message: str) -> None:
        if not self._preflight_result_is_current():
            return
        self._preflight_status = f"DJI-Ordner-Vorprüfung fehlgeschlagen: {message}"
        self._refresh_import_page()

    @Slot()
    def _preflight_cancelled(self) -> None:
        if not self._preflight_result_is_current():
            return
        self._preflight_status = (
            "DJI-Ordner-Vorprüfung abgebrochen. Originaldateien unverändert."
        )
        self._refresh_import_page()

    @Slot()
    def _preflight_thread_stopped(self) -> None:
        # The native thread must finish before we release its Python wrapper.
        QTimer.singleShot(0, self._preflight_cleanup)

    @Slot()
    def _preflight_cleanup(self) -> None:
        thread = self._preflight_thread
        if thread is None:
            return
        thread.wait()
        self._preflight_thread = None
        thread.deleteLater()
        if self._current_project_id != self._preflight_project_id:
            self._preflight_status = None
        self._preflight_project_id = None
        if self._preflight_close_pending:
            self._preflight_close_pending = False
            self.close()
        else:
            self._refresh_import_page()

    def _cancel_flight_preflight(self) -> None:
        thread = self._preflight_thread
        if thread is not None:
            thread.request_cancel()

    def _inspect_rgb_integrity(self, source_folder: str, output_folder: str) -> None:
        """Start one read-only scan; Qt delivers status back to the GUI thread."""
        from mcm_solarcheck.gui.flight_rgb_integrity_worker import FlightRgbIntegrityThread

        if (self._current_project_id is None
                or getattr(self, "_integrity_thread", None) is not None
                or self._integrity_close_pending):
            return
        thread = FlightRgbIntegrityThread(source_folder, output_folder, self)
        self._integrity_thread = thread
        self._integrity_worker = thread
        self._integrity_project_id = self._current_project_id
        self._rgb_integrity_status = "RGB-Integritätsprüfung läuft …"
        self._refresh_import_page()

        # Signals are queued to GUI-owned slots. The background QThread
        # runs the shared service directly and owns no moved QObject worker.
        thread.progress.connect(self._integrity_progress, Qt.ConnectionType.QueuedConnection)
        thread.result_ready.connect(self._integrity_finished, Qt.ConnectionType.QueuedConnection)
        thread.failed.connect(self._integrity_failed, Qt.ConnectionType.QueuedConnection)
        thread.cancelled.connect(self._integrity_cancelled, Qt.ConnectionType.QueuedConnection)
        thread.finished.connect(self._integrity_thread_stopped, Qt.ConnectionType.QueuedConnection)
        thread.start()

    def _integrity_result_is_current(self) -> bool:
        return (self._integrity_project_id is not None
                and self._current_project_id == self._integrity_project_id
                and not self._integrity_close_pending)

    @Slot(int, int, str)
    def _integrity_progress(self, done: int, total: int, status: str) -> None:
        if not self._integrity_result_is_current():
            return
        self._rgb_integrity_status = (
            f"RGB-Integritätsprüfung: {done}/{total} geprüft ({status})."
        )
        self._refresh_import_page()

    @Slot(object)
    def _integrity_finished(self, result) -> None:
        if not self._integrity_result_is_current():
            return
        from mcm_solarcheck.gui.flight_rgb_integrity_status import format_rgb_integrity_summary
        self._rgb_integrity_status = format_rgb_integrity_summary(result)
        self._refresh_import_page()

    @Slot(str)
    def _integrity_failed(self, message: str) -> None:
        if not self._integrity_result_is_current():
            return
        self._rgb_integrity_status = f"RGB-Integritätsprüfung fehlgeschlagen: {message}"
        self._refresh_import_page()

    @Slot()
    def _integrity_cancelled(self) -> None:
        if not self._integrity_result_is_current():
            return
        self._rgb_integrity_status = "RGB-Integritätsprüfung abgebrochen; keine Dateien verändert."
        self._refresh_import_page()

    @Slot()
    def _integrity_thread_stopped(self) -> None:
        # Keep both Python wrappers alive until Qt has returned from the
        # finished signal and its deferred QObject deletions have been queued.
        QTimer.singleShot(0, self._integrity_cleanup)

    @Slot()
    def _integrity_cleanup(self) -> None:
        thread = self._integrity_thread
        if thread is None:
            return
        # QThread.finished may precede native thread-local destructors.
        # Synchronize before releasing the object or rebuilding the Qt page.
        thread.wait()
        self._integrity_thread = None
        self._integrity_worker = None
        thread.deleteLater()
        if self._current_project_id != self._integrity_project_id:
            self._rgb_integrity_status = None
        self._integrity_project_id = None
        if self._integrity_close_pending:
            self._integrity_close_pending = False
            self.close()
        else:
            self._refresh_import_page()

    def closeEvent(self, event):
        """Keep all owned QThreads alive until their native work has stopped."""
        integrity_busy = getattr(self, "_integrity_thread", None) is not None
        preflight_busy = self._preflight_thread is not None
        import_busy = self._import_thread is not None
        if integrity_busy or preflight_busy or import_busy:
            if integrity_busy:
                self._integrity_close_pending = True
                self._cancel_rgb_integrity()
            if preflight_busy:
                self._preflight_close_pending = True
                self._cancel_flight_preflight()
            if import_busy:
                self._import_close_pending = True
                self._cancel_image_import()
            event.ignore()
            return
        super().closeEvent(event)

    def _cancel_rgb_integrity(self):
        worker = getattr(self, "_integrity_worker", None)
        if worker is not None:
            worker.request_cancel()

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

    def _run_full_flight_rgb_links(self, directory: str) -> None:
        """Run the independent complete-flight RGB link check from one folder."""
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QFileDialog, QProgressDialog
        from mcm_solarcheck.gui.flight_rgb_worker import FlightRgbWorker

        if self._current_project_id is None:
            return
        destination = QFileDialog.getSaveFileName(
            self, "RGB-Registrierungsergebnisse als JSON speichern", "",
            "JSON-Datei (*.json)"
        )[0]
        if not destination:
            return
        if getattr(self, "_rgb_link_thread", None) is not None:
            return
        thread = QThread(self)
        worker = FlightRgbWorker(directory, destination)
        worker.moveToThread(thread)
        progress = QProgressDialog("RGB-Bildverbindungen werden geprüft ...", "Abbrechen", 0, 100, self)
        progress.setMinimumDuration(0)
        self._rgb_link_thread = thread
        self._rgb_link_worker = worker
        self._rgb_link_progress = progress
        progress.canceled.connect(worker.request_cancel)
        thread.started.connect(worker.run)

        def on_progress(done, total, status):
            progress.setValue(round(100 * done / max(1, total)))
            progress.setLabelText(f"RGB-Verbindungen: {done}/{total}; zuletzt {status}")

        def on_finished(result):
            self._rgb_preview_status = (
                f"RGB-Prüfung abgeschlossen: {result['capture_count']} Aufnahmen, "
                f"{result['registered']} Verbindungen erfolgreich, "
                f"{result['failed']} fehlgeschlagen. Einzelstatus: {destination}. "
                "Nicht metrisch; kein Orthofoto. Thermal noch nicht registriert."
            )
            self._rgb_preview_path = None
            self._refresh_import_page()

        def on_failed(reason):
            self._rgb_preview_status = f"Vollständige RGB-Prüfung fehlgeschlagen: {reason}"
            self._refresh_import_page()

        def on_cancelled():
            self._rgb_preview_status = "RGB-Prüfung abgebrochen; keine Ergebnisdatei erstellt."
            self._refresh_import_page()

        def on_thread_finished():
            progress.close()
            self._rgb_link_thread = None
            self._rgb_link_worker = None
            self._rgb_link_progress = None
            thread.deleteLater()

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.failed.connect(on_failed)
        worker.cancelled.connect(on_cancelled)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(on_thread_finished)
        thread.start()

    def _export_full_flight_rgb_segments(self, directory: str, registration_path: str) -> None:
        """Export local previews asynchronously without changing project approvals."""
        from pathlib import Path
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QFileDialog, QProgressDialog
        from mcm_solarcheck.gui.flight_rgb_segments_worker import FlightRgbSegmentsWorker

        if self._current_project_id is None:
            return
        if getattr(self, "_rgb_segments_thread", None) is not None:
            return
        destination = QFileDialog.getExistingDirectory(
            self, "Leeren Ausgabeordner für RGB-Segmente auswählen"
        )
        if not destination:
            return
        target = Path(destination)
        if not target.is_dir() or target.is_symlink() or any(target.iterdir()):
            self._rgb_preview_status = "RGB-Export benötigt einen vorhandenen leeren regulären Ausgabeordner."
            self._refresh_import_page()
            return
        thread = QThread(self)
        worker = FlightRgbSegmentsWorker(directory, registration_path, destination)
        worker.moveToThread(thread)
        progress = QProgressDialog("RGB-Segmente werden exportiert ...", "Abbrechen", 0, 100, self)
        progress.setMinimumDuration(0)
        self._rgb_segments_thread = thread
        self._rgb_segments_worker = worker
        self._rgb_segments_progress = progress
        progress.canceled.connect(worker.request_cancel)
        thread.started.connect(worker.run)

        def on_progress(done, total, status):
            progress.setValue(round(100 * done / max(1, total)))
            progress.setLabelText(f"RGB-Segmente: {done}/{total}; zuletzt {status}")

        def on_finished(result):
            self._rgb_preview_path = None
            from mcm_solarcheck.gui.flight_rgb_segments_status import format_rgb_segments_result
            self._rgb_preview_status = format_rgb_segments_result(
                result, target / "segments_summary.json"
            )
            self._refresh_import_page()

        def on_failed(reason):
            self._rgb_preview_status = f"RGB-Segmentexport fehlgeschlagen: {reason}"
            self._refresh_import_page()

        def on_thread_finished():
            progress.close()
            self._rgb_segments_thread = None
            self._rgb_segments_worker = None
            self._rgb_segments_progress = None
            thread.deleteLater()

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.failed.connect(on_failed)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(on_thread_finished)
        thread.start()

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

    def _start_background_image_import(self, source_directory: str, *, original_zips=None,
                                       original_files=None, include_unpaired_thermal=False,
                                       append_original_files=False) -> None:
        """Run guarded DJI import off-thread, with no Qt objects in its worker."""
        from mcm_solarcheck.gui.flight_import_worker import FlightImportThread

        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or self._current_project_id is None
            or self._import_thread is not None
            or self._import_close_pending
        ):
            return
        worker = FlightImportThread(
            self._project_service, self._current_project_id, source_directory, self,
            original_zips=original_zips,
            original_files=original_files,
            include_unpaired_thermal=include_unpaired_thermal,
            append_original_files=append_original_files,
        )
        self._import_thread = worker
        self._import_project_id = self._current_project_id
        self._last_import_attempt = None
        self._import_performance_snapshot = None
        self._import_metrics_status = None
        self._benchmark_comparison = None
        self._benchmark_comparison_status = None
        self._import_status = "DJI-Bildimport läuft im Hintergrund …"
        worker.progress.connect(self._import_progress, Qt.ConnectionType.QueuedConnection)
        worker.metrics_ready.connect(
            self._import_metrics_ready, Qt.ConnectionType.QueuedConnection,
        )
        worker.result_ready.connect(self._import_finished, Qt.ConnectionType.QueuedConnection)
        worker.failed.connect(self._import_failed, Qt.ConnectionType.QueuedConnection)
        worker.cancelled.connect(self._import_cancelled, Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(self._import_thread_stopped, Qt.ConnectionType.QueuedConnection)
        self._refresh_import_page()
        worker.start()

    def _import_result_is_current(self) -> bool:
        return (
            self._import_project_id is not None
            and self._import_project_id == self._current_project_id
            and not self._import_close_pending
        )

    @Slot(str, int)
    def _import_progress(self, phase: str, count: int) -> None:
        if not self._import_result_is_current():
            return
        self._import_status = f"DJI-Bildimport: {phase} ({count} Prüfpunkte)."
        self._refresh_import_page()

    def _import_metrics_text(self) -> str | None:
        from mcm_solarcheck.services.offline_import_metrics import (
            format_import_performance,
        )

        if self._import_performance_snapshot is None:
            return self._import_metrics_status
        formatted = format_import_performance(self._import_performance_snapshot)
        return (
            f"{formatted} {self._import_metrics_status}"
            if self._import_metrics_status else formatted
        )

    @Slot(object)
    def _import_metrics_ready(self, snapshot) -> None:
        """Only the original project's completed worker can publish measurements."""
        if not self._import_result_is_current():
            return
        self._import_performance_snapshot = snapshot
        self._import_metrics_status = None
        self._refresh_import_page()

    def _save_import_metrics(self, source_project: str, destination: str) -> None:
        """Save anonymous diagnostics only by explicit offline user action."""
        from mcm_solarcheck.services.offline_import_metrics import (
            save_anonymous_import_report,
        )

        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project != self._current_project_id
            or self._import_performance_snapshot is None
            or self._import_thread is not None
            or self._import_close_pending
        ):
            return
        try:
            save_anonymous_import_report(
                self._import_performance_snapshot, destination,
            )
        except (FileExistsError, OSError, TypeError, ValueError):
            self._import_metrics_status = (
                "Messbericht nicht gespeichert. Bitte eine neue JSON-Datei "
                "in einem vorhandenen, beschreibbaren lokalen Ordner "
                "ohne Verknüpfungen wählen."
            )
        else:
            self._import_metrics_status = (
                "Anonymer Import-Messbericht lokal als JSON gespeichert. "
                "Keine Bildpfade oder Projektkennungen enthalten."
            )
        self._refresh_import_page()

    def _benchmark_comparison_text(self) -> str | None:
        """Show only aggregate measurements, never user-selected file paths."""
        comparison = self._benchmark_comparison
        if comparison is None:
            return self._benchmark_comparison_status

        seconds = comparison.elapsed_seconds
        summary = (
            f"Anonymer Import-Benchmark-Vergleich: {comparison.runs} Läufe; "
            f"je {comparison.rgb_frames} RGB, "
            f"{comparison.thermal_frames} Thermal und "
            f"{comparison.image_pairs} Paare gespeichert. "
            f"Gesamtdauer min/median/max: "
            f"{seconds['min']:.2f}/{seconds['median']:.2f}/"
            f"{seconds['max']:.2f} s."
        )
        def stage(label, values):
            if values is None:
                return f" {label}: nicht durchgängig verfügbar."
            return (
                f" {label} min/median/max: "
                f"{values['min']:.2f}/{values['median']:.2f}/"
                f"{values['max']:.2f} s."
            )
        summary += stage("Einlesen/Zuordnen", comparison.read_and_pair_seconds)
        summary += stage("SQLite", comparison.sqlite_commit_seconds)
        rss = comparison.process_peak_rss_bytes
        if rss is None:
            summary += " Prozess-RSS: nicht durchgängig verfügbar."
        else:
            mib = tuple(rss[key] / (1024 * 1024) for key in ("min", "median", "max"))
            summary += (
                f" Prozess-RSS min/median/max: "
                f"{mib[0]:.1f}/{mib[1]:.1f}/{mib[2]:.1f} MiB."
            )
        summary += (
            " RSS gilt für die gesamte Prozesslaufzeit; keine isolierte "
            "Importspitze oder garantierte RAM-Obergrenze. Gleiche Bildzahlen "
            "beweisen weder denselben Flug noch identische Hardware; keine "
            "Windows-/DJI-Fachabnahme."
        )
        if self._benchmark_comparison_status is not None:
            summary += " " + self._benchmark_comparison_status
        return summary

    def _compare_benchmark_reports(
        self, source_project: str, report_paths,
    ) -> None:
        """Read only explicitly selected files through the shared service."""
        from mcm_solarcheck.services.offline_benchmark_comparison import (
            compare_offline_benchmark_reports,
        )
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project is None
            or source_project != self._current_project_id
            or self._import_thread is not None
            or self._import_close_pending
        ):
            return
        # Fail closed: never re-export a previous success after an invalid set.
        self._benchmark_comparison = None
        try:
            result = compare_offline_benchmark_reports(report_paths)
        except (OSError, ValueError, TypeError):
            self._benchmark_comparison_status = (
                "Vergleich nicht möglich: 3–30 erfolgreiche, gültige lokale "
                "Benchmark-Berichte mit gleichen Bildzahlen auswählen."
            )
        else:
            self._benchmark_comparison = result
            self._benchmark_comparison_status = None
        self._refresh_import_page()

    def _save_benchmark_comparison(
        self, source_project: str, destination: str,
    ) -> None:
        """Write an anonymous result only following the separate save click."""
        from mcm_solarcheck.services.offline_import_metrics import (
            save_anonymous_import_report,
        )
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or source_project is None
            or source_project != self._current_project_id
            or self._benchmark_comparison is None
            or self._import_thread is not None
            or self._import_close_pending
        ):
            return
        try:
            save_anonymous_import_report(self._benchmark_comparison, destination)
        except (OSError, ValueError, TypeError):
            self._benchmark_comparison_status = (
                "Anonymer Vergleich nicht gespeichert: "
                "Ziel und vorhandene Dateien prüfen."
            )
        else:
            self._benchmark_comparison_status = (
                "Anonymer Vergleich lokal als JSON gespeichert; "
                "keine Quelldateinamen oder Projektkennungen im Bericht."
            )
        self._refresh_import_page()

    @Slot(object)
    def _import_finished(self, outcome) -> None:
        if not self._import_result_is_current():
            return
        attempt, _result, state = outcome
        self._last_import_attempt = attempt
        if attempt.succeeded:
            self._import_status = (
                "DJI-Import atomar gespeichert; "
                "keine automatische Fachprüfung oder Berichtsfreigabe."
            )
            self._last_review_status = None
            self._plant_overview_offset = 0
            self._clear_prepared_draft()
        else:
            self._import_status = f"DJI-Import fehlgeschlagen: {attempt.error}"
        self._refresh_import_page()
        self._refresh_processing_page()
        self._refresh_plant_overview_page()
        self._refresh_review_page()
        self._refresh_report_page()
        self._refresh_export_page()
        self.apply_workflow_state(state)

    @Slot(str)
    def _import_failed(self, message: str) -> None:
        if not self._import_result_is_current():
            return
        self._import_status = f"DJI-Import fehlgeschlagen: {message}"
        self._refresh_import_page()

    @Slot()
    def _import_cancelled(self) -> None:
        if not self._import_result_is_current():
            return
        self._import_status = (
            "DJI-Import abgebrochen, bevor die SQLite-Transaktion "
            "vollständig übernommen wurde."
        )
        self._refresh_import_page()

    @Slot()
    def _import_thread_stopped(self) -> None:
        QTimer.singleShot(0, self._import_cleanup)

    @Slot()
    def _import_cleanup(self) -> None:
        worker = self._import_thread
        if worker is None:
            return
        worker.wait()
        self._import_thread = None
        worker.deleteLater()
        if self._current_project_id != self._import_project_id:
            self._import_status = None
        self._import_project_id = None
        if self._import_close_pending:
            self._import_close_pending = False
            self.close()
        else:
            self._refresh_import_page()

    def _cancel_image_import(self) -> None:
        worker = self._import_thread
        if worker is not None:
            worker.request_cancel()

    def _reconcile_stored_pairs(self) -> None:
        """Apply only the operator-requested metadata association for this project."""
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or self._project_service is None
            or self._current_project_id is None
            or self._import_thread is not None
            or self._import_close_pending
        ):
            return
        project = self._current_project_id
        try:
            created = self._project_service.reconcile_imported_pairs(project)
        except (ValueError, RuntimeError, PermissionError, KeyError) as exc:
            self._import_status = f"Technische Zuordnung nicht möglich: {exc}"
        else:
            self._import_status = (
                f"{created} zusätzliche Bildpaare technisch zugeordnet. "
                "Keine geometrische Registrierung oder Fachfreigabe."
            )
            if created:
                self._clear_prepared_draft()
        self._refresh_import_page()
        self._refresh_processing_page()
        self._refresh_plant_overview_page()
        self._refresh_review_page()
        self._refresh_report_page()

    def _request_flight_folder_import(self, source_folder: str) -> None:
        """Stage loose JPG originals from one DJI flight folder, with preview."""
        if (self._deployment is not DeploymentMode.OFFLINE_DESKTOP
                or self._project_service is None or self._current_project_id is None
                or self._import_thread is not None or self._import_close_pending):
            return
        try:
            folder = Path(source_folder)
            if not folder.is_dir() or folder.is_symlink():
                raise ValueError("Kein gültiger lokaler DJI-Ordner")
            files = sorted((
                item for item in folder.iterdir()
                if item.is_file() and item.suffix.lower() == ".jpg"
            ), key=lambda item: item.name)
            if any(item.is_symlink() and item.suffix.lower() == ".jpg"
                   for item in folder.iterdir()):
                raise ValueError("Verknüpfte JPG-Dateien werden nicht automatisch eingelesen")
            if not files:
                raise ValueError("Im ausgewählten Ordner wurden keine JPG-Dateien gefunden")
            thermal = sum(p.name.upper().endswith("_T.JPG") for p in files)
            rgb = sum(p.name.upper().endswith("_V.JPG") for p in files)
            if thermal + rgb != len(files):
                raise ValueError(
                    "Der Ordner enthält JPG-Dateien ohne DJI-Thermal-/RGB-Kennung"
                )
        except (OSError, ValueError) as exc:
            self._import_status = f"Flugordner nicht übernommen: {exc}"
            self._refresh_import_page()
            return
        answer = QMessageBox.question(
            self, "DJI-Flugordner importieren",
            f"Gefunden: {thermal} Thermalbilder und {rgb} RGB-Bilder "
            f"({len(files)} JPG-Dateien).\n"
            "Nur die oberste Ordnerebene wird berücksichtigt.\n"
            "Originale bleiben unverändert; SolarCheck legt lokale Kopien an.\n"
            "Jetzt importieren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer is QMessageBox.StandardButton.Yes:
            self._request_original_files_import(tuple(str(p) for p in files))

    def _request_additional_files_import(self, original_files: tuple[str, ...]) -> None:
        """Explicit additive path; normal first import keeps its empty-project gate."""
        if (self._deployment is not DeploymentMode.OFFLINE_DESKTOP
                or self._project_service is None or self._current_project_id is None
                or self._import_thread is not None or self._import_close_pending
                or not original_files):
            return
        self._start_background_image_import(
            "", original_files=tuple(original_files), append_original_files=True,
        )

    def _request_original_files_import(self, original_files: tuple[str, ...]) -> None:
        """Primary operator path: selected unpacked DJI images, no ZIP required."""
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or self._project_service is None
            or self._current_project_id is None
            or self._import_thread is not None
            or self._import_close_pending
            or not original_files
        ):
            return
        self._start_background_image_import("", original_files=tuple(original_files))

    def _request_original_zip_import(
        self, thermal_zip: str, rgb_zip: str, include_unpaired_thermal: bool,
    ) -> None:
        """Only an explicit operator choice may open and stage private ZIPs."""
        if (
            self._deployment is not DeploymentMode.OFFLINE_DESKTOP
            or self._project_service is None
            or self._current_project_id is None
            or self._import_thread is not None
            or self._import_close_pending
        ):
            return
        self._start_background_image_import(
            "", original_zips=(thermal_zip, rgb_zip),
            include_unpaired_thermal=include_unpaired_thermal,
        )

    def _request_image_import(self, source_directory: str) -> None:
        """Route a selected directory through the guarded application import boundary."""
        if (self._deployment is not DeploymentMode.OFFLINE_DESKTOP
                or self._project_service is None or self._current_project_id is None
                or self._import_thread is not None or self._import_close_pending):
            return
        if (self._deployment is DeploymentMode.OFFLINE_DESKTOP
                and callable(getattr(self._project_service, "import_project_images_cancellable", None))):
            self._start_background_image_import(source_directory)
            return
        attempt, _result, state = self._project_service.import_project_images(
            self._current_project_id,
            source_directory,
        )
        self._last_import_attempt = attempt
        self._import_performance_snapshot = None
        self._import_metrics_status = None
        self._benchmark_comparison = None
        self._benchmark_comparison_status = None
        self._last_review_status = None
        self._plant_overview_offset = 0
        self._clear_prepared_draft()
        self._refresh_import_page()
        self._refresh_processing_page()
        self._refresh_plant_overview_page()
        self._refresh_review_page()
        self._refresh_report_page()
        self._refresh_export_page()
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
            self._workflow_navigation.set_availability(route, availability.allowed)
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
