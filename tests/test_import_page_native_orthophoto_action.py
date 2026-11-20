import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication, QPushButton
from mcm_solarcheck.gui.import_page import make_import_page


def test_import_does_not_offer_the_frozen_native_orthophoto_engine():
    app = QApplication.instance() or QApplication([])
    page = make_import_page(current_project_id='p1')
    assert page.findChild(QPushButton, 'generate_orthophotos_button') is None
    assert page.findChild(QPushButton, 'register_orthophoto_pair_button') is not None
    page.close()
