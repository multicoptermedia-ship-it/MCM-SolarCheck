"""Read-only research report reopening and unpublished cancellation contracts."""
import builtins
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

import pytest

from mcm_solarcheck.vision.pvis_instance_decoding import aggregate

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0, str(SCRIPTS))
import MCM_SolarCheck_CVUT_YOLO_PRUEFUNG as runner


def saved_report(tmp_path):
    row = dict(reference_instances=1, scored_prediction_instances=2,
        predictions_wholly_ignored=0, matched_instances=1, additional_predictions=1,
        missed_references=0, foreground_intersection=100, foreground_union=150)
    rows = [dict(raw_masks=dict(row), module_outlines=dict(row)) for _ in range(24)]
    result = runner.sealed(dict(check=runner.CHECK,
        status='finished_public_research_not_production', crops=rows,
        raw_mask_metrics=aggregate([r['raw_masks'] for r in rows]),
        module_outline_metrics=aggregate([r['module_outlines'] for r in rows]),
        **{k:False for k in runner.FALSE_FLAGS}))
    path = tmp_path/'report.json'
    path.write_text(json.dumps(result))
    return path,result


def test_show_reads_no_model_image_or_torch_and_keeps_bytes(tmp_path,monkeypatch):
    path,expected = saved_report(tmp_path)
    original = path.read_bytes()
    real_import = builtins.__import__
    def guarded(name,*a,**k):
        if name.split('.')[0] in ('torch','ultralytics','PIL'):
            pytest.fail('Report reopening imported model or image runtime')
        return real_import(name,*a,**k)
    monkeypatch.setattr(builtins,'__import__',guarded)
    assert runner.show(path) == expected
    assert runner.show(path) == expected
    assert path.read_bytes() == original


@pytest.mark.parametrize('field',runner.FALSE_FLAGS)
def test_resealed_reports_cannot_claim_customer_or_quality_scope(tmp_path,field):
    path,value = saved_report(tmp_path)
    value[field] = True
    path.write_text(json.dumps(runner.sealed(value)))
    with pytest.raises(ValueError,match='scope'):
        runner.show(path)


def test_resealed_totals_must_match_all_24_crops(tmp_path):
    path,value = saved_report(tmp_path)
    value['module_outline_metrics']['matched_instances'] += 1
    path.write_text(json.dumps(runner.sealed(value)))
    with pytest.raises(ValueError,match='totals'):
        runner.show(path)


def test_cancel_before_start_preserves_previous_report_without_reading_inputs(tmp_path):
    path,_ = saved_report(tmp_path)
    original = path.read_bytes()
    with pytest.raises(KeyboardInterrupt):
        runner.validate(tmp_path/'missing',tmp_path/'missing.pt',path,
            should_cancel=lambda:True)
    assert path.read_bytes() == original


def test_existing_report_is_never_overwritten(tmp_path):
    path,_ = saved_report(tmp_path)
    original = path.read_bytes()
    with pytest.raises(ValueError,match='Preserve completed'):
        runner.validate(tmp_path/'missing',tmp_path/'missing.pt',path)
    assert path.read_bytes() == original


def test_published_public_befund_is_reopenable_and_does_not_claim_count_accuracy():
    root = SCRIPTS.parent/'docs/evidence'
    value = runner.show(root/'cvut-yolo-module-validation-2026-11-27.json')
    assert value['raw_mask_metrics']['matched_instances'] == 90
    outlines = value['module_outline_metrics']
    assert (outlines['matched_instances'],outlines['additional_predictions'],
            outlines['missed_references']) == (59,45,58)
    assert outlines['reference_instances'] == 117
    assert outlines['scored_prediction_instances'] == 104


def test_historical_source_archive_matches_inventory_without_images_or_private_link():
    root = SCRIPTS.parent/'docs/evidence'
    evidence = json.loads((root/'cvut-yolo-public-2026-11-27.json').read_text())
    entry = evidence['historical_source_archive']
    data = (root/entry['name']).read_bytes()
    assert len(data) == entry['bytes'] and sha256(data).hexdigest() == entry['sha256']
    with zipfile.ZipFile(root/entry['name']) as archive:
        assert sorted(archive.namelist()) == sorted(
            ['README.txt']+['experiment-sources/'+name for name in entry['members']])
        for name,expected in entry['members'].items():
            assert name.endswith('.py')
            content = archive.read('experiment-sources/'+name)
            assert sha256(content).hexdigest() == expected
            assert b'drive.google' not in content
