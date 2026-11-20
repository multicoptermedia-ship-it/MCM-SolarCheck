"""Local image ROI selection -> existing detector -> thermal GIS proposals."""
from hashlib import sha256
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.gui.orthophoto_pv_review import (
    OrthophotoPVReviewDialog, OrthophotoROIImage,
)


@pytest.fixture(scope='module')
def qapp():
    return QApplication.instance() or QApplication([])


def _drag(image, start, end):
    QTest.mousePress(image, Qt.MouseButton.LeftButton, pos=QPoint(*start))
    QTest.mouseMove(image, QPoint(*end))
    QTest.mouseRelease(image, Qt.MouseButton.LeftButton, pos=QPoint(*end))


def _sources(tmp_path, width=800, height=600, *, modules=True):
    rgb, thermal = tmp_path/'rgb.tif', tmp_path/'thermal.tif'
    array = np.full((3, height, width), 230, np.uint8)
    if modules:
        # Two synthetic blue module rectangles, using RGB band order.
        array[:, 100:151, 100:181] = np.array((40, 70, 120), np.uint8)[:, None, None]
        array[:, 300:351, 400:481] = np.array((40, 70, 120), np.uint8)[:, None, None]
    transform = from_origin(350000, 5650000, .1, .1)
    with rasterio.open(rgb, 'w', driver='GTiff', width=width, height=height,
                       count=3, dtype='uint8', crs='EPSG:25832', transform=transform) as target:
        target.write(array)
        target.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue)
    with rasterio.open(thermal, 'w', driver='GTiff', width=width//2, height=height//2,
                       count=1, dtype='float32', nodata=np.nan, crs='EPSG:25832',
                       transform=from_origin(350000, 5650000, .2, .2)) as target:
        target.write(np.ones((1, height//2, width//2), np.float32))
    return rgb, thermal


def test_real_mouse_rectangle_maps_to_native_pixels_at_nonunit_scale(qapp):
    image = OrthophotoROIImage(np.zeros((100, 200, 3), np.uint8), (1000, 500))
    image.show()
    changes = []
    image.selection_changed.connect(changes.append)
    _drag(image, (20, 10), (39, 29))
    assert image.selected_window == (100, 50, 100, 100)
    assert changes == [(100, 50, 100, 100)]
    # Reverse drag uses the same selected native pixels.
    _drag(image, (39, 29), (20, 10))
    assert image.selected_window == (100, 50, 100, 100)
    image.close()


def test_oversized_native_selection_is_refused_before_detector_read(tmp_path, qapp, monkeypatch):
    rgb, thermal = _sources(tmp_path, 3000, 1500, modules=False)
    dialog = OrthophotoPVReviewDialog(rgb, thermal)
    dialog.show()
    image = dialog.findChild(OrthophotoROIImage, 'orthophoto_pv_roi_image')
    assert image.width() == 1024 and image.height() == 512
    _drag(image, (1, 1), (1023, 511))
    run = dialog.findChild(QPushButton, 'orthophoto_pv_detect_button')
    assert not run.isEnabled()
    assert 'kleineren Ausschnitt' in dialog.findChild(QLabel, 'orthophoto_pv_status').text()
    from mcm_solarcheck.gui import orthophoto_pv_review as module
    monkeypatch.setattr(module, 'detect_orthophoto_pv_window',
                        lambda *a, **kw: pytest.fail('oversized ROI must not run'))
    dialog._run_detection()
    assert dialog.proposal_result is None
    dialog.close()


def test_actual_detector_and_roi_render_pending_proposals_without_network_or_writes(tmp_path, qapp, monkeypatch):
    import socket
    def forbidden_network(*args, **kwargs):
        pytest.fail('local review must not use a network service')
    monkeypatch.setattr(socket, 'create_connection', forbidden_network)
    rgb, thermal = _sources(tmp_path)
    originals = [sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)]
    files_before = set(tmp_path.iterdir())
    dialog = OrthophotoPVReviewDialog(rgb, thermal)
    dialog.show()
    image = dialog.findChild(OrthophotoROIImage, 'orthophoto_pv_roi_image')
    _drag(image, (20, 20), (779, 579))
    run = dialog.findChild(QPushButton, 'orthophoto_pv_detect_button')
    assert run.isEnabled()
    run.click()
    result = dialog.proposal_result
    assert result is not None and len(result.proposals) == 2
    assert result.rgb_window == (20, 20, 760, 560)
    assert all(p.review_status == 'pending' for p in result.proposals)
    assert all(p.thermal_valid_coverage == 1. for p in result.proposals)
    assert all(not p.thermal_calibration_verified for p in result.proposals)
    assert not dialog.findChild(QLabel, 'orthophoto_pv_result_image').pixmap().isNull()
    status = dialog.findChild(QLabel, 'orthophoto_pv_status').text()
    assert '2 Modulvorschläge' in status and 'keine Temperaturauswertung' in status
    assert [sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)] == originals
    assert set(tmp_path.iterdir()) == files_before
    # A new selection cannot display the previous proposal overlay as its own.
    _drag(image, (5, 5), (50, 50))
    assert dialog.proposal_result is None
    assert dialog.findChild(QLabel, 'orthophoto_pv_result_image').pixmap().isNull()
    dialog.close()


def test_detector_failure_is_shown_without_approval_or_persisted_output(tmp_path, qapp, monkeypatch):
    from mcm_solarcheck.gui import orthophoto_pv_review as module
    rgb, thermal = _sources(tmp_path)
    dialog = OrthophotoPVReviewDialog(rgb, thermal)
    dialog.show()
    image = dialog.findChild(OrthophotoROIImage, 'orthophoto_pv_roi_image')
    _drag(image, (1, 1), (200, 200))
    def failed(*args, **kwargs):
        raise ValueError('synthetic local failure')
    monkeypatch.setattr(module, 'detect_orthophoto_pv_window', failed)
    dialog.findChild(QPushButton, 'orthophoto_pv_detect_button').click()
    assert dialog.proposal_result is None
    assert 'Modulprüfung nicht möglich' in dialog.findChild(QLabel, 'orthophoto_pv_status').text()
    assert dialog.findChild(QPushButton, 'orthophoto_pv_detect_button').isEnabled()
    dialog.close()
