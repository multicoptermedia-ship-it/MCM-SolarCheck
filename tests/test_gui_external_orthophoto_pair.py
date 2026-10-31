"""Existing desktop GeoTIFF import extended to explicit sensor pairs."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton

from mcm_solarcheck.gui.import_page import make_import_page


@pytest.fixture(scope='module')
def qapp():
    return QApplication.instance() or QApplication([])


def _sources(tmp_path):
    rgb, thermal = tmp_path / 'rgb-ortho.tif', tmp_path / 'thermal-ortho.tif'
    transform = from_origin(350000, 5650000, .1, .1)
    with rasterio.open(rgb, 'w', driver='GTiff', width=20, height=20, count=3,
                       dtype='uint8', crs='EPSG:25832', transform=transform) as target:
        target.write(np.full((3, 20, 20), 70, np.uint8))
        target.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue)
    with rasterio.open(thermal, 'w', driver='GTiff', width=20, height=20, count=1,
                       dtype='float32', nodata=np.nan, crs='EPSG:25832', transform=transform) as target:
        target.write(np.full((1, 20, 20), 100., np.float32))
    return rgb, thermal


def test_pair_picker_needs_a_project_and_complete_selection(qapp):
    empty = make_import_page()
    assert not empty.findChild(QPushButton, 'register_orthophoto_pair_button').isEnabled()
    calls = []
    page = make_import_page(current_project_id='P1', on_register_orthophoto_pair=lambda *a: calls.append(a),
                            choose_register_orthophoto_pair=lambda: ('rgb.tif', ''))
    page.findChild(QPushButton, 'register_orthophoto_pair_button').click()
    assert calls == []


def test_pair_picker_keeps_explicit_sensor_roles_and_value_kind(qapp):
    calls = []
    page = make_import_page(current_project_id='P1', on_register_orthophoto_pair=lambda *a: calls.append(a),
                            choose_register_orthophoto_pair=lambda: ('rgb.tif', 'thermal.tif'))
    kind = page.findChild(QComboBox, 'orthophoto_thermal_value_kind')
    kind.setCurrentIndex(kind.findData('sensor_values'))
    page.findChild(QPushButton, 'register_orthophoto_pair_button').click()
    assert calls == [('rgb.tif', 'thermal.tif', 'sensor_values')]


def test_desktop_pair_import_survives_reopen_without_approving_project(tmp_path, qapp, monkeypatch):
    import hashlib
    import socket
    from mcm_solarcheck.offline.composition import build_offline_services
    from mcm_solarcheck.gui.shell import SolarCheckMainWindow
    from mcm_solarcheck.services.deployment import DeploymentMode
    from mcm_solarcheck.services.shell_navigation import ShellRoute

    def forbidden_network(*_a, **_kw):
        pytest.fail('local orthophoto intake must not use the network')
    monkeypatch.setattr(socket, 'create_connection', forbidden_network)
    rgb, thermal = _sources(tmp_path)
    originals = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)]
    database = tmp_path / 'project.sqlite'
    service = build_offline_services(database).projects
    service.create_project('P1', 'Synthetic paired orthophotos')
    service.create_project('P2', 'Another project')
    before = service.state('P1')
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    window._open_project('P1')
    window._register_project_orthophoto_pair(str(rgb), str(thermal), 'sensor_values')
    page = window._pages[ShellRoute.IMPORT]
    assert page.findChild(QComboBox, 'registered_orthophoto_pairs').count() == 1
    assert 'keine fachliche' in page.findChild(QLabel, 'geotiff_inspection_result').text()
    assert window._orthophoto_comparison is not None
    assert service.state('P1') == before
    window.close()

    reopened = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP,
                                   project_service=build_offline_services(database).projects)
    reopened._open_project('P1')
    page = reopened._pages[ShellRoute.IMPORT]
    assert page.findChild(QComboBox, 'registered_orthophoto_pairs').count() == 1
    page.findChild(QPushButton, 'show_registered_orthophoto_pair_button').click()
    assert reopened._orthophoto_comparison is not None
    from PySide6.QtCore import QCoreApplication, QEvent
    page = reopened._pages[ShellRoute.IMPORT]
    page.findChild(QPushButton, 'inspect_orthophoto_modules_button').click()
    dialog = reopened._orthophoto_pv_dialog
    assert dialog is not None
    dialog.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert reopened._orthophoto_pv_dialog is None
    page.findChild(QPushButton, 'inspect_orthophoto_modules_button').click()
    assert reopened._orthophoto_pv_dialog is not None
    reopened._open_project('P2')
    assert reopened._orthophoto_pv_dialog is None
    assert reopened._pages[ShellRoute.IMPORT].findChild(QComboBox, 'registered_orthophoto_pairs') is None
    assert reopened._orthophoto_comparison is None
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)] == originals
    reopened.close()


def test_saved_pair_offers_existing_pv_bridge_with_explicit_roles(qapp):
    requested = []
    pair = {'rgb_source_path': 'rgb.tif', 'thermal_source_path': 'thermal.tif'}
    page = make_import_page(current_project_id='P1', orthophoto_pairs=(pair,),
                            on_inspect_orthophoto_modules=lambda *a: requested.append(a))
    page.findChild(QPushButton, 'inspect_orthophoto_modules_button').click()
    assert requested == [('rgb.tif', 'thermal.tif')]
