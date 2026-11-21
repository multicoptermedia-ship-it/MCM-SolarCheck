"""Local learning preparation through the saved module editor; no real images."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from mcm_solarcheck.gui.thermal_partial_pv import PartialThermalPVReviewDialog
from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_training as learning
from test_thermal_partial_training import reviewed
from test_thermal_partial_pv import module_scene
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source
from test_gui_thermal_partial_pv import qapp, dispose_windows


def test_prepare_save_reopen_stale_and_unsaved_edits_through_module_editor(module_scene, qapp, monkeypatch):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    originals = {p: p.read_bytes() for p in (value.rgb_path, value.thermal_path, value.folder / pv.STATE)}
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    monkeypatch.setattr(dialog, '_detect', lambda *a: pytest.fail('No new detection'))
    assert dialog.learning.isEnabled()
    dialog.learning.click()
    prep = dialog._learning_dialog
    assert prep.isVisible() and not prep.save.isEnabled()
    assert value.label in prep.findChildren(type(prep.status))[0].text()
    prep.group.setText('Synthetic plant A')
    prep.reviewer.setText('Synthetic reviewer')
    assert not prep.save.isEnabled()  # Outline reviews alone do not assert completeness.
    prep.complete.setChecked(True)
    assert prep.save.isEnabled()
    prep.save.click()
    assert 'lokal gespeichert' in prep.status.text()
    assert 'Datenteil:' in prep.status.text()
    assert 'kein vollständiger Trainingsdatensatz' in prep.status.text()
    before = (value.folder / learning.STATE).read_bytes()
    prep.close()
    dialog.close()
    assert all(p.read_bytes() == data for p, data in originals.items())
    monkeypatch.setattr(PartialThermalPVReviewDialog, '_detect', lambda *a: pytest.fail('Reopen without inference'))
    reopened = PartialThermalPVReviewDialog(value)
    reopened.show()
    reopened.learning.click()
    restored = reopened._learning_dialog
    assert restored.complete.isChecked() and restored.group.isReadOnly()
    assert 'lokal gespeichert' in restored.status.text()
    restored.reviewer.setText('Not saved')
    restored.close()
    assert (value.folder / learning.STATE).read_bytes() == before
    # Main editor unsaved changes cannot be silently acknowledged as training labels.
    reopened.table.item(0, 3).setText('Synthetic updated outline note')
    previous_dialog = reopened._learning_dialog
    reopened.learning.click()
    assert reopened._learning_dialog is previous_dialog
    assert 'lokal speichern' in reopened._status.text()
    reopened._save()
    reopened.learning.click()
    stale = reopened._learning_dialog
    assert 'veraltet' in stale.status.text() and not stale.complete.isChecked()
    assert not stale.save.isEnabled()
    stale.complete.setChecked(True)
    stale.save.click()
    assert 'lokal gespeichert' in stale.status.text()
    stale.revoke.click()
    assert 'zurückgenommen' in stale.status.text()
    assert not stale.complete.isChecked() and not stale.save.isEnabled()
    assert learning.read_learning_preparation(value, key)['entry'] is None
    stale.close()
    reopened.close()


def test_close_without_saving_and_pending_review_never_prepare_labels(module_scene, qapp):
    _, value = module_scene
    key, region = reviewed(value)
    region['entries'][0]['status'] = 'pending'
    pv.save_module_review(value, {key: region}, key)
    dialog = PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog.learning.click()
    prep = dialog._learning_dialog
    assert 'offenen Umrisse' in prep.status.text()
    prep.group.setText('Synthetic')
    prep.reviewer.setText('Synthetic')
    prep.complete.setChecked(True)
    assert not prep.save.isEnabled()
    prep.close()
    assert not (value.folder / learning.STATE).exists()
    dialog.table.cellWidget(0, 2).setCurrentIndex(1)
    dialog._save()
    dialog.learning.click()
    ready = dialog._learning_dialog
    ready.group.setText('Synthetic')
    ready.reviewer.setText('Synthetic')
    ready.complete.setChecked(True)
    assert ready.save.isEnabled()
    ready.close()
    dialog.close()
    assert not (value.folder / learning.STATE).exists()
