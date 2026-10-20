"""Independent Qt/SQLite privacy contract for explicit offline JSON export.

Only the file chooser is replaced: export and non-overwrite checks use the real
service and local filesystem. All project identities and file bytes are synthetic.
"""

import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QPushButton, QWidget

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.offline_import_metrics import ImportPerformanceSnapshot
from mcm_solarcheck.services.shell_navigation import ShellRoute


PRIVATE_CUSTOMER = "PRIVATER_KUNDENNAME"
PRIVATE_PROJECT = "privates-projekt-pilot-4711"
OTHER_PROJECT = "anderes-projekt-pilot-9284"


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def uncaught_qt_errors(monkeypatch):
    # Exceptions from Python Qt slots may reach sys.excepthook rather than the
    # caller of button.click(); assert that neither route silently hides one.
    errors = []
    monkeypatch.setattr(sys, "excepthook", lambda *error: errors.append(error))
    yield errors
    assert errors == [], "The export action raised an uncaught Qt-slot exception"


@pytest.fixture
def snapshot():
    return ImportPerformanceSnapshot(
        elapsed_seconds=12.5,
        read_and_pair_seconds=10.0,
        sqlite_commit_seconds=2.5,
        observed_progress_updates=4,
        reported_checkpoints=8,
        process_peak_rss_bytes=96 * 1024 * 1024,
        process_peak_rss_at_start_bytes=64 * 1024 * 1024,
        outcome="succeeded",
    )


@pytest.fixture
def offline_window(qt_app, tmp_path, snapshot, uncaught_qt_errors):
    window = build_offline_window(tmp_path / "offline.sqlite3")
    service = window._project_service
    service.create_project(PRIVATE_PROJECT, PRIVATE_CUSTOMER)
    service.create_project(OTHER_PROJECT, "Anderer synthetischer Kunde")
    window._open_project(PRIVATE_PROJECT)
    # This pilot begins with an already available measurement. Image decoding
    # and worker completion have separate integration coverage.
    window._import_performance_snapshot = snapshot
    window._refresh_import_page()
    try:
        yield window
    finally:
        window.close()
        QApplication.processEvents()


def metrics_label(window):
    label = window._pages[ShellRoute.IMPORT].findChild(
        QLabel, "offline_import_metrics",
    )
    assert label is not None
    return label


def export_button(window):
    button = window._pages[ShellRoute.IMPORT].findChild(
        QPushButton, "save_offline_import_metrics",
    )
    assert button is not None
    return button


def import_page_text(window):
    """Include widget text and accessibility surfaces, not just one label."""
    page = window._pages[ShellRoute.IMPORT]
    assert page.objectName() == "import_page"
    parts = []
    for widget in [page, *page.findChildren(QWidget)]:
        for name in (
            "text", "toolTip", "statusTip", "whatsThis",
            "accessibleName", "accessibleDescription",
        ):
            getter = getattr(widget, name, None)
            if callable(getter):
                value = getter()
                if isinstance(value, str):
                    parts.append(value)
    return "\n".join(parts)


def choose_destination(monkeypatch, destination):
    calls = []

    def choose(*args, **kwargs):
        calls.append(True)
        return str(destination), "JSON (*.json)"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", choose)
    return calls


def test_existing_private_target_stays_unchanged_without_ui_path_leak(
    offline_window, tmp_path, monkeypatch,
):
    destination = tmp_path / f"{PRIVATE_CUSTOMER}-vorhanden.json"
    original = b"Synthetische Kundendatei\x00\xff\nNicht ueberschreiben."
    destination.write_bytes(original)
    choices = choose_destination(monkeypatch, destination)
    before = metrics_label(offline_window).text()

    assert export_button(offline_window).isEnabled()
    assert choices == []
    export_button(offline_window).click()

    assert choices == [True]
    assert destination.read_bytes() == original
    message = metrics_label(offline_window).text()
    assert message.strip() and message != before, "No export failure was presented"
    # The wording may change; private target details must never reach the UI.
    for text in (message, import_page_text(offline_window)):
        assert PRIVATE_CUSTOMER not in text
        assert destination.name not in text
        assert str(destination) not in text
        assert str(tmp_path) not in text


