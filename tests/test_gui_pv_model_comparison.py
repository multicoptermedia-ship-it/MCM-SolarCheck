"""Qt -> isolated real CPU neural test graph -> local comparison -> reopen/cancel."""
import time
import pytest
pytest.importorskip('onnx')
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QFileDialog, QLabel
from PySide6.QtTest import QTest

from mcm_solarcheck.gui.thermal_partial_pv import PartialThermalPVReviewDialog
from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_model_comparison as evaluation
from test_pv_onnx_evaluation import model_manifest
from test_gui_thermal_partial_pv import qapp, dispose_windows
from test_thermal_partial_pv import module_scene
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source


def reviewed(value):
    result=pv.detect_partial_pv_window(value,window=(20,20,760,560))
    region=pv.make_region(value,result)
    for e in region['entries']:e['status']='outline_ok'
    key=pv.region_key(result.rgb_window)
    pv.save_module_review(value,{key:region},key)


def wait_finished(dialog):
    deadline=time.monotonic()+45
    while (dialog._model_process.state()!=QProcess.ProcessState.NotRunning or dialog._model_pending is not None) and time.monotonic()<deadline:
        QTest.qWait(30)
    assert dialog._model_process.state()==QProcess.ProcessState.NotRunning
    assert dialog._model_pending is None


def test_actual_gui_worker_model_overlay_reopen_without_model_and_cancel_preserve_sources(module_scene,model_manifest,qapp,monkeypatch):
    source,value=module_scene
    reviewed(value)
    originals={p:p.read_bytes() for p in (value.rgb_path,value.thermal_path,value.folder/pv.STATE,source/'job.json')}
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(model_manifest),''))
    dialog=PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog.model_start.click()
    wait_finished(dialog)
    assert dialog._model_process.exitCode()==0
    result=dialog._model_dialog
    assert result is not None and result.isVisible()
    assert any(value.label in label.text() for label in result.findChildren(QLabel))
    assert 'wiedergefunden: 1' in result.findChild(QLabel,'orthophoto_pv_help').text()
    saved=(value.folder/evaluation.STATE).read_bytes()
    result.close()
    model_manifest.write_text('{}')
    dialog.model_open.click()
    assert dialog._model_dialog is not result and dialog._model_dialog.isVisible()
    dialog._model_dialog.close()
    # Failure never replaces the previous successful comparison or human review.
    dialog.model_start.click()
    wait_finished(dialog)
    assert dialog._model_process.exitCode()==2
    assert (value.folder/evaluation.STATE).read_bytes()==saved
    # Cancellation kills only this worker, discards staging, keeps old result.
    dialog.model_start.click()
    dialog._cancel_model_comparison()
    wait_finished(dialog)
    assert (value.folder/evaluation.STATE).read_bytes()==saved
    assert not list(value.folder.glob('pv-model-comparison-*.LOCAL.json'))
    assert all(p.read_bytes()==data for p,data in originals.items())
    dialog.close()


def test_unsaved_reference_and_file_selection_cancel_do_not_start_worker(module_scene,qapp,monkeypatch):
    _,value=module_scene
    reviewed(value)
    dialog=PartialThermalPVReviewDialog(value)
    dialog.show()
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:pytest.fail('Save references first'))
    dialog.table.item(0,3).setText('unsaved synthetic note')
    dialog.model_start.click()
    assert dialog._model_process is None and 'speichern' in dialog._status.text()
    dialog._save()
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:('',''))
    dialog.model_start.click()
    assert dialog._model_process is None and not (value.folder/evaluation.STATE).exists()
    dialog.close()


@pytest.mark.parametrize('finish', ['timeout','close'])
def test_timeout_and_window_close_discard_staging_without_losing_saved_review(module_scene,model_manifest,qapp,monkeypatch,finish):
    _,value=module_scene
    reviewed(value)
    saved=(value.folder/pv.STATE).read_bytes()
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(model_manifest),''))
    dialog=PartialThermalPVReviewDialog(value)
    dialog.show()
    dialog.model_start.click()
    if finish=='timeout': dialog._model_timer.timeout.emit()
    else: dialog.close()
    wait_finished(dialog)
    assert (value.folder/pv.STATE).read_bytes()==saved
    assert not (value.folder/evaluation.STATE).exists()
    assert not list(value.folder.glob('pv-model-comparison-*.LOCAL.json'))
    dialog.close()
