"""Qt import-page contracts for opt-in, local benchmark comparisons."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.gui.import_page import make_import_page


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _button(page, name):
    button = page.findChild(QPushButton, name)
    assert button is not None
    return button


def test_comparison_actions_require_project_and_explicit_callbacks(qt_app):
    page = make_import_page(
        current_project_id=None,
        on_compare_benchmark_reports=lambda paths: None,
        on_save_benchmark_comparison=lambda destination: None,
    )
    try:
        assert not _button(page, "compare_offline_benchmark_reports").isEnabled()
        assert not _button(page, "save_offline_benchmark_comparison").isEnabled()
        assert page.findChild(QLabel, "offline_benchmark_comparison") is None
    finally:
        page.close()
    no_handlers = make_import_page(current_project_id="P1")
    try:
        assert not _button(no_handlers, "compare_offline_benchmark_reports").isEnabled()
        assert not _button(no_handlers, "save_offline_benchmark_comparison").isEnabled()
    finally:
        no_handlers.close()


def test_user_selected_paths_and_explicit_export_are_separate(qt_app):
    selected = []
    exports = []
    page = make_import_page(
        current_project_id="P1",
        on_compare_benchmark_reports=lambda paths: selected.append(paths),
        choose_benchmark_reports=lambda: [
            "/private/customer-01.json", "/private/customer-02.json",
            "/private/customer-03.json",
        ],
        benchmark_comparison_text=(
            "3 Messungen, Median 4.0 s. Prozess-RSS seit Prozessstart, "
            "keine isolierte Importspitze."
        ),
        on_save_benchmark_comparison=lambda destination: exports.append(destination),
        choose_benchmark_comparison_destination=lambda: "/tmp/result.json",
    )
    try:
        label = page.findChild(QLabel, "offline_benchmark_comparison")
        assert label is not None
        assert label.textFormat() == Qt.TextFormat.PlainText
        assert "keine isolierte Importspitze" in label.text()
        assert "customer" not in label.text()
        assert selected == []
        assert exports == []
        _button(page, "compare_offline_benchmark_reports").click()
        assert selected == [(
            "/private/customer-01.json", "/private/customer-02.json",
            "/private/customer-03.json",
        )]
        assert exports == []
        _button(page, "save_offline_benchmark_comparison").click()
        assert exports == ["/tmp/result.json"]
    finally:
        page.close()


def test_dialog_cancellation_creates_no_callback(qt_app):
    selected = []
    exports = []
    page = make_import_page(
        current_project_id="P1",
        on_compare_benchmark_reports=lambda paths: selected.append(paths),
        choose_benchmark_reports=lambda: [],
        on_save_benchmark_comparison=lambda path: exports.append(path),
        choose_benchmark_comparison_destination=lambda: "",
    )
    try:
        _button(page, "compare_offline_benchmark_reports").click()
        _button(page, "save_offline_benchmark_comparison").click()
        assert selected == []
        assert exports == []
    finally:
        page.close()
