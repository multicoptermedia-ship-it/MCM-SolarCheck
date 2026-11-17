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
    for x, y in polygon:
        point = editor.image.display_point((x, y)).toPoint()
        QTest.mouseClick(editor.image, Qt.MouseButton.LeftButton, pos=point)


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


def test_editor_centers_selected_module_resizes_zooms_pans_and_saves_native_corners(module_scene, qapp, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest
    from test_thermal_partial_pv import MANUAL
    _, value = module_scene
    originals = {p: p.read_bytes() for p in (value.rgb_path, value.thermal_path)}
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog._select_window((20, 20, 760, 560))
    dialog._run.click()
    dialog._save()
    saved = (value.folder / pv.STATE).read_bytes()
    monkeypatch.setattr(dialog, '_detect', lambda *a: pytest.fail('Display actions do not detect'))
    selected = max(range(2), key=lambda i: min(p[0] for p in dialog.proposal_result.proposals[i].rgb_polygon_px))
    dialog.table.selectRow(selected)
    module_id = dialog.table.item(selected, 0).data(Qt.ItemDataRole.UserRole)
    base = dialog._labelled_result.toImage()
    highlighted = dialog._output.pixmap().toImage()
    assert base != highlighted
    before = dialog.panes.widget(1).height()
    dialog.resize(dialog.width(), dialog.height()+150)
    qapp.processEvents()
    dialog.panes.setSizes([100, 450, 100])
    qapp.processEvents()
    assert dialog.panes.widget(1).height() > before
    for widget in (dialog,):
        assert widget.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
        assert widget.isSizeGripEnabled()
    dialog.correct.click()
    editor = dialog._editor_dialog
    qapp.processEvents()  # Initial selected-module focus after viewport layout.
    assert editor.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
    assert editor.isSizeGripEnabled() and editor.image.zoom > 1
    polygon = dialog.proposal_result.proposals[selected].rgb_polygon_px
    center = tuple(sum(p[i] for p in polygon)/len(polygon) for i in range(2))
    visible = editor.image.mapTo(editor.scroll.viewport(), editor.image.display_point(center).toPoint())
    assert editor.scroll.viewport().rect().contains(visible)
    editor.showMaximized()
    qapp.processEvents()
    assert editor.isMaximized()
    editor.showNormal()
    qapp.processEvents()
    editor.findChild(QPushButton, 'partial_pv_zoom_fit').click()
    assert editor.image.zoom <= 1
    editor.findChild(QPushButton, 'partial_pv_zoom_selected').click()
    assert editor.image.zoom > 1
    editor.findChild(QPushButton, 'partial_pv_zoom_native').click()
    assert editor.image.zoom == 1
    editor.findChild(QPushButton, 'partial_pv_zoom_in').click()
    assert editor.image.zoom > 1
    editor.findChild(QPushButton, 'partial_pv_zoom_out').click()
    assert editor.image.zoom == pytest.approx(1)
    editor._set_zoom(2.)
    _corners(editor, MANUAL[:2])
    editor._set_zoom(8., center=(620, 100))
    assert editor.image.base.width() == 760  # No zoom-sized backing raster.
    hbar = editor.scroll.horizontalScrollBar()
    vbar = editor.scroll.verticalScrollBar()
    old_h, old_v = hbar.value(), vbar.value()
    position = editor.image.display_point((620, 100)).toPoint()
    QTest.mousePress(editor.image, Qt.MouseButton.MiddleButton, pos=position)
    QTest.mouseMove(editor.image, position+QPoint(20, 10))
    QTest.mouseRelease(editor.image, Qt.MouseButton.MiddleButton, pos=position+QPoint(20, 10))
    assert (hbar.value(), vbar.value()) != (old_h, old_v)
    assert editor.image.corners == list(MANUAL[:2])  # Panning adds no corner.
    _corners(editor, MANUAL[2:])
    assert editor.image.corners == list(MANUAL)
    assert (value.folder / pv.STATE).read_bytes() == saved
    editor.apply.click()
    dialog._save()
    dialog.close()
    reopened = PartialThermalPVReviewDialog(value)
    entries = reopened.regions[reopened.current_region]['entries']
    assert entries[selected]['module_id'] == module_id
    assert entries[selected]['proposal']['rgb_polygon_px'] == MANUAL
    assert entries[selected]['status'] == 'pending'
    assert len(entries[selected]['history']) == 1
    assert all(p.read_bytes() == data for p, data in originals.items())
    reopened.close()


@pytest.mark.parametrize('zoom', [.25, 2., 8.])
def test_corner_clicks_map_to_same_native_pixels_at_different_zoom(qapp, zoom):
    import numpy as np
    from mcm_solarcheck.gui.thermal_partial_pv import ModuleCornerImage
    image = ModuleCornerImage(np.zeros((560, 760, 3), dtype=np.uint8), (20, 20, 760, 560))
    image.set_zoom(zoom)
    image.show()
    # Centers represented exactly even in the quarter-size overview.
    polygon = ((602, 62), (658, 62), (658, 138), (602, 138))
    from PySide6.QtTest import QTest
    for point in polygon:
        QTest.mouseClick(image, Qt.MouseButton.LeftButton, pos=image.display_point(point).toPoint())
    assert image.corners == list(polygon)
    image.close()


def _select_id(dialog, module_id):
    row = next(i for i in range(dialog.table.rowCount())
        if dialog.table.item(i, 0).data(Qt.ItemDataRole.UserRole) == module_id)
    dialog.table.selectRow(row)


def test_delete_two_nested_outlines_save_reopen_restore_and_keep_remaining_row_mapping(module_scene, qapp, monkeypatch):
    import rasterio
    from test_thermal_partial_pv import nested_result, ADDED
    _, value = module_scene
    originals = {p: p.read_bytes() for p in (value.rgb_path, value.thermal_path)}
    result = nested_result(value)
    region = pv.make_region(value, result)
    ids = [e['module_id'] for e in region['entries']]
    region['entries'][0].update(status='outline_ok', note='Synthetic full module stays')
    key = pv.region_key(result.rgb_window)
    pv.save_module_review(value, {key: region}, key)
    monkeypatch.setattr(PartialThermalPVReviewDialog, '_detect', lambda *a: pytest.fail('No detection on deletion or reopen'))
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    assert dialog.table.rowCount() == 3
    _select_id(dialog, ids[1])
    removed_review = dialog.table.cellWidget(1, 2)
    dialog.delete.click()
    assert dialog.table.rowCount() == 2
    assert not removed_review.isVisible()
    assert [e['module_id'] for e in pv.active_entries(dialog.regions[key])] == [ids[0], ids[2]]
    # Green/orange outline removed from its former RGB location.
    with rasterio.open(value.rgb_path) as rgb:
        color = tuple(int(v) for v in rgb.read()[:3, 240, 240])
    assert dialog._output.pixmap().toImage().pixelColor(220, 220).getRgb()[:3] == color
    _select_id(dialog, ids[2])
    dialog.table.item(1, 3).setText('Synthetic remaining nested outline')
    dialog.findChild(QPushButton, 'partial_pv_module_detail').click()
    assert any(ids[2] in label.text() for label in dialog._detail_dialog.findChildren(QLabel))
    dialog._detail_dialog.close()
    dialog.correct.click()
    assert dialog._editor_dialog.module_id == ids[2]
    dialog._editor_dialog.reject()
    dialog.delete.click()
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).data(Qt.ItemDataRole.UserRole) == ids[0]
    assert dialog.table.cellWidget(0, 2).currentData() == 'outline_ok'
    assert dialog.table.item(0, 3).text() == 'Synthetic full module stays'
    assert dialog.deleted.count() == 3  # Placeholder plus two deleted IDs.
    dialog._save()
    dialog.close()
    reopened = PartialThermalPVReviewDialog(value)
    reopened.show()
    assert reopened.table.rowCount() == 1 and not reopened._run.isEnabled()
    assert len(reopened.proposal_result.proposals) == 1
    assert reopened.deleted.findData(ids[1]) > 0 and reopened.deleted.findData(ids[2]) > 0
    # New additions reserve both deleted IDs, and row actions target the right ID.
    reopened.add.click()
    editor = reopened._editor_dialog
    _corners(editor, ADDED)
    editor.apply.click()
    assert reopened.table.item(1, 0).text() == 'A1:M-0004'
    reopened.table.item(1, 3).setText('Synthetic added module after deletions')
    reopened.correct.click()
    assert reopened._editor_dialog.module_id.endswith(':M-0004')
    reopened._editor_dialog.reject()
    reopened.deleted.setCurrentIndex(reopened.deleted.findData(ids[2]))
    assert reopened.restore.isEnabled()
    reopened.restore.click()
    assert [e['module_id'] for e in pv.active_entries(reopened.regions[key])] == [ids[0], ids[2],
        reopened.regions[key]['entries'][-1]['module_id']]
    assert reopened.table.item(1, 3).text() == 'Synthetic remaining nested outline'
    assert reopened.table.item(2, 3).text() == 'Synthetic added module after deletions'
    reopened._save()
    reopened.close()
    final = PartialThermalPVReviewDialog(value)
    assert final.table.rowCount() == 3
    assert final.deleted.findData(ids[1]) > 0 and final.deleted.findData(ids[2]) == -1
    assert all(p.read_bytes() == data for p, data in originals.items())
    final.close()


