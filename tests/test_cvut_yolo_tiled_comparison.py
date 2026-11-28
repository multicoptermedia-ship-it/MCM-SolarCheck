"""Generated fixed-grid inference and model-free report reopening contracts."""
import builtins
import json
from pathlib import Path
from hashlib import sha256
import zipfile
from copy import deepcopy

import numpy as np
import pytest

from mcm_solarcheck.services import cvut_yolo_tiled_comparison as comparison
from mcm_solarcheck.vision.detection import ModuleDetection
from test_cvut_yolo_public_validation import runner


def generated_report():
    metrics = {method: {threshold: dict(reference_instances=2, predictions=1,
        matched_instances=1, additional_predictions=0, missed_references=1, AP=.5)
        for threshold in ('iou050', 'iou075')} for method in comparison.METHODS}
    rows = [dict(public_case=case, width=5280, height=3956, metrics=deepcopy(metrics))
            for case in comparison.CASES]
    return runner.sealed(dict(check=comparison.CHECK, profile=comparison.PROFILE,
        status='finished_public_research_not_production', images=rows,
        totals={method: {threshold: {k: 3*v for k,v in metrics[method][threshold].items() if k!='AP'}
            for threshold in ('iou050', 'iou075')} for method in comparison.METHODS},
        **{k:False for k in runner.FALSE_FLAGS}))


def test_full_image_report_reopens_without_models_images_or_coco(tmp_path, monkeypatch):
    value=generated_report();path=tmp_path/'tiled.json';path.write_text(json.dumps(value))
    original=path.read_bytes();real=builtins.__import__
    def guarded(name,*args,**kwargs):
        if name.split('.')[0] in ('torch','ultralytics','PIL','pycocotools'):
            pytest.fail('Report reopening imported model/image/evaluation runtime')
        return real(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guarded)
    assert runner.show(path)==runner.show(path)==json.loads(json.dumps(value))
    assert path.read_bytes()==original


@pytest.mark.parametrize('change',['case','image','totals','matched','negative','AP','method','flag'])
def test_resealed_inconsistent_full_image_report_is_rejected(tmp_path,change):
    value=generated_report();row=value['images'][0]
    if change=='case':row['public_case']=24
    elif change=='image':row['width']=256
    elif change=='totals':value['totals']['whole_image256']['iou050']['predictions']+=1
    elif change=='matched':row['metrics']['whole_image256']['iou050']['matched_instances']=2
    elif change=='negative':row['metrics']['whole_image256']['iou050']['predictions']=-1
    elif change=='AP':row['metrics']['whole_image256']['iou050']['AP']=2
    elif change=='method':row['metrics'].pop('grid512_iou')
    else:value['production_approved']=True
    path=tmp_path/'changed.json';path.write_text(json.dumps(runner.sealed(value)))
    with pytest.raises(ValueError):runner.show(path)


def test_same_rgb_windows_reuse_inference_across_fusion_profiles_without_labels():
    yy,xx=np.indices((512,512));rgb=np.stack((xx%256,yy%256,(xx+yy)%255),axis=-1).astype(np.uint8)
    original=rgb.copy();calls=[]
    def detector(pixels):
        assert pixels.dtype==np.uint8 and pixels.shape==(256,256,3)
        calls.append(pixels.tobytes())
        return (ModuleDetection(((80,80),(150,80),(150,130),(80,130)),.9),)
    proposals,diagnostics,computed=comparison.compare_image(rgb,detector)
    assert computed==len(calls)==len(set(calls))
    assert set(proposals)==set(comparison.METHODS)
    assert all(d.confidence==.9 for rows in proposals.values() for d in rows)
    assert diagnostics['grid512_iou']['planned_tiles']==1
    assert np.array_equal(rgb,original)


def test_cancelled_grid_cannot_return_a_complete_comparison():
    calls=[]
    with pytest.raises(KeyboardInterrupt):
        comparison.compare_image(np.zeros((512,512,3),np.uint8),
            lambda image:calls.append(1) or (),should_cancel=lambda:bool(calls))
    assert calls==[1]


def test_incompatible_comparison_modes_stop_before_source_or_model_access(tmp_path):
    with pytest.raises(ValueError,match='one explicit'):
        runner.validate(tmp_path/'missing',tmp_path/'missing.pt',tmp_path/'new.json',
            native_source=tmp_path,tiled_source=tmp_path)


def test_cancel_before_public_whole_image_access(tmp_path):
    with pytest.raises(KeyboardInterrupt):
        runner.validate(tmp_path/'missing',tmp_path/'missing.pt',tmp_path/'new.json',
            tiled_source=tmp_path,should_cancel=lambda:True)
    assert not (tmp_path/'new.json').exists()


def test_saved_public_full_image_evidence_does_not_relabel_old_crop_quality():
    folder=Path(__file__).resolve().parents[1]/'docs/evidence'
    value=runner.show(folder/'cvut-yolo-full-image-grid-2026-11-28.json')
    assert value['test_pixels_read'] is value['customer_images_read'] is False
    assert value['totals']['whole_image256']['iou050']['reference_instances']==348
    assert value['totals']['whole_image256']['iou050']['matched_instances']==0
    first=value['images'][0]['metrics']['grid1024_iou']
    assert tuple(first['iou050'][k] for k in ('matched_instances','additional_predictions','missed_references'))==(134,18,18)
    assert tuple(first['iou075'][k] for k in ('matched_instances','additional_predictions','missed_references'))==(124,28,28)


def test_historical_research_sources_are_preserved_without_images_or_weights():
    folder=Path(__file__).resolve().parents[1]/'docs/evidence'
    index=json.loads((folder/'cvut-yolo-grid-evidence-2026-11-28.json').read_text())
    archive=folder/'cvut-yolo-research-sources-2026-11-28.zip'
    assert sha256(archive.read_bytes()).hexdigest()==index['archive_sha256']
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(index['historical_sources'])
        for name,expected in index['historical_sources'].items():
            assert name.endswith('.py') and sha256(z.read(name)).hexdigest()==expected
    trial=json.loads((folder/'cvut-yolo-focused-anchor-2026-11-28.json').read_text())
    assert trial['policy_source_sha256']==index['historical_sources']['pvis_yolo_training_targets-v2.py']
    assert trial['trainer_source_sha256']==index['historical_sources']['solarcheck_pv_focused_anchor_trial_20261128.py']
    assert trial['app_model_updated'] is trial['production_approved'] is False
