"""Isolated pilot boundaries, synthetic masks and exact public artifact checks."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from mcm_solarcheck.vision import pv_hawk_module_detector as hawk

ROOT=Path(__file__).resolve().parents[1]


def script_module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def manifest(tmp_path):
    spec=hawk.specification()
    path=tmp_path/'pv-hawk-rgb.LOCAL.json'
    path.write_text(json.dumps(dict(profile=hawk.PROFILE,evaluation_allowed=True,
        production_approved=False,source_commit=spec['source_commit'],weights_sha256=spec['weights_sha256'])))
    return path


@pytest.mark.parametrize('key,value',[('evaluation_allowed',False),('production_approved',True),
    ('source_commit','other'),('weights_sha256','0'*64),('profile','other')])
def test_only_pinned_evaluation_manifest_before_tensorflow_import(manifest,key,value):
    before=set(sys.modules)
    record=json.loads(manifest.read_text());record[key]=value;manifest.write_text(json.dumps(record))
    with pytest.raises(ValueError):hawk.validate_manifest(manifest)
    assert not any(m.startswith('tensorflow') for m in set(sys.modules)-before)


def test_manifest_cannot_select_arbitrary_runtime_command(manifest):
    root=manifest.parent
    record=json.loads(manifest.read_text());record['python']='arbitrary-program';manifest.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='Umgebung fehlt'):hawk.evaluation_python(manifest)
    binary=root/('env/Scripts/python.exe' if sys.platform=='win32' else 'env/bin/python')
    binary.parent.mkdir(parents=True);binary.write_bytes(b'test executable placeholder')
    assert hawk.evaluation_python(manifest)==str(binary)


def test_hash_failure_rejected_and_all_sources_checked_before_import(tmp_path,manifest,monkeypatch):
    p=tmp_path/'source.py';p.write_bytes(b'altered')
    with pytest.raises(ValueError):hawk.checked_bytes(p,dict(bytes=7,sha256='0'*64))
    real_model=hawk._model
    monkeypatch.setattr(hawk,'_model',lambda *a:pytest.fail('No code before weight verification'))
    with pytest.raises(ValueError):hawk.PVHawkModuleDetector(manifest)
    # _model checks the entire source subset before importing TensorFlow.
    with pytest.raises(ValueError):real_model(tmp_path,hawk.specification())


def test_masks_native_coordinates_one_instance_and_fragment_rejection():
    masks=np.zeros((80,120,3),bool)
    masks[20:50,30:90,0]=True
    masks[10:20,10:20,1]=True;masks[60:70,100:110,1]=True
    masks[1:10,1:10,2]=True
    result=dict(masks=masks,scores=np.array([.9,.95,.6]),class_ids=np.ones(3))
    found=hawk.mask_detections(result,(80,120,3))
    assert len(found)==1 and found[0].confidence==.9
    assert set(found[0].polygon_px)=={(30.,20.),(89.,20.),(89.,49.),(30.,49.)}
    result['scores'][0]=np.nan
    with pytest.raises(ValueError):hawk.mask_detections(result,(80,120,3))


def test_native_bgr_to_rgb_and_source_preservation_without_model_loading():
    class Model:
        def detect(self,images,verbose):
            assert images[0][0,0].tolist()==[3,2,1]
            return [dict(masks=np.zeros((30,40,0),bool),scores=np.array([]),class_ids=np.array([]))]
    detector=hawk.PVHawkModuleDetector.__new__(hawk.PVHawkModuleDetector)
    detector.model=Model();detector._check_weights=lambda:None
    image=np.full((30,40,3),[1,2,3],np.uint8);before=image.copy()
    assert detector.detect_array(image)==()
    assert np.array_equal(image,before)


def test_explicit_download_hash_atomic_failure_and_reuse(tmp_path,monkeypatch):
    setup=script_module('MCM_SolarCheck_PV_HAWK_SETUP')
    content=b'public synthetic artifact';check=dict(bytes=len(content),sha256=sha256(content).hexdigest())
    from io import BytesIO
    monkeypatch.setattr(setup.urllib.request,'urlopen',lambda *a,**k:BytesIO(content))
    target=tmp_path/'weights.h5';setup.download('https://example.invalid/artifact',target,check)
    assert target.read_bytes()==content
    monkeypatch.setattr(setup.urllib.request,'urlopen',lambda *a,**k:pytest.fail('Reuse checked file'))
    setup.download('https://example.invalid/artifact',target,check)
    target.write_bytes(b'old artifact')
    monkeypatch.setattr(setup.urllib.request,'urlopen',lambda *a,**k:BytesIO(b'corrupt'))
    with pytest.raises(ValueError):setup.download('https://example.invalid/artifact',target,check)
    assert target.read_bytes()==b'old artifact' and not list(tmp_path.glob('*.download'))


def test_setup_refuses_nonpilot_target_without_process_or_mutation(tmp_path,monkeypatch):
    setup=script_module('MCM_SolarCheck_PV_HAWK_SETUP');existing=tmp_path/'original.db';existing.write_bytes(b'keep')
    monkeypatch.setattr(setup.subprocess,'check_output',lambda *a,**k:pytest.fail('No process for invalid target'))
    with pytest.raises(ValueError,match='nicht leer'):setup.setup(tmp_path,Path(sys.executable))
    assert existing.read_bytes()==b'keep' and len(list(tmp_path.iterdir()))==1


def test_worker_python310_digest_compatibility(monkeypatch):
    import hashlib
    from io import BytesIO
    worker=script_module('MCM_SolarCheck_PV_MODELLVERGLEICH')
    monkeypatch.delattr(hashlib,'file_digest',raising=False)
    worker.prepare_runtime()
    assert hashlib.file_digest(BytesIO(b'abc'),'sha256').hexdigest()==hashlib.sha256(b'abc').hexdigest()


def prediction_outputs():
    probabilities=np.array([[[.05,.95],[.4,.6],[.8,.2],[.01,.99]]],np.float32)
    boxes=np.array([[[.1,.1,.2,.2],[.3,.1,.4,.2],[.5,.1,.6,.2],[0,0,0,0]]],np.float32)
    instances=np.zeros((1,200,6),np.float32);instances[0,:2,4]=1
    return [instances,probabilities,None,None,boxes,None,None]


def test_network_counts_exclude_padding_and_never_return_private_tensors():
    counts=hawk.network_counts(prediction_outputs())
    assert counts==dict(region_proposals=3,foreground_regions=2,regions_at_070=1,regions_at_090=1,
        maximum_region_score=.95,post_nms_instances=2)
    assert all(value is None or type(value) in (int,float) for value in counts.values())
    outputs=prediction_outputs();outputs[1][0,0,0]=np.nan
    with pytest.raises(ValueError):hawk.network_counts(outputs)


def test_each_mask_exclusion_is_counted_without_weakening_existing_filters():
    masks=np.zeros((80,120,5),bool)
    masks[20:50,30:90,0]=True
    masks[10:20,10:20,1]=True;masks[60:70,100:110,1]=True
    masks[10:20,10:20,2]=True
    masks[10,10,3]=True
    masks[10:20,10:20,4]=True
    result=dict(masks=masks,scores=np.array([.9,.9,.6,.9,.9]),class_ids=np.array([1,1,1,1,0]))
    counts={};found=hawk.mask_detections(result,(80,120,3),diagnostics=counts)
    assert len(found)==1
    assert counts==dict(returned_instances=5,rejected_class_or_score=2,rejected_fragmented_mask=1,
        rejected_empty_or_small_mask=1,rejected_boundary=0,accepted_outlines=1)


@pytest.mark.parametrize('fail',[False,True])
def test_observer_uses_one_prediction_and_restores_model_after_failure(fail):
    class Graph:
        def __init__(self):self.calls=0
        def predict(self,*args,**kwargs):
            self.calls+=1
            if fail:raise RuntimeError('synthetic failure')
            return prediction_outputs()
    class Model:
        def __init__(self):self.keras_model=Graph()
        def detect(self,images,verbose):
            self.keras_model.predict(images,verbose=0)
            return [dict(masks=np.zeros((30,40,0),bool),scores=np.array([]),class_ids=np.array([]))]
    detector=hawk.PVHawkModuleDetector.__new__(hawk.PVHawkModuleDetector)
    detector.model=Model();detector._check_weights=lambda:None
    before=detector.model.keras_model.predict
    if fail:
        with pytest.raises(RuntimeError):detector.detect_array(np.zeros((30,40,3),np.uint8))
    else:
        assert detector.detect_array(np.zeros((30,40,3),np.uint8))==()
        assert detector.last_diagnostics['network']['regions_at_070']==1
    assert detector.model.keras_model.calls==1 and detector.model.keras_model.predict==before
