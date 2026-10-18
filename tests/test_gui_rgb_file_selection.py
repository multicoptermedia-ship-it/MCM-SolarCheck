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


def test_local_preview_image_is_shown_with_nonmetric_description(tmp_path):
    from PIL import Image
    from PySide6.QtWidgets import QLabel
    image_path = tmp_path / "preview.png"
    Image.new("RGB", (200, 100), (120, 80, 40)).save(image_path)
    app = QApplication.instance() or QApplication([])
    page = make_import_page(
        current_project_id="P1",
        rgb_preview_path=image_path,
        rgb_preview_status="Nicht metrische RGB-Vorschau erstellt.",
    )
    image = page.findChild(QLabel, "rgb_preview_image")
    assert image is not None
    assert image.pixmap() is not None and not image.pixmap().isNull()
    assert image.pixmap().width() <= 720
    assert image.pixmap().height() <= 420
    assert "kein Orthofoto" in image.accessibleDescription()
    page.close()


def test_missing_preview_does_not_show_stale_image(tmp_path):
    from PySide6.QtWidgets import QLabel
    app = QApplication.instance() or QApplication([])
    page = make_import_page(current_project_id="P1",
                            rgb_preview_path=tmp_path / "missing.png")
    image = page.findChild(QLabel, "rgb_preview_image")
    assert image is not None
    assert image.pixmap() is None or image.pixmap().isNull()
    page.close()


def test_folder_action_forwards_one_directory_without_manual_image_selection():
    from PySide6.QtWidgets import QPushButton
    app = QApplication.instance() or QApplication([])
    selected = []
    page = make_import_page(
        current_project_id="P1",
        on_preview_rgb_folder=selected.append,
        choose_rgb_folder=lambda: "/local/dji-flight",
    )
    button = page.findChild(QPushButton, "preview_rgb_folder_button")
    assert button is not None and button.isEnabled()
    button.click()
    assert selected == ["/local/dji-flight"]
    page.close()


def test_folder_action_disabled_without_project():
    from PySide6.QtWidgets import QPushButton
    app = QApplication.instance() or QApplication([])
    page = make_import_page(
        on_preview_rgb_folder=lambda directory: None,
        choose_rgb_folder=lambda: "/local/dji-flight",
    )
    button = page.findChild(QPushButton, "preview_rgb_folder_button")
    assert button is not None and not button.isEnabled()
    page.close()
