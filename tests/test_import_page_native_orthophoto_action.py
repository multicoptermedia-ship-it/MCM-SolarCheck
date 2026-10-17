import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication, QPushButton
from mcm_solarcheck.gui.import_page import make_import_page


def test_native_orthophoto_button_is_disabled_without_verified_workflow():
    app = QApplication.instance() or QApplication([])
    page = make_import_page(current_project_id='p1')
    button = page.findChild(QPushButton, 'generate_orthophotos_button')
    assert button is not None
    assert not button.isEnabled()
    assert 'Vermessung' in button.toolTip()
    page.close()
