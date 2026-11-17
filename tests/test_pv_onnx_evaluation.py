"""Real OpenCV neural inference on a synthetic contract graph, never a trained PV model."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
onnx = pytest.importorskip('onnx')
from onnx import helper, numpy_helper, TensorProto

from mcm_solarcheck.vision.onnx_module_detector import OnnxModuleDetector, PROFILE
from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_model_comparison as evaluation
from mcm_solarcheck.services.thermal_partial_comparison import FLAGS
from test_thermal_partial_pv import module_scene
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source


def synthetic_model(folder):
    """Small input-connected NN graph with fixed outputs; no training claim."""
    nodes = [helper.make_node('GlobalAveragePool', ['image'], ['pooled'])]
    initializers, outputs = [], []
    for name, data in (
        ('boxes', np.array([[.10, .22, .22, .31], [.70, .70, .8, .8]], np.float32)),
        ('scores', np.array([.9, .8], np.float32)),
        ('masks', np.ones((2, 28, 28), np.float32))):
        flat = data.reshape(-1)
        initializers += [numpy_helper.from_array(np.zeros((len(flat), 3, 1, 1), np.float32), name+'w'),
            numpy_helper.from_array(flat, name+'b'), numpy_helper.from_array(np.asarray(data.shape, np.int64), name+'shape')]
        nodes += [helper.make_node('Conv', ['pooled', name+'w', name+'b'], [name+'raw'], kernel_shape=[1, 1]),
            helper.make_node('Reshape', [name+'raw', name+'shape'], [name])]
        outputs.append(helper.make_tensor_value_info(name, TensorProto.FLOAT, list(data.shape)))
    graph = helper.make_graph(nodes, 'SYNTHETIC_CONTRACT_NOT_TRAINED_PV',
        [helper.make_tensor_value_info('image', TensorProto.FLOAT, [1, 3, 64, 64])], outputs, initializers)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)], ir_version=8)
    path = folder/'synthetic.onnx'
    path.write_bytes(model.SerializeToString())
    record = dict(profile=PROFILE, weights=path.name, input_size=64, evaluation_allowed=True,
        task='pv_module_instance_segmentation', classes=['pv_module'],
        production_approved=False, code_license='MIT', reviewer='synthetic test fixture',
        rights_evidence='generated tensors only; no external weights/data',
        model=dict(provider='synthetic-contract', model_version='1', modality='rgb', dataset='generated test data',
            license_id='MIT', weights_sha256=sha256(path.read_bytes()).hexdigest(),
            preprocessing='rgb-unit-letterbox', backend='opencv-dnn-cpu'))
    manifest = folder/'synthetic-model.json'
    manifest.write_text(json.dumps(record))
    return manifest


@pytest.fixture
def model_manifest(tmp_path):
    return synthetic_model(tmp_path)


def test_actual_cpu_neural_inference_maps_native_roi_without_downloads(model_manifest, monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request, 'urlopen', lambda *a, **k: pytest.fail('No network for inference'))
    detector = OnnxModuleDetector(model_manifest)
    found = detector.detect_array(np.zeros((560, 760, 3), np.uint8))
    assert len(found) == 2
    assert all(0 <= x < 760 and 0 <= y < 560 for d in found for x, y in d.polygon_px)
    xs, ys = zip(*found[0].polygon_px)
    assert min(xs) == pytest.approx(77.1286, abs=2)
    assert 65 < min(ys) < 95 and 125 < max(ys) < 155
    assert detector.description['production_approved'] is False
    assert detector.manifest.provider == 'synthetic-contract'


@pytest.mark.parametrize('failure', ['no_rights','approved','wrong_hash','traversal','thermal','unsupported_license','bad_profile'])
def test_invalid_or_unreviewed_model_is_refused_before_inference(model_manifest, failure):
    data = json.loads(model_manifest.read_text())
    if failure == 'no_rights': data['evaluation_allowed'] = False
    elif failure == 'approved': data['production_approved'] = True
    elif failure == 'wrong_hash': data['model']['weights_sha256'] = '0'*64
    elif failure == 'traversal': data['weights'] = '../synthetic.onnx'
    elif failure == 'thermal': data['model']['modality'] = 'thermal'
    elif failure == 'unsupported_license': data['model']['license_id'] = 'AGPL-3.0'
    else: data['profile'] = 'unverified'
    model_manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError): OnnxModuleDetector(model_manifest)


def test_saved_reference_comparison_separate_counts_reopen_no_mutation(module_scene, model_manifest, monkeypatch):
    source, value = module_scene
    result = pv.detect_partial_pv_window(value, window=(20,20,760,560))
    region = pv.make_region(value,result)
    for entry in region['entries']: entry['status']='outline_ok'
    key = pv.region_key(result.rgb_window)
    pv.save_module_review(value,{key:region},key)
    original = {p:p.read_bytes() for p in (value.rgb_path,value.thermal_path,value.folder/pv.STATE,source/'job.json')}
    record=evaluation.compare_saved_region(source,model_manifest,key)
    assert record['counts']==dict(reviewed_outlines=2,candidate_outlines=2,matched_reviewed_outlines=1,
        unmatched_reviewed_outlines=1,additional_unreviewed_candidates=1)
    assert all(record[k] is False for k in (*FLAGS,*evaluation.EXTRA_FLAGS))
    assert all(p.read_bytes()==data for p,data in original.items())
    monkeypatch.setattr(evaluation, 'OnnxModuleDetector',lambda *a:pytest.fail('Reopen does not load a model'))
    restored, candidates, references=evaluation.read_model_comparison(value)
    assert restored['counts']==record['counts'] and len(candidates.proposals)==2 and len(references)==2
    # A changed saved human reference invalidates the comparison.
    region['entries'][0]['note']='changed synthetic judgement'
    pv.save_module_review(value,{key:region},key)
    with pytest.raises(ValueError): evaluation.read_model_comparison(value)


def test_actual_isolated_worker_cli_and_failed_run_keep_last_success(module_scene,model_manifest):
    source,value=module_scene
    result=pv.detect_partial_pv_window(value,window=(20,20,760,560))
    region=pv.make_region(value,result)
    for entry in region['entries']: entry['status']='outline_ok'
    key=pv.region_key(result.rgb_window)
    pv.save_module_review(value,{key:region},key)
    script=Path(__file__).resolve().parents[1]/'scripts/MCM_SolarCheck_PV_MODELLVERGLEICH.py'
    args=[sys.executable,str(script),'--source',str(source),'--manifest',str(model_manifest),'--region',key]
    run=subprocess.run(args,capture_output=True,timeout=45)
    assert run.returncode==0,run.stderr.decode()
    assert not run.stdout and not run.stderr
    saved=(value.folder/evaluation.STATE).read_bytes()
    model_manifest.write_text('{}')
    failed=subprocess.run(args,capture_output=True,timeout=45)
    assert failed.returncode==2 and not failed.stdout and not failed.stderr
    assert (value.folder/evaluation.STATE).read_bytes()==saved


def test_external_tensor_model_rejected_without_reading_its_location(model_manifest):
    model_path=model_manifest.parent/'synthetic.onnx'
    model=onnx.load_model_from_string(model_path.read_bytes())
    tensor=model.graph.initializer[0]
    tensor.ClearField('raw_data')
    tensor.data_location=TensorProto.EXTERNAL
    tensor.external_data.add(key='location',value='/unrelated-private-location')
    model_path.write_bytes(model.SerializeToString())
    data=json.loads(model_manifest.read_text())
    data['model']['weights_sha256']=sha256(model_path.read_bytes()).hexdigest()
    model_manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='Externe'):
        OnnxModuleDetector(model_manifest)


def test_rgb_preprocessing_padding_and_invalid_output_are_checked(model_manifest):
    detector=OnnxModuleDetector(model_manifest)
    class RecordingNet:
        blob=None
        def setInput(self,blob):self.blob=blob
        def forward(self,names):
            return [np.array([[.2,.2,.4,.4]],np.float32),np.array([float('nan')]),np.ones((1,28,28),np.float32)]
    detector.net=RecordingNet()
    image=np.zeros((32,64,3),np.uint8)
    image[:]=[10,20,30]
    with pytest.raises(ValueError,match='ONNX-Instanzausgaben'):
        detector.detect_array(image)
    blob=detector.net.blob
    assert blob.shape==(1,3,64,64)
    assert not blob[:,:,0].any() and not blob[:,:,-1].any()
    assert blob[0,:,20,20]==pytest.approx([30/255,20/255,10/255])
