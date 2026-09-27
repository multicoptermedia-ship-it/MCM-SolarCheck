import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QDialogButtonBox, QListWidget, QApplication, QLabel, QPushButton, QStackedWidget, QWidget

from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.gui.project_page import NewProjectDialog, make_project_page
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.gui.theme import APP_STYLE_SHEET, ANTHRACITE, WORK_SURFACE, ACCENT_GREEN
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.services.workflow import ProjectWorkflowState, StageReadiness, WorkflowAction, WorkflowAttempt, WorkflowStage
from mcm_solarcheck.storage.queries import ProjectRecord


@pytest.fixture(scope="module")
def app() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


def test_online_shell_starts_at_login(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)

    assert window.current_route is ShellRoute.LOGIN


def test_offline_shell_starts_at_project_without_login_route(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)

    assert window.current_route is ShellRoute.PROJECT
    with pytest.raises(ValueError):
        window.show_route(ShellRoute.LOGIN)


@pytest.mark.parametrize(
    "command_id, expected_route",
    [
        (ShellCommandId.IMPORT, ShellRoute.IMPORT),
        (ShellCommandId.PROCESS, ShellRoute.PROCESSING),
        (ShellCommandId.PLANT_OVERVIEW, ShellRoute.PLANT_OVERVIEW),
        (ShellCommandId.REVIEW, ShellRoute.REVIEW),
        (ShellCommandId.REPORT, ShellRoute.REPORT),
        (ShellCommandId.EXPORT, ShellRoute.EXPORT),
    ],
)
def test_menu_actions_use_shared_navigation(
    app: QApplication, command_id: ShellCommandId, expected_route: ShellRoute
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)

    window.action(command_id).trigger()

    assert window.current_route is expected_route


def test_user_guide_command_is_exposed_in_help(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)

    assert window.action(ShellCommandId.USER_GUIDE).objectName() == "user_guide_action"


def test_online_entry_exposes_login_guide_and_provider_attribution(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)
    page = window.findChild(QStackedWidget).currentWidget()

    assert page.objectName() == "login_page"
    assert page.findChild(type(page), "project_page") is None
    assert page.findChild(QLabel, "login_hint") is not None
    guide = page.findChild(QLabel, "user_guide_hint")
    provider = page.findChild(QLabel, "provider_attribution")

    assert guide is not None
    assert "Hilfe" in guide.text()
    assert provider is not None
    assert provider.text() == "powered by MCM-Dronetech GmbH"


