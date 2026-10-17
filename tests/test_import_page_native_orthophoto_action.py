"""Native orthophoto action is never advertised as ready without wiring."""
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QPushButton
from mcm_solarcheck.gui.import_page import make_import_page


def test_native_orthophoto_button_is_disabled_without_verified_workflow(qtbot):
    page = make_import_page(current_project_id="p1")
    qtbot.addWidget(page)
    button = page.findChild(QPushButton, "generate_orthophotos_button")
    assert button is not None
    assert not button.isEnabled()
    assert "Vermessung" in button.toolTip()
