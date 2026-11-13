"""Existing desktop GeoTIFF import extended to explicit sensor pairs."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QLabel, QPushButton

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


def test_joint_native_picker_offers_both_formats_and_sends_all_jpgs_to_original_import(qapp, monkeypatch):
    selections = iter((['rgb1.JPG', 'rgb2.JPG'], ['thermal1.JPG', 'thermal2.JPG']))
    dialogs, calls = [], []
    def choose(parent, title, directory, file_filter):
        dialogs.append((title, file_filter))
        return next(selections), ''
    monkeypatch.setattr(QFileDialog, 'getOpenFileNames', choose)
    page = make_import_page(
        current_project_id='P1', on_import_original_files=lambda paths: calls.append(paths),
        on_register_orthophoto_pair=lambda *a: pytest.fail('JPGs are not finished orthophotos'),
    )
    try:
        page.findChild(QPushButton, 'register_orthophoto_pair_button').click()
        assert calls == [('rgb1.JPG', 'rgb2.JPG', 'thermal1.JPG', 'thermal2.JPG')]
        assert len(dialogs) == 2
        assert 'RGB' in dialogs[0][0] and 'Thermal' in dialogs[1][0]
        for _, file_filter in dialogs:
            assert '*.jpg' in file_filter and '*.tif' in file_filter and '*.tiff' in file_filter
        assert page.findChild(QLabel, 'joint_image_import_status').text() == ''
    finally:
        page.close()


@pytest.mark.parametrize('cancel_second', (False, True))
def test_joint_picker_cancellation_never_imports_a_partial_selection(qapp, monkeypatch, cancel_second):
    selections = iter((['rgb.JPG'], []) if cancel_second else ([],))
    dialogs = []
    def choose(*args):
        dialogs.append(args)
        return next(selections), ''
    monkeypatch.setattr(QFileDialog, 'getOpenFileNames', choose)
    page = make_import_page(
        current_project_id='P1',
        on_import_original_files=lambda *a: pytest.fail('cancelled'),
        on_register_orthophoto_pair=lambda *a: pytest.fail('cancelled'),
    )
    try:
        page.findChild(QPushButton, 'register_orthophoto_pair_button').click()
        assert len(dialogs) == (2 if cancel_second else 1)
    finally:
        page.close()


@pytest.mark.parametrize('selections', (
    (['rgb.JPG'], ['thermal.tif']),
    (['rgb.tif'], ['thermal.JPG']),
    (['rgb.JPG', 'rgb.tif'], ['thermal.JPG']),
    (['rgb.tif', 'another-rgb.tif'], ['thermal.tif']),
    (['rgb.png'], ['thermal.png']),
))
def test_joint_picker_rejects_mixed_or_ambiguous_roles_without_calling_import(qapp, selections):
    page = make_import_page(
        current_project_id='P1', choose_register_orthophoto_pair=lambda: selections,
        on_import_original_files=lambda *a: pytest.fail('invalid input'),
        on_register_orthophoto_pair=lambda *a: pytest.fail('invalid input'),
    )
    try:
        page.findChild(QPushButton, 'register_orthophoto_pair_button').click()
        assert 'getrennt importieren' in page.findChild(QLabel, 'joint_image_import_status').text()
    finally:
        page.close()


def test_joint_picker_does_not_register_jpg_as_orthophoto_when_original_import_is_unavailable(qapp):
    page = make_import_page(
        current_project_id='P1', choose_register_orthophoto_pair=lambda: ('rgb.JPG', 'thermal.JPG'),
        on_register_orthophoto_pair=lambda *a: pytest.fail('JPGs require original import'),
    )
    try:
        page.findChild(QPushButton, 'register_orthophoto_pair_button').click()
        assert 'JPG-Import derzeit nicht verfügbar' in page.findChild(QLabel, 'joint_image_import_status').text()
    finally:
        page.close()


def test_joint_jpg_selection_uses_existing_staging_thread_sqlite_and_reopens(tmp_path, qapp, monkeypatch):
    from dataclasses import replace
    from mcm_solarcheck.gui.shell import SolarCheckMainWindow
    from mcm_solarcheck.offline.composition import build_offline_services
    from mcm_solarcheck.services.deployment import DeploymentMode
    from mcm_solarcheck.services.shell_navigation import ShellRoute
    import mcm_solarcheck.services.project_pipeline as pipeline
    from test_original_files_project_bridge import loose_originals
    from test_original_zip_project_bridge import fake_import_in_durable_folder
    from test_gui_image_import_thread import pump_until

    originals = loose_originals(tmp_path)
    thermal, rgb = originals[0], originals[2]
    before = {p: p.read_bytes() for p in originals}
    # Only the existing decoder boundary is synthetic; staging, thread,
    # SQLite transaction, project isolation and reopening are real.
    def decode(folder, **kwargs):
        imported = fake_import_in_durable_folder(folder, **kwargs)
        return replace(imported, rgb_frames=(imported.rgb_frames[1],))
    monkeypatch.setattr(pipeline, 'import_m3t_project', decode)
    selections = iter(([str(rgb)], [str(thermal)]))
    monkeypatch.setattr(QFileDialog, 'getOpenFileNames', lambda *a: (next(selections), ''))
    database = tmp_path / 'project.sqlite3'
    service = build_offline_services(database).projects
    service.create_project('P1', 'Synthetic originals')
    service.create_project('P2', 'Unchanged')
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    try:
        window._open_project('P1')
        window._pages[ShellRoute.IMPORT].findChild(QPushButton, 'register_orthophoto_pair_button').click()
        pump_until(lambda: window._import_thread is None)
        summary = service.import_summary('P1')
        assert (summary.rgb_frames, summary.thermal_frames, summary.image_pairs) == (1, 1, 1)
        assert service.import_summary('P2').rgb_frames == 0
        assert service.project_orthophoto_pairs('P1') == ()  # Originals, no fabricated orthophoto.
        assert '1 RGB' in window._pages[ShellRoute.IMPORT].findChild(QLabel, 'import_summary').text()
        assert window._pages[ShellRoute.PROCESSING].findChild(QPushButton, 'processing_generate_micmac').isEnabled()
    finally:
        window.close()
    reopened = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP,
                                   project_service=build_offline_services(database).projects)
    try:
        reopened._open_project('P1')
        assert '1 RGB' in reopened._pages[ShellRoute.IMPORT].findChild(QLabel, 'import_summary').text()
        assert all(path.read_bytes() == data for path, data in before.items())
        saved = next((tmp_path / 'private-m3t-originals').iterdir())
        assert (saved / rgb.name).read_bytes() == before[rgb]
        assert (saved / thermal.name).read_bytes() == before[thermal]
    finally:
        reopened.close()


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
