"""Opt-in real CPU YOLO contracts, exclusively generated inputs/weights."""
from collections import OrderedDict
from io import BytesIO
import os
import pickle

import pytest

from mcm_solarcheck.vision import cvut_yolo_research as research

pytestmark = pytest.mark.skipif(not os.environ.get('SOLARCHECK_TEST_YOLO_RUNTIME'),
    reason='Explicit isolated public YOLO CPU reference only')


@pytest.fixture(scope='module')
def runtime():
    import torch
    from ultralytics.cfg import get_cfg
    from ultralytics.nn.tasks import SegmentationModel
    from ultralytics.utils import yaml_load
    import ultralytics
    from pathlib import Path
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(6400)
    cfg = yaml_load(Path(ultralytics.__file__).parent/'cfg/models/v8/yolov8-seg.yaml')
    cfg.update(scale='n', nc=1)
    model = SegmentationModel(cfg, ch=3, nc=1, verbose=False).cpu().float().eval()
    model.args = get_cfg()
    return torch, model


def test_passive_public_graph_extracts_only_tensors_and_shared_activations(runtime):
    torch, model = runtime
    stream = BytesIO()
    torch.save(dict(model=model, version='8.1.29'), stream)
    expected = model.state_dict()
    state, meta = research._passive_tensor_state(stream.getvalue(), torch)
    assert meta['tensor_keys'] == len(expected) == 417
    assert set(state) == set(expected)
    assert all(torch.equal(state[k], expected[k]) for k in expected)
    fresh = research.reference_model(torch, state)
    x = torch.zeros((1,3,64,64))
    with torch.inference_mode():
        assert torch.equal(fresh(x)[0], model(x)[0])


def test_unknown_pickle_callable_is_rejected_without_execution(runtime, tmp_path):
    torch, _ = runtime
    sentinel = tmp_path/'must-not-exist'
    class Dangerous:
        def __reduce__(self):
            return (os.system, (f'touch {sentinel}',))
    stream = BytesIO()
    torch.save(dict(model=Dangerous()), stream)
    with pytest.raises(pickle.UnpicklingError):
        research._passive_tensor_state(stream.getvalue(), torch)
    assert not sentinel.exists()


def test_strict_tensor_types_and_finites(runtime):
    torch, model = runtime
    state = OrderedDict((k,v.clone()) for k,v in model.state_dict().items())
    first = next(k for k,v in state.items() if v.is_floating_point())
    state[first].flatten()[0] = float('nan')
    with pytest.raises(ValueError, match='shapes, types or values'):
        research.reference_model(torch, state)
    state[first] = state[first].double().nan_to_num()
    with pytest.raises(ValueError, match='shapes, types or values'):
        research.reference_model(torch, state)


def test_stages_unfreeze_convolutions_but_keep_batchnorm_and_projection(runtime):
    torch, model = runtime
    for stage in (22, 10, 0):
        research.configure_public_training(torch, model, stage)
        assert model.model[-1].training
        assert all(not p.requires_grad for n,p in model.named_parameters() if '.dfl.' in n)
        for layer in model.modules():
            if isinstance(layer, torch.nn.BatchNorm2d):
                assert not layer.training
                assert all(not p.requires_grad for p in layer.parameters())
        assert any(p.requires_grad for n,p in model.named_parameters()
                   if int(n.split('.')[1]) >= stage)
        if stage:
            assert all(not p.requires_grad for p in model.model[stage-1].parameters())


def generated_batch(torch, *, ignored=False):
    labels = torch.zeros((1,64,64))
    labels[:,20:44,20:44] = 1
    valid = torch.zeros((1,64,64), dtype=torch.bool)
    if not ignored:
        valid[:,16:48,16:48] = True
    return dict(img=torch.zeros((1,3,64,64)), batch_idx=torch.zeros(1),
        cls=torch.zeros((1,1)), bboxes=torch.tensor([[.5,.5,.375,.375]]),
        masks=labels, valid_pixels=valid)


@pytest.mark.parametrize('ignored', [False, True])
def test_unknown_outputs_have_exactly_zero_direct_gradient(runtime, ignored):
    torch, model = runtime
    research.configure_public_training(torch, model, 22)
    criterion = research.known_pixel_loss(torch, model)
    batch = generated_batch(torch, ignored=ignored)
    model.zero_grad(set_to_none=True)
    predictions = model(batch['img'])
    for value in (*predictions[0], predictions[1], predictions[2]):
        value.retain_grad()
    loss, _ = criterion(predictions, batch)
    assert torch.isfinite(loss)
    loss.backward()
    for feature, known in zip(predictions[0], criterion.known_grids):
        assert torch.count_nonzero(feature.grad.masked_select(~known.expand_as(feature))) == 0
    assert torch.count_nonzero(predictions[1].grad.masked_select(
        ~criterion.known_anchors[:,None].expand_as(predictions[1]))) == 0
    assert torch.count_nonzero(predictions[2].grad.masked_select(
        ~criterion.known_proto[None,None].expand_as(predictions[2]))) == 0
    if ignored:
        assert loss.item() == 0


def test_missing_validity_mask_never_defaults_to_background(runtime):
    torch, model = runtime
    research.configure_public_training(torch, model, 22)
    criterion = research.known_pixel_loss(torch, model)
    batch = generated_batch(torch)
    del batch['valid_pixels']
    with pytest.raises(ValueError, match='validity mask'):
        criterion(model(batch['img']), batch)


def test_explicit_native512_forward_and_original256_profile_remain_separate(runtime):
    import numpy as np
    from mcm_solarcheck.vision.cvut_yolo_validation import infer
    torch,model=runtime
    fresh=research.reference_model(torch,model.state_dict())
    rgb=np.zeros((512,512,3),np.uint8)
    with pytest.raises(ValueError):infer(torch,fresh,rgb)
    boxes,masks,scores=infer(torch,fresh,rgb,size=512)
    assert boxes.shape==(len(masks),4) and masks.shape[1:]==(512,512)
    assert scores.shape==(len(masks),) and np.isfinite(scores).all()
