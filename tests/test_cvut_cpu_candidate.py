"""Candidate gates, two-class masks and preservation of the existing result."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QLabel

from test_gui_thermal_partial_pv import qapp, dispose_windows
from test_thermal_partial_pv import module_scene
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source

from mcm_solarcheck.vision import cvut_module_detector as cvut
from mcm_solarcheck.services import thermal_partial_model_comparison as evaluation


@pytest.fixture
def cvut_manifest(tmp_path):
    root = tmp_path/'cvut';root.mkdir()
    spec = cvut.specification()
    manifest = root/'cvut-rgb.LOCAL.json'
    manifest.write_text(json.dumps(dict(profile=cvut.PROFILE, source_commit=spec['source_commit'],
        weights_sha256=spec['weights_sha256'], evaluation_allowed=True, production_approved=False)))
    return manifest


def test_manifest_and_own_interpreter_only(cvut_manifest):
    from sys import platform
    root, _, spec = cvut.validate_manifest(cvut_manifest)
    with pytest.raises(ValueError):cvut.evaluation_python(cvut_manifest)
    python = root/('env/Scripts/python.exe' if platform=='win32' else 'env/bin/python')
    python.parent.mkdir(parents=True);python.write_bytes(b'synthetic executable placeholder')
    assert cvut.evaluation_python(cvut_manifest)==str(python)
    data=json.loads(cvut_manifest.read_text());data['production_approved']=True
    cvut_manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):cvut.validate_manifest(cvut_manifest)


def test_candidate_components_preserve_native_pixel_centers_and_reject_boundary():
    spec=cvut.specification();p=np.zeros((270,480),np.float32)
    p[40:71,80:141]=.9;p[140:171,280:341]=.95;p[0:20,400:430]=.99
    detections=cvut.components(p,(540,960,3),spec)
    assert len(detections)==2
    points=np.array(detections[0].polygon_px)
    assert np.allclose(points.min(axis=0),(160.5,80.5))
    assert np.allclose(points.max(axis=0),(280.5,140.5))
    assert all(.89<=d.confidence<=.96 for d in detections)
    p[50,50]=np.nan
    with pytest.raises(ValueError):cvut.components(p,(540,960,3),spec)


def test_cvut_result_does_not_overwrite_baseline_and_reopens_without_model(
        module_scene,cvut_manifest,monkeypatch):
    from test_gui_pv_model_comparison import reviewed
    source,value=module_scene
    reviewed(value)
    from mcm_solarcheck.services.thermal_partial_pv import load_module_review
    _,key=load_module_review(value)
    baseline=value.folder/evaluation.STATE;baseline.write_text('synthetic baseline preserved')
    originals={p:p.read_bytes() for p in (value.rgb_path,value.thermal_path,baseline)}
    class Candidate:
        def __init__(self,path):
            self.name='synthetic CVUT fixture'
            self.description=dict(profile=cvut.PROFILE,provider='CVUT synthetic',model_version='fixture',
                preprocessing='cvut-rgb-unit-480x270-candidate-1',production_approved=False,
                preprocessing_verified=False,class_mapping_verified=False)
        def detect_array(self,image):return ()
    monkeypatch.setattr(cvut,'CVUTModuleDetector',Candidate)
    record=evaluation.compare_saved_region(source,cvut_manifest,key)
    assert (value.folder/evaluation.CVUT_STATE).exists()
    assert all(p.read_bytes()==b for p,b in originals.items())
    monkeypatch.setattr(cvut,'CVUTModuleDetector',lambda *a:pytest.fail('No inference on reopen'))
    assert evaluation.read_model_comparison(value,value.folder/evaluation.CVUT_STATE)[0]==json.loads(json.dumps(record))
    assert evaluation.shareable_counts(record)['input_profile']=='cvut-rgb-unit-480x270-candidate-1'
    assert all(record[k] is False for k in (*evaluation.FLAGS,*evaluation.EXTRA_FLAGS))


def test_extract_public_rgb_does_not_replace_wrong_existing_weights(tmp_path,monkeypatch):
    import zipfile
    script=Path(__file__).resolve().parents[1]/'scripts/MCM_SolarCheck_CVUT_CPU_PILOT.py'
    import sys
    monkeypatch.syspath_prepend(str(script.parent))
    s=importlib.util.spec_from_file_location('cvut_setup',script);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    archive=tmp_path/'public.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('rgb.pth',b'synthetic public fixture')
    prefix=tmp_path/'pilot';prefix.mkdir()
    from hashlib import sha256
    spec=dict(archive_bytes=archive.stat().st_size,archive_sha256=m.digest(archive),weights='rgb.pth',
              weights_bytes=24,weights_sha256=sha256(b'synthetic public fixture').hexdigest())
    m.extract_rgb(archive,prefix,spec)
    assert (prefix/'rgb.pth').read_bytes()==b'synthetic public fixture'
    m.extract_rgb(archive,prefix,spec)
    (prefix/'rgb.pth').write_bytes(b'wrong')
    with pytest.raises(ValueError):m.extract_rgb(archive,prefix,spec)
    assert (prefix/'rgb.pth').read_bytes()==b'wrong'


def test_gui_cvut_choice_and_baseline_preserved(module_scene,cvut_manifest,qapp,monkeypatch,dispose_windows):
    from test_gui_pv_model_comparison import reviewed
    from mcm_solarcheck.gui.thermal_partial_pv import PartialThermalPVReviewDialog
    from PySide6.QtWidgets import QInputDialog
    source,value=module_scene
    reviewed(value)
    from mcm_solarcheck.services.thermal_partial_pv import load_module_review
    _,key=load_module_review(value)
    class Candidate:
        name='synthetic CVUT fixture'
        description=dict(profile=cvut.PROFILE,provider='CVUT fixture',model_version='synthetic',production_approved=False)
        def __init__(self,path):pass
        def detect_array(self,image):return ()
    monkeypatch.setattr(cvut,'CVUTModuleDetector',Candidate)
    record=evaluation.compare_saved_region(source,cvut_manifest,key)
    baseline=value.folder/evaluation.STATE;baseline.write_text('untouched fixture baseline')
    before=baseline.read_bytes()
    dialog=PartialThermalPVReviewDialog(value);dialog.show()
    monkeypatch.setattr(QInputDialog,'getItem',lambda *a,**k:('CVUT-Kandidat',True))
    dialog.model_open.click()
    assert dialog._model_dialog is not None and dialog._model_dialog.isVisible()
    assert 'Experimenteller CVUT-Kandidat' in dialog._model_dialog.findChild(
        QLabel,'partial_pv_diagnostics').text()
    assert dialog._model_dialog._record==json.loads(json.dumps(record)) and baseline.read_bytes()==before
    dialog.close()


def test_gui_cvut_uses_own_worker_and_cancel_keeps_previous(module_scene,cvut_manifest,qapp,monkeypatch,dispose_windows):
    import sys
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import QFileDialog
    from test_gui_pv_model_comparison import reviewed
    from mcm_solarcheck.gui.thermal_partial_pv import PartialThermalPVReviewDialog
    source,value=module_scene;reviewed(value)
    python=cvut_manifest.parent/('env/Scripts/python.exe' if sys.platform=='win32' else 'env/bin/python')
    python.parent.mkdir(parents=True);python.write_bytes(b'placeholder never executed')
    baseline=value.folder/evaluation.STATE;baseline.write_text('preserve baseline')
    calls=[]
    monkeypatch.setattr(QProcess,'start',lambda self,program,args:calls.append((program,args)))
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(cvut_manifest),''))
    dialog=PartialThermalPVReviewDialog(value);dialog.show();dialog.model_start.click()
    assert calls[0][0]==str(python) and str(source) in calls[0][1]
    dialog._model_cancelled=True
    dialog._model_finished(2,QProcess.ExitStatus.CrashExit)
    assert baseline.read_text()=='preserve baseline'
    assert not list(value.folder.glob('pv-model-comparison-*.LOCAL.json'))
    dialog.close()


def test_failed_setup_probe_retains_previous_manifest_and_report(tmp_path,monkeypatch):
    import shutil
    import subprocess
    import zipfile
    script=Path(__file__).resolve().parents[1]/'scripts/MCM_SolarCheck_CVUT_CPU_PILOT.py'
    monkeypatch.syspath_prepend(str(script.parent))
    loader=importlib.util.spec_from_file_location('cvut_setup_failure',script)
    setup=importlib.util.module_from_spec(loader);loader.loader.exec_module(setup)
    root=tmp_path/'pilot';root.mkdir()
    (root/'cvut-cpu-pilot.json').write_text(json.dumps({'check':setup.MARKER}))
    previous=root/setup.MANIFEST;previous.write_text('last manifest unchanged')
    report=root/setup.PROBE_REPORT;report.write_text('last probe unchanged')
    archive=tmp_path/'public.zip'
    data=b'synthetic public fixture'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('rgb.pth',data)
    from hashlib import sha256
    spec=dict(cvut.specification(),archive_bytes=archive.stat().st_size,archive_sha256=setup.digest(archive),
              weights='rgb.pth',weights_bytes=len(data),weights_sha256=sha256(data).hexdigest(),sources={})
    config=tmp_path/'spec.json';config.write_text(json.dumps(spec));monkeypatch.setattr(setup,'SPEC',config)
    monkeypatch.setattr(shutil,'disk_usage',lambda p:type('Space',(),{'free':8*1024**3})())
    calls=[]
    def run(args,**kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args,2 if '--probe' in args else 0,stdout=b'',stderr=b'')
    monkeypatch.setattr(subprocess,'run',run)
    with pytest.raises(ValueError,match='CPU-Probe'):setup.setup(root,archive)
    assert previous.read_text()=='last manifest unchanged' and report.read_text()=='last probe unchanged'
    assert not (root/setup.PROBE_MANIFEST).exists()
    assert all(str(root/'env') in args[0] for args in calls if '-m' in args and 'pip' in args)