def test_new_export_is_opt_in_anonymous_json_without_ui_destination_leak(
    offline_window, tmp_path, monkeypatch,
):
    destination = tmp_path / f"{PRIVATE_CUSTOMER}-neu.json"
    choices = choose_destination(monkeypatch, destination)
    assert not destination.exists()
    assert choices == []

    export_button(offline_window).click()

    assert choices == [True]
    raw = destination.read_text(encoding="utf-8")
    document = json.loads(raw)
    assert document["outcome"] == "succeeded"
    assert document["elapsed_seconds"] == 12.5
    assert document["contains_source_paths"] is False
    assert document["contains_project_or_customer_ids"] is False
    # An allowlist checks the exported schema independently of the writer's
    # own anonymous_report() implementation and its self-reported flags.
    assert set(document) <= {
        "schema_version", "measurement", "outcome", "elapsed_seconds",
        "read_and_pair_seconds", "sqlite_commit_seconds", "progress_updates",
        "checkpoints_reported", "process_peak_rss_bytes",
        "process_peak_rss_at_start_bytes", "rss_scope", "sampling",
        "contains_source_paths", "contains_project_or_customer_ids",
        "is_real_dji_validation",
    }
    for private in (
        PRIVATE_CUSTOMER, PRIVATE_PROJECT, OTHER_PROJECT,
        destination.name, str(destination), str(tmp_path),
    ):
        assert private not in raw
    assert all(
        "/" not in value and "\\" not in value
        for value in document.values() if isinstance(value, str)
    )
    for private in (PRIVATE_CUSTOMER, destination.name, str(tmp_path)):
        assert private not in import_page_text(offline_window)


def test_missing_private_directory_fails_locally_without_creating_it(
    offline_window, tmp_path, monkeypatch,
):
    destination = tmp_path / PRIVATE_CUSTOMER / "messung.json"
    choose_destination(monkeypatch, destination)
    before = metrics_label(offline_window).text()

    export_button(offline_window).click()

    assert not destination.parent.exists()
    assert metrics_label(offline_window).text() != before
    assert PRIVATE_CUSTOMER not in import_page_text(offline_window)
    assert str(tmp_path) not in import_page_text(offline_window)


def test_project_switch_rejects_missing_and_stale_measurement_exports(
    offline_window, tmp_path, monkeypatch, snapshot,
):
    destination = tmp_path / "fremdes-projekt.json"
    choices = choose_destination(monkeypatch, destination)
    assert export_button(offline_window).isEnabled()

    offline_window._open_project(OTHER_PROJECT)

    assert offline_window._import_performance_snapshot is None
    assert offline_window._pages[ShellRoute.IMPORT].findChild(
        QLabel, "offline_import_metrics",
    ) is None
    assert not export_button(offline_window).isEnabled()
    export_button(offline_window).click()
    assert choices == []
    offline_window._save_import_metrics(PRIVATE_PROJECT, str(destination))
    assert not destination.exists()

    # Even after the new project has its own measurement, an old-project
    # callback must not be allowed to export the new project's data.
    offline_window._import_performance_snapshot = snapshot
    offline_window._refresh_import_page()
    assert export_button(offline_window).isEnabled()
    offline_window._save_import_metrics(PRIVATE_PROJECT, str(destination))
    assert not destination.exists()


def test_online_shell_rejects_local_export_even_with_a_stale_snapshot(
    offline_window, qt_app, tmp_path, monkeypatch, snapshot,
):
    destination = tmp_path / "online-verboten.json"
    choices = choose_destination(monkeypatch, destination)
    window = SolarCheckMainWindow(
        DeploymentMode.ONLINE, project_service=offline_window._project_service,
    )
    try:
        window._open_project(PRIVATE_PROJECT)
        window._import_performance_snapshot = snapshot
        window._refresh_import_page()
        assert window._pages[ShellRoute.IMPORT].findChild(
            QLabel, "offline_import_metrics",
        ) is None
        assert not export_button(window).isEnabled()
        export_button(window).click()
        window._save_import_metrics(PRIVATE_PROJECT, str(destination))
        assert choices == []
        assert not destination.exists()
    finally:
        window.close()
