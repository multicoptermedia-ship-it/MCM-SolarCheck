"""Generated mask, proposal and persistence fixtures; never customer/public image reads."""
from dataclasses import asdict
from hashlib import sha256
import importlib
import json
import shutil
import sys

import numpy as np
from PIL import Image
import pytest

from mcm_solarcheck.vision import pvis_instance_decoding as decoder
from mcm_solarcheck.services import pvis_instance_validation as validation
from mcm_solarcheck.services.pvis_public_training_data import fingerprint, read_arrays
from mcm_solarcheck.review.model_lineage import TrainingRun
from test_pvis_public_training import completed, pilot

cli = importlib.import_module('MCM_SolarCheck_PVIS_INSTANZPRUEFUNG')


def logits():
    value = np.zeros((4, 64, 64), np.float32)
    value[0] = 10; value[1, 8:32, 8:48] = 20
    value[2, 8:32, 28:48] = 2
    return value


def test_adjacent_regions_are_separate_without_any_reference_or_module_count():
    value = logits(); original = value.copy()
    prediction, probability, info = decoder.decode(value)
    assert info['status'] == 'complete' and info['candidate_instances'] == 2
    assert prediction[10, 10] == 1 and prediction[10, 30] == 2
    assert prediction[0, 0] == 0 and .99 < probability[10, 10] <= 1
    assert np.array_equal(value, original)
    assert decoder.decode(value)[2] == info


def test_spatially_disconnected_regions_do_not_merge_through_background():
    value = logits(); value[1, :, 25:31] = 0; value[2:] = 0
    prediction, _, info = decoder.decode(value)
    assert info['candidate_instances'] == 2 and prediction[10, 26] == 0


def test_fixed_seed_range_does_not_chain_distant_embeddings_via_a_slope():
    value = logits(); value[2] = np.arange(64, dtype=np.float32)[None, :]*.04
    prediction, _, info = decoder.decode(value)
    assert info['candidate_instances'] >= 3
    assert prediction[10, 8] != prediction[10, 47]


def test_empty_candidates_and_crop_boundary_are_explicit():
    value = logits(); value[1] = -10
    prediction, _, info = decoder.decode(value)
    assert not prediction.any() and info['candidate_instances'] == 0
    value[1] = 20
    _, _, info = decoder.decode(value)
    assert info['candidate_instances'] == 2  # original differing embedding still separates
    assert any(c['touches_crop_edge'] for c in info['candidates'])


def test_too_many_regions_produce_unscored_diagnostic_instead_of_false_success():
    value = logits(); value[1] = -10; value[1, ::2, ::2] = 20
    prediction, _, info = decoder.decode(value)
    assert info['status'] == 'limit_exceeded_unscored'
    assert info['regions_examined'] == 512 and info['rejected_small_regions'] == 512
    assert not prediction.any()


@pytest.mark.parametrize('fault', ['shape', 'dtype', 'nan', 'inf'])
def test_invalid_logits_rejected(fault):
    value = logits()
    if fault == 'shape': value = value[:2]
    if fault == 'dtype': value = value.astype(np.float64)
    if fault == 'nan': value[3, 4, 4] = np.nan
    if fault == 'inf': value[1, 4, 4] = np.inf
    with pytest.raises(ValueError): decoder.decode(value)


def test_decode_cancellation_never_returns_partial_success():
    with pytest.raises(KeyboardInterrupt): decoder.decode(logits(), should_cancel=lambda: True)


def masks():
    target = np.zeros((64, 64), np.int32)
    target[8:28, 8:28] = 11; target[8:28, 28:48] = 27
    return target


def test_exact_mask_match_and_id_permutation_have_same_counts():
    target = masks(); predicted = np.where(target == 11, 2, np.where(target == 27, 1, 0)).astype(np.int32)
    result = decoder.score_instances(target, predicted)
    metrics = decoder.aggregate([result])
    assert metrics['matched_instances'] == 2 and metrics['precision'] == metrics['recall'] == 1
    assert metrics['foreground_iou'] == 1 and metrics['count_difference'] == 0