def test_offline_entry_has_no_online_login_or_provider_elements(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    page = window.findChild(QStackedWidget).currentWidget()
    assert page.objectName() == "project_page"
    assert page.findChild(QLabel, "login_hint") is None
    assert page.findChild(QLabel, "provider_attribution") is None
    assert page.findChild(QLabel, "user_guide_hint") is None


def test_shell_uses_central_theme_tokens(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)

    assert window.styleSheet() == APP_STYLE_SHEET
    assert ANTHRACITE in APP_STYLE_SHEET
    assert WORK_SURFACE in APP_STYLE_SHEET
    assert ACCENT_GREEN.startswith("#")


def test_workflow_navigation_uses_shared_route_order(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    navigation = window.findChild(QWidget, "workflow_navigation")
    assert navigation is not None

    expected = [
        ("project_navigation", "Projekt"),
        ("import_navigation", "Import"),
        ("processing_navigation", "Verarbeitung"),
        ("plant_overview_navigation", "Anlagenübersicht"),
        ("review_navigation", "Review"),
        ("report_navigation", "Bericht"),
        ("export_navigation", "Export"),
    ]
    buttons = navigation.findChildren(QPushButton)
    assert [(button.objectName(), button.text()) for button in buttons] == expected


def test_workflow_navigation_routes_through_shell(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    button = window.findChild(QPushButton, "review_navigation")

    assert button is not None
    button.click()

    assert window.current_route is ShellRoute.REVIEW


def test_current_workflow_location_has_non_color_accessible_state(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    review = window.findChild(QPushButton, "review_navigation")
    project = window.findChild(QPushButton, "project_navigation")

    assert review is not None
    assert project is not None
    review.click()

    assert review.property("current") is True
    assert review.accessibleName() == "Review, aktueller Bereich"
    assert project.property("current") is False
    assert project.accessibleName() == "Projekt"


def test_menu_availability_follows_backend_workflow_state(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    state = ProjectWorkflowState(
        (
            StageReadiness(WorkflowStage.PROJECT, True),
            StageReadiness(WorkflowStage.IMPORT, False, ("no imported image frames",)),
            StageReadiness(
                WorkflowStage.PROCESSING,
                False,
                ("import required before processing",),
            ),
            StageReadiness(
                WorkflowStage.REVIEW,
                False,
                ("no processed modules or findings",),
            ),
            StageReadiness(
                WorkflowStage.REPORT,
                False,
                ("unreviewed findings remain",),
            ),
            StageReadiness(
                WorkflowStage.EXPORT,
                False,
                ("unreviewed findings remain",),
            ),
        )
    )

    window.apply_workflow_state(state)

    assert window.action(ShellCommandId.IMPORT).isEnabled()
    assert not window.action(ShellCommandId.PROCESS).isEnabled()
    assert (
        window.action(ShellCommandId.PROCESS).toolTip()
        == "no imported image frames"
    )
    assert not window.action(ShellCommandId.REVIEW).isEnabled()
    assert not window.action(ShellCommandId.REPORT).isEnabled()
    assert not window.action(ShellCommandId.EXPORT).isEnabled()


def test_ready_backend_workflow_enables_guarded_menu_actions(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    state = ProjectWorkflowState(
        tuple(StageReadiness(stage, True) for stage in WorkflowStage)
    )

    window.apply_workflow_state(state)

    for command_id in (
        ShellCommandId.IMPORT,
        ShellCommandId.PROCESS,
        ShellCommandId.REVIEW,
        ShellCommandId.REPORT,
        ShellCommandId.EXPORT,
    ):
        assert window.action(command_id).isEnabled()
        assert window.action(command_id).isEnabled()


def test_workflow_navigation_uses_same_backend_blockers_as_menu(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    state = ProjectWorkflowState(
        (
            StageReadiness(WorkflowStage.PROJECT, True),
            StageReadiness(WorkflowStage.IMPORT, False, ("no imported image frames",)),
            StageReadiness(
                WorkflowStage.PROCESSING,
                False,
                ("import required before processing",),
            ),
            StageReadiness(
                WorkflowStage.REVIEW,
                False,
                ("no processed modules or findings",),
            ),
            StageReadiness(
                WorkflowStage.REPORT,
                False,
                ("unreviewed findings remain",),
            ),
            StageReadiness(
                WorkflowStage.EXPORT,
                False,
                ("unreviewed findings remain",),
            ),
        )
    )

    window.apply_workflow_state(state)

    process_button = window.findChild(QPushButton, "processing_navigation")
    assert process_button is not None
    assert process_button.isEnabled()
    assert process_button.property("blocked") is True
    assert process_button.toolTip() == "no imported image frames"
    assert process_button.accessibleDescription() == (
        "Blockiert: no imported image frames"
    )
    assert (
        process_button.toolTip()
        == window.action(ShellCommandId.PROCESS).toolTip()
    )

    import_button = window.findChild(QPushButton, "import_navigation")
    assert import_button is not None
    assert import_button.isEnabled()
    assert import_button.property("blocked") is False


def test_blocked_navigation_explains_reason_without_route_change(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    state = ProjectWorkflowState(
        (
            StageReadiness(WorkflowStage.PROJECT, True),
            StageReadiness(WorkflowStage.IMPORT, False, ("no imported image frames",)),
            StageReadiness(
                WorkflowStage.PROCESSING,
                False,
                ("import required before processing",),
            ),
            StageReadiness(
                WorkflowStage.REVIEW,
                False,
                ("no processed modules or findings",),
            ),
            StageReadiness(WorkflowStage.REPORT, False, ("review required",)),
            StageReadiness(WorkflowStage.EXPORT, False, ("review required",)),
        )
    )
    window.apply_workflow_state(state)
    assert window.current_route is ShellRoute.PROJECT

    process_button = window.findChild(QPushButton, "processing_navigation")
    explanation = window.findChild(QLabel, "workflow_blocker_explanation")
    assert process_button is not None
    assert explanation is not None

    process_button.click()

    assert window.current_route is ShellRoute.PROJECT
    assert explanation.isVisible() is False or explanation.text() == (
        "Verarbeitung ist blockiert: no imported image frames"
    )
    assert explanation.text() == (
        "Verarbeitung ist blockiert: no imported image frames"
    )


def test_successful_navigation_clears_previous_blocker_feedback(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    state = ProjectWorkflowState(
        (
            StageReadiness(WorkflowStage.PROJECT, True),
            StageReadiness(WorkflowStage.IMPORT, False, ("no imported image frames",)),
            StageReadiness(WorkflowStage.PROCESSING, False, ("import required",)),
            StageReadiness(WorkflowStage.REVIEW, False, ("processing required",)),
            StageReadiness(WorkflowStage.REPORT, False, ("review required",)),
            StageReadiness(WorkflowStage.EXPORT, False, ("review required",)),
        )
    )
    window.apply_workflow_state(state)
    explanation = window.findChild(QLabel, "workflow_blocker_explanation")
    process_button = window.findChild(QPushButton, "processing_navigation")
    import_button = window.findChild(QPushButton, "import_navigation")
    assert explanation is not None
    assert process_button is not None
    assert import_button is not None

    process_button.click()
    assert explanation.text() == "Verarbeitung ist blockiert: no imported image frames"

    import_button.click()
    assert window.current_route is ShellRoute.IMPORT
    assert explanation.text() == ""


def test_blocked_navigation_keeps_textual_and_accessible_feedback(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    state = ProjectWorkflowState(
        (
            StageReadiness(WorkflowStage.PROJECT, True),
            StageReadiness(WorkflowStage.IMPORT, False, ("no imported image frames",)),
            StageReadiness(WorkflowStage.PROCESSING, False, ("import required",)),
            StageReadiness(WorkflowStage.REVIEW, False, ("processing required",)),
            StageReadiness(WorkflowStage.REPORT, False, ("review required",)),
            StageReadiness(WorkflowStage.EXPORT, False, ("review required",)),
        )
    )
    window.apply_workflow_state(state)

    button = window.findChild(QPushButton, "processing_navigation")
    explanation = window.findChild(QLabel, "workflow_blocker_explanation")
    assert button is not None
    assert explanation is not None
    assert button.property("blocked") is True
    assert button.accessibleDescription() == "Blockiert: no imported image frames"

    button.click()

    assert "blockiert" in explanation.text().lower()
    assert "no imported image frames" in explanation.text()


def test_project_workspace_replaces_project_placeholder(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)

    assert window.current_route is ShellRoute.PROJECT
    page = window.findChild(QWidget, "project_page")
    create = window.findChild(QPushButton, "create_project_button")
    empty = window.findChild(QLabel, "project_empty_state")
    assert page is not None
    assert create is not None
    assert create.text() == "Neues Projekt erstellen"
    assert empty is not None
    assert empty.text() == "Keine gespeicherten Projekte vorhanden."


def test_online_login_keeps_project_workspace_behind_entry_boundary(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.ONLINE)

    assert window.current_route is ShellRoute.LOGIN
    assert window.findChild(QWidget, "project_page") is not None

    window.show_route(ShellRoute.PROJECT)

    assert window.current_route is ShellRoute.PROJECT
    assert window.findChild(QPushButton, "create_project_button") is not None


def test_project_actions_fail_closed_without_application_service(
    app: QApplication,
) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    create = window.findChild(QPushButton, "create_project_button")
    open_project = window.findChild(QPushButton, "open_project_button")

    assert create is not None
    assert open_project is not None
    assert not create.isEnabled()
    assert not open_project.isEnabled()
    assert "Application Service" in create.accessibleDescription()
    assert "Application Service" in open_project.accessibleDescription()
    assert "persistierte Projektdaten" in open_project.toolTip()


def test_project_workspace_renders_backend_records_and_opens_selected_id(
    app: QApplication,
) -> None:
    from mcm_solarcheck.storage.queries import ProjectRecord

    opened: list[str | None] = []
    projects = (
        ProjectRecord("P-2", "Dach Süd", "2026-09-26 18:00:00"),
        ProjectRecord("P-1", "Halle Nord", "2026-09-25 12:00:00"),
    )
    page = make_project_page(projects=projects, on_open_project=opened.append)
    project_list = page.findChild(QListWidget, "project_list")
    open_project = page.findChild(QPushButton, "open_project_button")

    assert project_list is not None
    assert open_project is not None
    assert project_list.count() == 2
    assert project_list.item(0).text() == "Dach Süd · 2026-09-26 18:00:00"
    assert project_list.item(0).data(256) == "P-2"
    assert not open_project.isEnabled()

    project_list.setCurrentRow(1)
    assert open_project.isEnabled()
    open_project.click()

    assert opened == ["P-1"]


def test_shell_supplies_service_projects_to_workspace(app: QApplication) -> None:
    class ProjectService:
        def projects(self):
            return (
                ProjectRecord("P-42", "Persistierter Solarpark", "2026-09-26 18:00:00"),
            )

    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=ProjectService()
    )
    project_list = window.findChild(QListWidget, "project_list")

    assert project_list is not None
    assert project_list.count() == 1
    assert "Persistierter Solarpark" in project_list.item(0).text()
    assert project_list.item(0).data(256) == "P-42"


def test_shell_without_project_service_keeps_workspace_empty(app: QApplication) -> None:
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    project_list = window.findChild(QListWidget, "project_list")
    empty = window.findChild(QLabel, "project_empty_state")

    assert project_list is not None
    assert project_list.count() == 0
    assert not project_list.isVisible()
    assert empty is not None
    assert not empty.isHidden()


def test_project_open_applies_service_workflow_state_to_shell(app: QApplication) -> None:
    blocked = ProjectWorkflowState(
        (
            StageReadiness(WorkflowStage.PROJECT, True),
            StageReadiness(WorkflowStage.IMPORT, False, ("processing prerequisite",)),
            StageReadiness(WorkflowStage.PROCESSING, False, ("processing prerequisite",)),
            StageReadiness(WorkflowStage.REVIEW, False, ("review prerequisite",)),
            StageReadiness(WorkflowStage.REPORT, False, ("report prerequisite",)),
            StageReadiness(WorkflowStage.EXPORT, False, ("export prerequisite",)),
        )
    )

    class ProjectService:
        def projects(self):
            return (ProjectRecord("P-OPEN", "Persistiertes Projekt", "2026-09-26 18:00:00"),)

        def open_project(self, project_id):
            assert project_id == "P-OPEN"
            return blocked

    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=ProjectService()
    )
    project_list = window.findChild(QListWidget, "project_list")
    open_button = window.findChild(QPushButton, "open_project_button")
    project_list.setCurrentRow(0)
    open_button.click()

    assert window.current_project_id == "P-OPEN"
    assert window.action(ShellCommandId.IMPORT).isEnabled()
    assert not window.action(ShellCommandId.PROCESS).isEnabled()
    assert window.action(ShellCommandId.PROCESS).toolTip() == "processing prerequisite"


def test_failed_project_open_does_not_replace_current_project(app: QApplication) -> None:
    class ProjectService:
        def projects(self):
            return (ProjectRecord("P-FAIL", "Persistiertes Projekt", "2026-09-26 18:00:00"),)

        def open_project(self, project_id):
            raise KeyError(f"Unknown project: {project_id}")

    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=ProjectService()
    )
    project_list = window.findChild(QListWidget, "project_list")
    open_button = window.findChild(QPushButton, "open_project_button")
    project_list.setCurrentRow(0)

    try:
        open_button.click()
    except KeyError:
        pass

    assert window.current_project_id is None


def test_shell_refreshes_project_workspace_only_after_successful_creation(app: QApplication) -> None:
    class ProjectService:
        def __init__(self):
            self.records = []

        def projects(self):
            return tuple(self.records)

        def create_project(self, project_id, name):
            record = ProjectRecord(project_id, name, "2026-09-26 19:00:00")
            self.records.append(record)
            return record

        def open_project(self, project_id):
            assert project_id == "P-NEW"
            return ProjectWorkflowState(
                tuple(StageReadiness(stage, True) for stage in WorkflowStage)
            )

    service = ProjectService()
    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=service
    )

    window._create_project("P-NEW", "Neuer Solarpark")

    project_page = window._pages[ShellRoute.PROJECT]
    project_list = project_page.findChild(QListWidget, "project_list")
    assert project_list is not None
    assert project_list.count() == 1
    assert project_list.item(0).data(256) == "P-NEW"
    assert "Neuer Solarpark" in project_list.item(0).text()


def test_failed_project_creation_does_not_refresh_or_invent_project(app: QApplication) -> None:
    class ProjectService:
        def projects(self):
            return ()

        def create_project(self, project_id, name):
            raise ValueError("creation rejected")

    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=ProjectService()
    )
    original_page = window.findChild(QWidget, "project_page")

    try:
        window._create_project("P-FAIL", "Nicht gespeichert")
    except ValueError:
        pass

    project_list = window.findChild(QListWidget, "project_list")
    assert window.findChild(QWidget, "project_page") is original_page
    assert project_list is not None
    assert project_list.count() == 0


def test_successful_project_creation_opens_persisted_project_and_applies_state(app: QApplication) -> None:
    state = ProjectWorkflowState(
        (
            StageReadiness(WorkflowStage.PROJECT, True),
            StageReadiness(WorkflowStage.IMPORT, False, ("import prerequisite",)),
            StageReadiness(WorkflowStage.PROCESSING, False, ("processing prerequisite",)),
            StageReadiness(WorkflowStage.REVIEW, False, ("review prerequisite",)),
            StageReadiness(WorkflowStage.REPORT, False, ("report prerequisite",)),
            StageReadiness(WorkflowStage.EXPORT, False, ("export prerequisite",)),
        )
    )

    class ProjectService:
        def __init__(self):
            self.records = []

        def projects(self):
            return tuple(self.records)

        def create_project(self, project_id, name):
            record = ProjectRecord(project_id, name, "2026-09-26 19:30:00")
            self.records.append(record)
            return record

        def open_project(self, project_id):
            assert project_id == "P-CREATED"
            assert any(record.project_id == project_id for record in self.records)
            return state

    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=ProjectService()
    )

    window._create_project("P-CREATED", "Neu angelegt")

    assert window.current_project_id == "P-CREATED"
    assert window.action(ShellCommandId.IMPORT).isEnabled()
    assert not window.action(ShellCommandId.PROCESS).isEnabled()
    assert window.action(ShellCommandId.PROCESS).toolTip() == "import prerequisite"


def test_new_project_dialog_requires_nonblank_identity(app: QApplication) -> None:
    dialog = NewProjectDialog()
    buttons = dialog.findChild(QDialogButtonBox)
    ok = buttons.button(QDialogButtonBox.StandardButton.Ok)

    assert not ok.isEnabled()

    dialog.project_id.setText("   ")
    dialog.name.setText("Solarpark")
    assert not ok.isEnabled()

    dialog.project_id.setText("P-1")
    dialog.name.setText("   ")
    assert not ok.isEnabled()

    dialog.name.setText("Solarpark")
    assert ok.isEnabled()
    assert dialog.values() == ("P-1", "Solarpark")


def test_import_workspace_is_fail_closed_without_project_context(app: QApplication) -> None:
    page = make_import_page()
    button = page.findChild(QPushButton, "import_images_button")
    context = page.findChild(QLabel, "import_project_context")

    assert context.text() == "Kein aktives Projekt ausgewählt."
    assert not button.isEnabled()


def test_import_workspace_requires_callback_even_with_project(app: QApplication) -> None:
    page = make_import_page(current_project_id="P-IMPORT")
    button = page.findChild(QPushButton, "import_images_button")
    context = page.findChild(QLabel, "import_project_context")

    assert context.text() == "Aktives Projekt: P-IMPORT"
    assert not button.isEnabled()


def test_import_workspace_enables_service_callback_for_active_project(app: QApplication) -> None:
    calls = []
    page = make_import_page(
        current_project_id="P-IMPORT",
        on_import_images=calls.append,
        choose_directory=lambda: "/tmp/import-images",
    )
    button = page.findChild(QPushButton, "import_images_button")

    assert button.isEnabled()
    button.click()
    assert calls == ["/tmp/import-images"]


def test_open_project_refreshes_import_workspace_with_persisted_context(app: QApplication) -> None:
    state = ProjectWorkflowState(
        tuple(StageReadiness(stage, True) for stage in WorkflowStage)
    )

    class ProjectService:
        def projects(self):
            return (ProjectRecord("P-IMPORT", "Importprojekt", "2026-09-27 17:00:00"),)

        def open_project(self, project_id):
            assert project_id == "P-IMPORT"
            return state

    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=ProjectService()
    )
    original_import_page = window._pages[ShellRoute.IMPORT]

    window._open_project("P-IMPORT")

    import_page = window._pages[ShellRoute.IMPORT]
    context = import_page.findChild(QLabel, "import_project_context")
    button = import_page.findChild(QPushButton, "import_images_button")
    assert import_page is not original_import_page
    assert context.text() == "Aktives Projekt: P-IMPORT"
    assert button.isEnabled()


def test_import_request_routes_through_service_and_applies_backend_state(app: QApplication) -> None:
    state = ProjectWorkflowState(
        tuple(StageReadiness(stage, True) for stage in WorkflowStage)
    )

    class ProjectService:
        def projects(self):
            return (ProjectRecord("P-IMPORT", "Importprojekt", "2026-09-27 18:00:00"),)

        def open_project(self, project_id):
            assert project_id == "P-IMPORT"
            return state

        def import_project_images(self, project_id, source_directory):
            assert project_id == "P-IMPORT"
            assert source_directory == "/tmp/import-images"
            return WorkflowAttempt(WorkflowAction.IMPORT, True), object(), state

    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=ProjectService()
    )
    window._open_project("P-IMPORT")

    window._request_image_import("/tmp/import-images")

    assert window.current_project_id == "P-IMPORT"
    assert window.action(ShellCommandId.PROCESS).isEnabled()


def test_import_workspace_cancel_does_not_call_service_callback(app: QApplication) -> None:
    calls = []
    page = make_import_page(
        current_project_id="P-IMPORT",
        on_import_images=calls.append,
        choose_directory=lambda: "",
    )
    button = page.findChild(QPushButton, "import_images_button")

    button.click()

    assert calls == []


def test_import_workspace_renders_backend_summary_without_inventing_counts(app: QApplication) -> None:
    class Summary:
        rgb_frames = 12
        thermal_frames = 10
        image_pairs = 9

    page = make_import_page(
        current_project_id="P-IMPORT",
        import_summary=Summary(),
    )
    summary = page.findChild(QLabel, "import_summary")

    assert summary is not None
    assert summary.text() == "12 RGB · 10 Thermal · 9 Paare"


def test_import_workspace_omits_summary_when_backend_has_none(app: QApplication) -> None:
    page = make_import_page(current_project_id="P-IMPORT")

    assert page.findChild(QLabel, "import_summary") is None


def test_open_project_presents_persisted_import_summary_from_service(app: QApplication) -> None:
    state = ProjectWorkflowState(
        tuple(StageReadiness(stage, True) for stage in WorkflowStage)
    )

    class Summary:
        rgb_frames = 8
        thermal_frames = 7
        image_pairs = 6

    class ProjectService:
        def projects(self):
            return (ProjectRecord("P-SUMMARY", "Summary project", "2026-09-27 19:00:00"),)

        def open_project(self, project_id):
            assert project_id == "P-SUMMARY"
            return state

        def import_summary(self, project_id):
            assert project_id == "P-SUMMARY"
            return Summary()

    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=ProjectService()
    )

    window._open_project("P-SUMMARY")

    summary = window._pages[ShellRoute.IMPORT].findChild(QLabel, "import_summary")
    assert summary is not None
    assert summary.text() == "8 RGB · 7 Thermal · 6 Paare"


def test_successful_import_refreshes_summary_from_persisted_service_state(app: QApplication) -> None:
    state = ProjectWorkflowState(
        tuple(StageReadiness(stage, True) for stage in WorkflowStage)
    )

    class Summary:
        def __init__(self, rgb_frames, thermal_frames, image_pairs):
            self.rgb_frames = rgb_frames
            self.thermal_frames = thermal_frames
            self.image_pairs = image_pairs

    class ProjectService:
        def __init__(self):
            self.imported = False

        def projects(self):
            return (ProjectRecord("P-IMPORT", "Importprojekt", "2026-09-27 19:30:00"),)

        def open_project(self, project_id):
            return state

        def import_summary(self, project_id):
            return Summary(4, 3, 2) if self.imported else Summary(0, 0, 0)

        def import_project_images(self, project_id, source_directory):
            self.imported = True
            return WorkflowAttempt(WorkflowAction.IMPORT, True), object(), state

    service = ProjectService()
    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=service
    )
    window._open_project("P-IMPORT")

    window._request_image_import("/tmp/import-images")

    summary = window._pages[ShellRoute.IMPORT].findChild(QLabel, "import_summary")
    assert summary is not None
    assert summary.text() == "4 RGB · 3 Thermal · 2 Paare"


