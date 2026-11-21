"""Visible unknown-corner exclusions and safe aggregate-only mask clipboard."""
import json
import pytest

from PySide6.QtWidgets import QLabel, QPushButton, QDialog
from mcm_solarcheck.gui import thermal_partial_training as view

from mcm_solarcheck.gui.thermal_partial_pv import PartialThermalPVReviewDialog
from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_training as learning
from test_thermal_partial_training import reviewed, save
from test_learning_ignore_masks import area_for
from test_thermal_partial_pv import module_scene
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source
from test_gui_thermal_partial_pv import qapp, dispose_windows, _corners


def mark(prep, region, qapp):
    prep.findChild(QPushButton, 'pv_learning_ignore_add').click()
    editor = prep._area_editor
    qapp.processEvents()
    col, row = region['window'][:2]
    _corners(editor, [(x+col, y+row) for x, y in area_for(region)])
    assert editor.learning_ignore and 'unklaren bereich' in editor.windowTitle().lower()
    editor.apply.click()
    return editor


def test_unknown_corners_area_preview_copy_save_reopen_and_remove(module_scene, qapp):
    _, value = module_scene
    key, region = reviewed(value)
    region['entries'][0]['status'] = 'pending'
    pv.save_module_review(value, {key: region}, key)
    module_bytes = (value.folder/pv.STATE).read_bytes()
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog.learning.click()
    prep = dialog._learning_dialog
    prep.group.setText('Synthetic plant A')
    prep.reviewer.setText('Synthetic reviewer')
    assert not prep.preview.isEnabled()
    mark(prep, region, qapp)
    assert len(prep.ignore_areas) == 1 and prep.preview.isEnabled()
    assert '1 ausgewählte Modulflächen' in prep.summary.text()
    assert not prep.complete.isChecked() and not prep.save.isEnabled()
    prep.preview.click()
    mask = prep._mask_dialog
    assert mask.isVisible() and value.label in mask.findChildren(QLabel)[0].text()
    assert mask.findChild(QLabel, 'pv_learning_mask_native').pixmap().width() == region['window'][2]
    assert mask.findChild(QLabel, 'pv_learning_mask_candidate').pixmap().width() == 480
    mask.findChild(QPushButton, 'pv_learning_copy_counts').click()
    copied = json.loads(qapp.clipboard().text())
    assert copied['module_outlines'] == 1 and copied['ignored_outlines'] == 1
    assert copied['native_pixels']['ignored'] > 0
    assert copied['training_started'] is False
    assert 'Synthetic' not in qapp.clipboard().text() and str(value.rgb_path) not in qapp.clipboard().text()
    mask.close()
    prep.complete.setChecked(True)
    prep.save.click()
    assert 'lokal gespeichert' in prep.status.text()
    stored = (value.folder/learning.STATE).read_bytes()
    prep.close()
    dialog.learning.click()
    restored = dialog._learning_dialog
    assert restored.complete.isChecked() and len(restored.ignore_areas) == 1
    restored.remove.click()
    assert not restored.complete.isChecked()
    assert not restored.preview.isEnabled() and 'offenen Umrisse' in restored.status.text()
    restored.close()
    dialog.close()
    assert (value.folder/pv.STATE).read_bytes() == module_bytes
    assert (value.folder/learning.STATE).read_bytes() == stored


def test_cancel_area_and_unsaved_exclusion_edits_preserve_previous_state(module_scene, qapp):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    save(value, key)
    before = (value.folder/learning.STATE).read_bytes()
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog.learning.click()
    prep = dialog._learning_dialog
    prep.findChild(QPushButton, 'pv_learning_ignore_add').click()
    editor = prep._area_editor
    qapp.processEvents()
    _corners(editor, [(80, 80), (200, 80)])
    editor.reject()
    assert prep.ignore_areas == [] and prep.complete.isChecked()
    mark(prep, region, qapp)
    assert not prep.complete.isChecked()
    prep.close()
    dialog.close()
    assert (value.folder/learning.STATE).read_bytes() == before


def test_legacy_saved_completion_is_not_silently_approved_for_new_ignore_policy(module_scene, qapp):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    save(value, key)
    path = value.folder/learning.STATE
    record = json.loads(path.read_text(encoding='utf-8'))
    record['check'] = learning.LEGACY_CHECK
    entry = record['regions'][key]
    for field in ('mask_policy', 'user_ignore_polygons_px', 'ignore_polygons_px', 'ignored_draft_ids'):
        del entry['manifest'][field]
    entry['snapshot_id'] = learning._digest(entry['manifest'])
    path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
    before = path.read_bytes()
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog.learning.click()
    prep = dialog._learning_dialog
    assert 'Bisherige Vorbereitung geladen' in prep.status.text()
    assert not prep.complete.isChecked() and not prep.save.isEnabled()
    assert prep.preview.isEnabled()
    prep.preview.click()
    assert prep._mask_dialog.isVisible()
    prep._mask_dialog.close()
    prep.close()
    dialog.close()
    assert path.read_bytes() == before


def test_failed_preparation_load_can_still_close_parent_owned_dialog(qapp, monkeypatch):
    parent = QDialog()
    def fail(*args):
        raise ValueError('Synthetic unavailable preparation')
    monkeypatch.setattr(view, 'read_learning_preparation', fail)
    with pytest.raises(ValueError, match='Synthetic unavailable'):
        view.LearningPreparationDialog(None, 'synthetic', parent)
    partial = parent.findChildren(view.LearningPreparationDialog)[0]
    partial.close()  # The failed constructor must not make closeEvent unsafe.
    parent.close()