def test_equal_counts_with_wrong_outlines_is_not_a_match():
    target = masks(); predicted = np.roll(target, 30, axis=0)
    metrics = decoder.aggregate([decoder.score_instances(target, predicted)])
    assert metrics['count_difference'] == 0 and metrics['matched_instances'] == 0
    assert metrics['additional_predictions'] == metrics['missed_references'] == 2


def test_merged_prediction_cannot_match_two_modules_even_at_iou_half():
    target = masks(); predicted = (target > 0).astype(np.int32)
    result = decoder.score_instances(target, predicted)
    assert result['matched_instances'] == 1 and result['missed_references'] == 1
    assert len({m['prediction_id'] for m in result['matches']}) == 1


def test_split_reference_is_not_counted_as_two_correct_modules():
    target = masks(); target[target == 27] = 11
    predicted = masks(); predicted[predicted == 27] = 2; predicted[predicted == 11] = 1
    result = decoder.score_instances(target, predicted)
    assert result['matched_instances'] == 1 and result['additional_predictions'] == 1


def test_unknown_pixels_do_not_create_false_positives_or_a_false_perfect_precision():
    target = masks(); target[40:60, 4:20] = -1
    prediction = np.zeros_like(target); prediction[40:60, 4:20] = 3
    score = decoder.score_instances(target, prediction); metrics = decoder.aggregate([score])
    assert score['predictions_wholly_ignored'] == 1 and score['scored_prediction_instances'] == 0
    assert metrics['precision'] is None and metrics['recall'] == metrics['f1'] == 0


def test_ignored_bridge_is_not_removed_by_reference_during_decoding():
    value = logits(); value[2:] = 0
    prediction, _, _ = decoder.decode(value)
    target = masks(); target[:, 24:32] = -1
    score = decoder.score_instances(target, prediction)
    assert len(np.unique(prediction[prediction > 0])) == 1
    assert score['scored_prediction_instances'] == 1  # no reference-assisted split


@pytest.fixture
def saved_validation(completed):
    root, old_job, parent = completed
    package, manifest, _ = cli._input(root)
    parameters = dict(parent['training_run']['parameters'])
    parameters['source_sha256'] = dict(trainer=sha256(validation.Path(validation.trained.__file__).read_bytes()).hexdigest(),
        model_factory=sha256(validation.Path(validation.trained.reference_model.__globals__['__file__']).read_bytes()).hexdigest(),
        dataset_reader=sha256(validation.Path(read_arrays.__globals__['__file__']).read_bytes()).hexdigest())
    run = TrainingRun(**dict(parent['training_run'], parameters=parameters))
    parent.update(training_run=asdict(run), run_id=run.run_id, torch_version='2.15.0+cpu')
    parent.pop('report_sha256'); parent['report_sha256'] = fingerprint(parent)
    job = old_job.with_name(run.run_id); old_job.rename(job)
    (job/'report.json').write_text(json.dumps(parent))
    latest = json.loads((root/'latest.json').read_text()); latest['run_id'] = run.run_id
    (root/'latest.json').write_text(json.dumps(latest))
    rgb, targets = read_arrays(package, manifest)
    config = validation._configuration(parent, manifest, dict(torch='2.15.0+cpu', numpy='fixture', opencv='fixture', pillow='fixture'))
    folder = root/validation.FOLDER/fingerprint(config); folder.mkdir(parents=True)
    rows = []
    for i, sample in enumerate(manifest['samples']):
        if sample['split'] != 'validation': continue
        prediction = targets[i].copy(); prediction[prediction < 0] = 0
        key = validation._key(sample)
        validation._png(folder/(key+'-mask.png'), Image.fromarray(prediction.astype(np.uint16)))
        validation._png(folder/(key+'-preview.png'), validation.preview(rgb[i], targets[i], prediction, (prediction > 0).astype(np.float32)))
        row = dict(evaluation_id=folder.name, sample_id=sample['sample_id'], source_record_sha256=sample['source_record_sha256'],
            reference_instance_observations=2,
            decoding=dict(status='complete', candidate_instances=2, candidates=decoder.describe(prediction)),
            score=decoder.score_instances(targets[i], prediction),
            mask_sha256=validation.trained._digest(folder/(key+'-mask.png')),
            preview_sha256=validation.trained._digest(folder/(key+'-preview.png')))
        row['row_sha256'] = fingerprint(row); rows.append(row)
        (folder/(key+'.json')).write_text(json.dumps(row))
    report = validation._summary(config, rows, False); report['report_sha256'] = fingerprint(report)
    (folder/'report.json').write_text(json.dumps(report)); (root/validation.INDEX).write_text(json.dumps(report))
    yield root, folder, report
    shutil.rmtree(root)