def test_import_workspace_labels_summary_as_persisted_backend_state(app: QApplication) -> None:
    class Summary:
        rgb_frames = 3
        thermal_frames = 2
        image_pairs = 1

    page = make_import_page(
        current_project_id="P-IMPORT",
        import_summary=Summary(),
    )

    heading = page.findChild(QLabel, "import_summary_heading")
    summary = page.findChild(QLabel, "import_summary")

    assert heading is not None
    assert heading.text() == "Persistierter Importstand"
    assert summary is not None
    assert summary.accessibleDescription() == (
        "Persistierte Bild- und Paarzahlen des aktiven Projekts."
    )


def test_import_workspace_presents_backend_attempt_outcome_without_inference(app: QApplication) -> None:
    class FailedAttempt:
        succeeded = False
        error = "thermal metadata unavailable"

    failed_page = make_import_page(
        current_project_id="P-IMPORT",
        import_attempt=FailedAttempt(),
    )
    failed_status = failed_page.findChild(QLabel, "import_attempt_status")

    assert failed_status is not None
    assert failed_status.text() == "Import fehlgeschlagen: thermal metadata unavailable"

    class SuccessfulAttempt:
        succeeded = True
        error = None

    successful_page = make_import_page(
        current_project_id="P-IMPORT",
        import_attempt=SuccessfulAttempt(),
    )
    successful_status = successful_page.findChild(QLabel, "import_attempt_status")

    assert successful_status is not None
    assert successful_status.text() == "Letzter Import erfolgreich abgeschlossen."


def test_import_workspace_omits_attempt_status_without_backend_attempt(app: QApplication) -> None:
    page = make_import_page(current_project_id="P-IMPORT")

    assert page.findChild(QLabel, "import_attempt_status") is None