def test_delete_all_close_without_save_then_save_empty_and_restore(module_scene, qapp, monkeypatch):
    from test_thermal_partial_pv import nested_result
    _, value = module_scene
    result = nested_result(value)
    region = pv.make_region(value, result)
    key = pv.region_key(result.rgb_window)
    pv.save_module_review(value, {key: region}, key)
    saved = (value.folder / pv.STATE).read_bytes()
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog.delete.click()
    dialog.close()
    assert (value.folder / pv.STATE).read_bytes() == saved
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    assert dialog.table.rowCount() == 3
    monkeypatch.setattr(dialog, '_detect', lambda *a: pytest.fail('Empty saved result must not re-detect'))
    for _ in range(3):
        dialog.delete.click()
    assert dialog.table.rowCount() == 0 and not dialog.proposal_result.proposals
    assert not dialog.delete.isEnabled() and not dialog.correct.isEnabled() and dialog.add.isEnabled()
    dialog._save()
    dialog.close()
    reopened = PartialThermalPVReviewDialog(value)
    reopened.show()
    assert reopened.table.rowCount() == 0 and not reopened._run.isEnabled()
    assert reopened.deleted.count() == 4
    reopened.deleted.setCurrentIndex(1)
    restored_id = reopened.deleted.currentData()
    reopened.restore.click()
    assert reopened.table.rowCount() == 1
    assert reopened.table.item(0, 0).data(Qt.ItemDataRole.UserRole) == restored_id
    reopened.close()
