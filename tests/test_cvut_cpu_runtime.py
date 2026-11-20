"""Opt-in pinned external reference + real CPU Torch on synthetic tensors only."""
import io
import json
import os
from pathlib import Path
import shutil

import numpy as np
import pytest

from mcm_solarcheck.vision import cvut_module_detector as cvut

pytestmark = pytest.mark.skipif(not os.environ.get('SOLARCHECK_TEST_CVUT_RUNTIME'),
                                reason='Explicit isolated CPU candidate runtime only')


@pytest.fixture(scope='module')
def runtime(tmp_path_factory):
    import torch
    spec = cvut.specification()
    root = tmp_path_factory.mktemp('cvut-reference')
    existing = os.environ.get('SOLARCHECK_CVUT_REFERENCE')
    if existing:
        shutil.copytree(Path(existing)/'vendor', root/'vendor')
    else:
        # This opt-in test downloads only four small pinned reference files,
        # never published weights, customer imagery or training data.
        import importlib.util
        script = Path(__file__).resolve().parents[1]/'scripts/MCM_SolarCheck_PV_HAWK_SETUP.py'
        s=importlib.util.spec_from_file_location('public_download',script)
        m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        for name, check in spec['sources'].items():
            m.download(spec['source_url']+spec['source_commit']+'/'+name,root/'vendor'/name,check)
    torch.set_num_threads(2)
    return torch, root, spec


def serialized(torch, state):
    stream=io.BytesIO();torch.save(state,stream);return stream.getvalue()


def test_real_reference_matches_all_observed_shapes_and_two_class_forward(runtime):
    torch,root,spec=runtime
    assert torch.__version__==spec['torch_version'] and torch.version.cuda is None
    model=cvut.reference_model(root,spec,torch)
    assert {k:list(v.shape) for k,v in model.state_dict().items()}==spec['state_shapes']
    with torch.inference_mode():
        logits=model(torch.zeros((1,3,270,480)))
    assert tuple(logits.shape)==(1,2,270,480) and torch.isfinite(logits).all()


@pytest.mark.parametrize('fault',['missing','shape','dtype','nan','mapping'])
def test_restricted_loading_rejects_invalid_state(runtime,fault):
    torch,_,_=runtime
    model=torch.nn.Conv2d(3,2,1)
    state=model.state_dict()
    spec={'state_shapes':{k:list(v.shape) for k,v in state.items()}}
    if fault=='missing':state.pop('bias')
    if fault=='shape':state['bias']=torch.zeros(3)
    if fault=='dtype':state['bias']=state['bias'].double()
    if fault=='nan':state['bias'][0]=float('nan')
    if fault=='mapping':state['mask_values']=[255,0]
    with pytest.raises(ValueError):cvut.checked_state(torch,serialized(torch,state),model,spec)


def unwanted_constructor(path):
    Path(path).write_text('must never execute')


def test_weights_only_never_falls_back_to_pickle_objects(runtime,tmp_path):
    torch,_,_=runtime
    marker=tmp_path/'not-created'
    class Payload:
        def __reduce__(self):return unwanted_constructor,(str(marker),)
    model=torch.nn.Conv2d(3,2,1)
    state={'weight':Payload()}
    with pytest.raises(Exception):cvut.checked_state(torch,serialized(torch,state),model,{'state_shapes':{}})
    assert not marker.exists()


def test_real_candidate_loader_probe_and_changed_weights(runtime,tmp_path,monkeypatch):
    torch,root,spec=runtime
    private=tmp_path/'pilot';private.mkdir();shutil.copytree(root/'vendor',private/'vendor')
    torch.manual_seed(0)
    model=cvut.reference_model(private,spec,torch)
    data=serialized(torch,model.state_dict());del model
    from hashlib import sha256
    spec=dict(spec,weights_bytes=len(data),weights_sha256=sha256(data).hexdigest())
    (private/spec['weights']).write_bytes(data)
    config=tmp_path/'synthetic-spec.json';config.write_text(json.dumps(spec))
    monkeypatch.setattr(cvut,'SPEC_PATH',config)
    manifest=private/'cvut-rgb.LOCAL.json'
    manifest.write_text(json.dumps(dict(profile=cvut.PROFILE,source_commit=spec['source_commit'],
        weights_sha256=spec['weights_sha256'],evaluation_allowed=True,production_approved=False)))
    detector=cvut.CVUTModuleDetector(manifest)
    p=detector.probabilities(np.zeros((50,70,3),np.uint8))
    assert p.shape==(270,480) and np.isfinite(p).all()
    assert detector.description['production_approved'] is False
    assert detector.description['preprocessing_verified'] is False
    import importlib.util
    script=Path(__file__).resolve().parents[1]/'scripts/MCM_SolarCheck_CVUT_CPU_PILOT.py'
    monkeypatch.syspath_prepend(str(script.parent))
    loader=importlib.util.spec_from_file_location('cvut_probe_test',script)
    setup=importlib.util.module_from_spec(loader);loader.loader.exec_module(setup)
    setup.probe(private)
    probe=json.loads((private/setup.PROBE_REPORT).read_text())
    assert probe['status']=='passed' and probe['output_classes']==2 and probe['synthetic_only'] is True
    assert probe['accuracy_verified'] is probe['production_approved'] is False
    (private/spec['weights']).write_bytes(b'changed')
    with pytest.raises(ValueError):detector.detect_array(np.zeros((50,70,3),np.uint8))


def test_two_channel_softmax_rgb_order_and_unit_range(runtime):
    torch,_,spec=runtime
    detector=cvut.CVUTModuleDetector.__new__(cvut.CVUTModuleDetector)
    detector.spec,detector.torch=spec,torch
    detector._check_weights=lambda:None
    class Capture(torch.nn.Module):
        def forward(self,x):
            assert x.shape==(1,3,270,480)
            assert torch.all(x[:,0]==1) and torch.all(x[:,2]==0)
            result=torch.full((1,2,270,480),3.0);result[:,1]=2.0
            return result
    detector.model=Capture()
    image=np.full((20,30,3),(0,128,255),np.uint8)
    p=detector.probabilities(image)
    assert np.allclose(p,1/(1+np.exp(1)))  # softmax([3,2]), not sigmoid(2)
