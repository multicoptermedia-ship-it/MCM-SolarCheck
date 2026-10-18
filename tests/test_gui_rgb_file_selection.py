"""Qt import page accepts individual RGB files without requiring ZIP."""
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from mcm_solarcheck.gui.import_page import make_import_page


def test_rgb_selection_callback_receives_individual_paths():
    app = QApplication.instance() or QApplication([])
    selected = []
    page = make_import_page(
        current_project_id="P1",
        on_preview_rgb_files=lambda paths: selected.append(paths),
        choose_rgb_files=lambda: ["/local/1.jpg", "/local/2.jpg", "/local/3.jpg"],
    )
    from PySide6.QtWidgets import QPushButton
    button = page.findChild(QPushButton, "preview_rgb_files_button")
    assert button is not None and button.isEnabled()
    button.click()
    assert selected == [("/local/1.jpg", "/local/2.jpg", "/local/3.jpg")]
    page.close()


def test_rgb_selection_disabled_without_project():
    app = QApplication.instance() or QApplication([])
    from PySide6.QtWidgets import QPushButton
    page = make_import_page(on_preview_rgb_files=lambda paths: None)
    button = page.findChild(QPushButton, "preview_rgb_files_button")
    assert button is not None and not button.isEnabled()
    page.close()


def test_rgb_selection_cancel_does_not_call_service():
    app = QApplication.instance() or QApplication([])
    from PySide6.QtWidgets import QPushButton
    selected = []
    page = make_import_page(
        current_project_id="P1",
        on_preview_rgb_files=lambda paths: selected.append(paths),
        choose_rgb_files=lambda: [],
        rgb_preview_status="Nicht metrische RGB-Vorschau erstellt.",
    )
    button = page.findChild(QPushButton, "preview_rgb_files_button")
    button.click()
    assert selected == []
    from PySide6.QtWidgets import QLabel
    status = page.findChild(QLabel, "rgb_preview_status")
    assert "Nicht metrische" in status.text()
    page.close()