def test_saved_validation_reopens_without_model_training_or_source_images(saved_validation, monkeypatch):
    root, _, expected = saved_validation
    monkeypatch.setattr(validation.trained, 'reference_model', lambda *a, **k: pytest.fail('Reopen built model'))
    monkeypatch.setattr(pilot.audited, '_sources', lambda *a: pytest.fail('Reopen decoded original JPEG'))
    assert cli.show(root) == expected
    assert expected['metrics']['matched_instances'] == 16
    assert all(expected[k] is False for k in validation.FALSE_FLAGS)


@pytest.mark.parametrize('kind', ['mask', 'preview', 'row', 'report', 'data', 'weights'])
def test_changed_artifacts_rejected_without_changing_training_publication(saved_validation, kind):
    root, folder, _ = saved_validation; previous = (root/'latest.json').read_bytes()
    paths = dict(mask=next(folder.glob('*-mask.png')), preview=next(folder.glob('*-preview.png')),
        row=next(folder.glob('crop-*.json')), report=root/validation.INDEX,
        data=next((root/'packages').glob('*/data.npz')),
        weights=next((root/'runs').glob('*/'+validation.trained.WEIGHTS)))
    path = paths[kind]; path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError): cli.show(root)
    assert (root/'latest.json').read_bytes() == previous


def test_resealed_report_cannot_approve_production(saved_validation):
    root, folder, report = saved_validation
    report['production_approved'] = True; report.pop('report_sha256'); report['report_sha256'] = fingerprint(report)
    for path in (root/validation.INDEX, folder/'report.json'): path.write_text(json.dumps(report))
    with pytest.raises(ValueError): cli.show(root)


def test_cancelled_new_validation_keeps_previous_index_and_training(saved_validation, monkeypatch):
    root, _, _ = saved_validation
    before = {p: p.read_bytes() for p in (root/validation.INDEX, root/'latest.json')}
    def cancel(*args, **kwargs): raise KeyboardInterrupt
    monkeypatch.setattr(validation, 'run_validation', cancel)
    with pytest.raises(KeyboardInterrupt): cli.evaluate(root, root.parent/'reference')
    assert all(p.read_bytes() == value for p, value in before.items())


def test_unscored_crop_never_enters_metrics_as_zero_error():
    config = dict(parent_run_id='a'*64, weights_sha256='b'*64)
    rows = [dict(sample_id='generated', row_sha256='c'*64, score=None, reference_instance_observations=3,
                 decoding=dict(candidate_instances=0))]
    summary = validation._summary(config, rows, True)
    assert summary['unscored_crops'] == 1 and summary['scored_crops'] == 0
    assert summary['metrics'] is None and summary['accuracy_verified'] is False


def test_cli_requires_mode_and_diagnostics_have_no_paths(tmp_path, capsys):
    with pytest.raises(SystemExit): cli.main([])
    before = 'torch' in sys.modules
    assert cli.main(['--show', '--prefix', str(tmp_path)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert str(tmp_path) not in json.dumps(result) and result['training_started'] is False
    assert ('torch' in sys.modules) == before
