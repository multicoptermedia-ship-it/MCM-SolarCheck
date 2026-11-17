"""Real selection/detector/draft-ID/detail/save/reopen path, synthetic sources only."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSlider
import pytest

from mcm_solarcheck.gui.thermal_partial_comparison import PartialThermalComparisonWindow
from mcm_solarcheck.gui.thermal_partial_pv import PartialThermalPVReviewDialog
from mcm_solarcheck.gui.orthophoto_pv_review import OrthophotoROIImage
from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_comparison as comparison
from test_thermal_partial_pv import module_scene
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source
from test_gui_orthophoto_pv_review import _drag


@pytest.fixture(scope='module')
def qapp():
    return QApplication.instance() or QApplication([])


def test_saved_comparison_to_roi_draft_ids_detail_review_save_and_reopen(module_scene, qapp, monkeypatch):
    _, value = module_scene
    originals = {p: p.read_bytes() for p in (value.rgb_path, value.thermal_path)}
    window = PartialThermalComparisonWindow(value)
    window.show()
    button = window.findChild(QPushButton, 'partial_comparison_pv_review')
    assert button.isEnabled()
    button.click()
    dialog = window._pv_dialog
    assert dialog.isVisible()
    assert value.label in dialog.findChild(QLabel, 'partial_pv_incomplete_notice').text()
    image = dialog.findChild(OrthophotoROIImage, 'orthophoto_pv_roi_image')
    _drag(image, (20, 20), (779, 579))
    dialog.findChild(QPushButton, 'orthophoto_pv_detect_button').click()
    assert dialog.table.rowCount() == 2
    ids = [dialog.table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(2)]
    assert all(dialog.table.item(i, 0).text().startswith("A1:M-") for i in range(2))
    assert all(':20-20-760-560:M-' in module_id for module_id in ids)
    dialog.table.cellWidget(0, 2).setCurrentIndex(1)
    dialog.table.item(0, 3).setText('Synthetic module outline inspected')
    covered = next(i for i in range(2) if dialog.table.item(i, 1).text() == '100.0')
    dialog.table.selectRow(covered)
    dialog.findChild(QPushButton, 'partial_pv_module_detail').click()
    detail = dialog._detail_dialog
    assert detail.isVisible()
    slider = detail.findChild(QSlider, 'orthophoto_thermal_opacity_slider')
    rendered = detail.findChild(QLabel, 'orthophoto_comparison_image')
    slider.setValue(0)
    a = rendered.pixmap().toImage()
    rgb = a.pixelColor(a.width()//2, a.height()//2).getRgb()
    slider.setValue(100)
    b = rendered.pixmap().toImage()
    assert rgb != b.pixelColor(b.width()//2, b.height()//2).getRgb()
    detail.close()
    dialog.findChild(QPushButton, 'partial_pv_save').click()
    assert 'lokal gespeichert' in dialog._status.text()
    saved_bytes = (value.folder / pv.STATE).read_bytes()
    dialog.close()
    monkeypatch.setattr(PartialThermalPVReviewDialog, '_detect',
        lambda *a: pytest.fail('Restore saved draft IDs without detection'))
    button.click()
    restored = window._pv_dialog
    assert restored is not dialog and restored.table.rowCount() == 2
    assert [restored.table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(2)] == ids
    assert restored.table.cellWidget(0, 2).currentData() == 'outline_ok'
    assert restored.table.item(0, 3).text() == 'Synthetic module outline inspected'
    assert restored._selection_image.selected_window == (20, 20, 760, 560)
    assert not restored._run.isEnabled()
    restored.table.item(0, 3).setText('Do not save this edit')
    restored.close()
    window.close()
    assert (value.folder / pv.STATE).read_bytes() == saved_bytes
    assert all(p.read_bytes() == data for p, data in originals.items())


def test_unreviewed_comparison_button_and_oversize_selection_cannot_run(module_scene, qapp, monkeypatch):
    _, value = module_scene
    comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='not_reviewed', note='')
    window = PartialThermalComparisonWindow(value)
    assert not window.pv.isEnabled()
    window.verdict.setCurrentIndex(1)
    assert not window.pv.isEnabled()  # The visual judgement must be saved first.
    window.save()
    assert window.pv.isEnabled()
    window.pv.click()
    dialog = window._pv_dialog
    monkeypatch.setattr(dialog, '_detect', lambda *a: pytest.fail('No oversized detection'))
    dialog._select_window((0, 0, 2049, 2))
    assert not dialog._run.isEnabled() and dialog.proposal_result is None
    assert dialog.table.rowCount() == 0
    assert not (value.folder / pv.STATE).exists()
    dialog.close()
    window.close()


def _corners(editor, polygon):
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QPoint
    col, row = editor.image.window[:2]
    for x, y in polygon:
        QTest.mouseClick(editor.image, Qt.MouseButton.LeftButton, pos=QPoint(x-col, y-row))


def test_manual_corners_cancel_correct_add_save_reopen_and_detail(module_scene, qapp, monkeypatch):
    from test_thermal_partial_pv import MANUAL, ADDED
    _, value = module_scene
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog._select_window((20, 20, 760, 560))
    dialog._run.click()
    dialog.table.cellWidget(0, 2).setCurrentIndex(2)
    dialog.table.item(0, 3).setText('Synthetic rejected partial outline')
    dialog._save()
    saved = (value.folder / pv.STATE).read_bytes()
    ids = [e['module_id'] for e in dialog.regions[dialog.current_region]['entries']]
    monkeypatch.setattr(dialog, '_detect', lambda *a: pytest.fail('No new detector'))
    dialog.table.selectRow(0)
    dialog.correct.click()
    editor = dialog._editor_dialog
    assert editor.isVisible() and value.label in editor.findChildren(QLabel)[0].text()
    _corners(editor, MANUAL)
    assert editor.image.corners == list(MANUAL)  # Native center indices, including ROI offset.
    editor.findChild(QPushButton, 'partial_pv_outline_cancel').click()
    assert dialog.regions[dialog.current_region]['entries'][0]['status'] == 'rejected'
    assert (value.folder / pv.STATE).read_bytes() == saved
    dialog.correct.click()
    editor = dialog._editor_dialog
    # Crossing corners stay in the editor; undo then finish in perimeter order.
    _corners(editor, (MANUAL[0], MANUAL[2], MANUAL[1], MANUAL[3]))
    editor.apply.click()
    assert editor.isVisible() and 'Nicht übernommen' in editor.status.text()
    for _ in range(4):
        editor.findChild(QPushButton, 'partial_pv_corner_undo').click()
    assert not editor.apply.isEnabled()
    _corners(editor, MANUAL)
    editor.apply.click()
    assert not editor.isVisible()
    assert dialog.table.cellWidget(0, 2).currentData() == 'pending'
    assert dialog.table.item(0, 3).text() == 'Synthetic rejected partial outline'
    assert dialog.regions[dialog.current_region]['entries'][0]['history'][0]['status'] == 'rejected'
    assert (value.folder / pv.STATE).read_bytes() == saved  # Accepting is not saving.
    dialog.table.cellWidget(0, 2).setCurrentIndex(1)
    dialog.add.click()
    editor = dialog._editor_dialog
    _corners(editor, ADDED)
    editor.apply.click()
    assert dialog.table.rowCount() == 3
    assert dialog.table.item(2, 0).text() == 'A1:M-0003'
    assert dialog.table.item(2, 1).text() == '100.0'
    dialog.findChild(QPushButton, 'partial_pv_module_detail').click()
    assert dialog._detail_dialog.isVisible()
    dialog._detail_dialog.close()
    dialog._save()
    assert 'lokal gespeichert' in dialog._status.text()
    dialog.close()
    monkeypatch.setattr(PartialThermalPVReviewDialog, '_detect', lambda *a: pytest.fail('No detector on reopen'))
    reopened = PartialThermalPVReviewDialog(value)
    assert reopened.table.rowCount() == 3
    assert [reopened.table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(2)] == ids
    assert reopened.table.cellWidget(0, 2).currentData() == 'outline_ok'
    assert reopened.proposal_result.proposals[0].rgb_polygon_px == MANUAL
    assert reopened.proposal_result.proposals[2].rgb_polygon_px == ADDED
    assert not reopened._run.isEnabled()
    reopened.close()


def test_manual_add_without_detector_and_close_without_saving(module_scene, qapp, monkeypatch):
    from test_thermal_partial_pv import MANUAL
    _, value = module_scene
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    assert not dialog.add.isEnabled() and not dialog.correct.isEnabled()
    dialog._select_window((20, 20, 760, 560))
    assert dialog.add.isEnabled() and not dialog.correct.isEnabled()
    monkeypatch.setattr(dialog, '_detect', lambda *a: pytest.fail('Manual path does not need detection'))
    dialog.add.click()
    editor = dialog._editor_dialog
    _corners(editor, MANUAL)
    editor.apply.click()
    assert dialog.table.rowCount() == 1 and dialog.correct.isEnabled()
    assert dialog.table.item(0, 0).text() == 'A1:M-0001'
    dialog.close()
    assert not (value.folder / pv.STATE).exists()
    reopened = PartialThermalPVReviewDialog(value)
    assert reopened.table.rowCount() == 0
    reopened.close()


@pytest.fixture(autouse=True)
def dispose_windows(qapp):
    # Exercise native close/destruction while QApplication is still alive.
    from PySide6.QtCore import QCoreApplication, QEvent
    yield
    for widget in qapp.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()
