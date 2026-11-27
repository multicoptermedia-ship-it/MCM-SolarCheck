"""Generated comparison, cancellation and read-only report contracts."""
import builtins
from pathlib import Path
import json
from types import SimpleNamespace

import numpy as np
import pytest

from mcm_solarcheck.services import cvut_yolo_native_comparison as comparison
from mcm_solarcheck.vision import cvut_yolo_validation as decoding
from mcm_solarcheck.vision.pvis_instance_decoding import aggregate
from test_cvut_yolo_public_validation import runner


def generated_comparison(monkeypatch, *, cancel=False):
    rgb=np.zeros((24,256,256,3),np.uint8)
    target=np.zeros((24,256,256),np.int32);target[:,40:80,40:120]=1
    samples=[(i,SimpleNamespace(rgb=np.zeros((512,512,3),np.uint8),
        instances=np.repeat(np.repeat(target[i],2,axis=0),2,axis=1),
        record=dict(record_sha256='a'*64))) for i in range(24)]
    calls=[]
    def inference(torch,model,image,*,size=256):
        calls.append(size)
        scale=size//256
        # No reference labels/counts/unknown regions passed into inference.
        mask=np.zeros((1,size,size),bool)
        mask[:,40*scale:80*scale,40*scale:120*scale]=True
        return np.array([[40,40,120,80]],float)*scale,mask,np.array([.9])
    monkeypatch.setattr(decoding,'infer',inference)
    return comparison.compare(None,None,rgb,target,samples,
        should_cancel=lambda:bool(cancel and calls)),calls


def test_both_scales_use_same_samples_and_independent_known_pixel_scoring(monkeypatch):
    result,calls=generated_comparison(monkeypatch)
    assert calls==[256,512]*24
    assert len(result['crops'])==24
    assert all(result['metrics'][key]['matched_instances']==24 for key in comparison.METRICS)
    assert result['reference_geometry']==dict(reference_instances=24,old_aspect_rejected=0)


def test_cancel_between_network_scales_cannot_return_partial_comparison(monkeypatch):
    with pytest.raises(KeyboardInterrupt):generated_comparison(monkeypatch,cancel=True)


def report(tmp_path,monkeypatch):
    result,_=generated_comparison(monkeypatch)
    value=runner.sealed(dict(result,check=runner.NATIVE_CHECK,
        status='finished_public_research_not_production',**{k:False for k in runner.FALSE_FLAGS}))
    path=tmp_path/'native.json';path.write_text(json.dumps(value))
    return path,value


def test_native_report_reopens_without_torch_images_or_a_new_run(tmp_path,monkeypatch):
    path,value=report(tmp_path,monkeypatch);original=path.read_bytes()
    real_import=builtins.__import__
    def guarded(name,*a,**k):
        if name.split('.')[0] in ('torch','ultralytics','PIL'):
            pytest.fail('Reopening imported a model/image runtime')
        return real_import(name,*a,**k)
    monkeypatch.setattr(builtins,'__import__',guarded)
    assert runner.show(path)==runner.show(path)==value
    assert path.read_bytes()==original


@pytest.mark.parametrize('field',['metrics','reference_geometry','crops'])
def test_resealed_native_totals_cannot_hide_missing_crops(tmp_path,monkeypatch,field):
    path,value=report(tmp_path,monkeypatch)
    if field=='metrics':value[field]['native512_raw']['matched_instances']+=1
    elif field=='reference_geometry':value[field]['old_aspect_rejected']+=1
    else:value[field].pop()
    path.write_text(json.dumps(runner.sealed(value)))
    with pytest.raises(ValueError):runner.show(path)


def test_cancellation_preserves_existing_report_before_native_image_read(tmp_path,monkeypatch):
    path,_=report(tmp_path,monkeypatch);original=path.read_bytes()
    with pytest.raises(KeyboardInterrupt):
        runner.validate(tmp_path/'missing',tmp_path/'missing.pt',path,
            native_source=tmp_path/'not-read',should_cancel=lambda:True)
    assert path.read_bytes()==original


def test_committed_native_evidence_keeps_original_grid_and_common_grid_distinct():
    path=Path(__file__).resolve().parents[1]/'docs/evidence/cvut-yolo-native-comparison-2026-11-27.json'
    value=runner.show(path);metrics=value['metrics']
    def counts(name):
        return tuple(metrics[name][k] for k in ('matched_instances','additional_predictions','missed_references'))
    assert counts('legacy256_outlines')==(59,45,58)
    assert counts('projective256_outlines')==(85,62,32)
    assert counts('common512_outlines_from256')==(85,66,32)
    assert counts('native512_outlines')==(69,136,48)
    assert value['reference_geometry']==dict(reference_instances=117,old_aspect_rejected=60)
    assert value['weights_sha256']=='d80be7a0629da05e4f315e3a8ead0fb2438649c191a123a33e14403a334cdc27'
