"""Public training contracts with generated pixels, no Torch or external images."""
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys
from dataclasses import asdict

import numpy as np
import pytest

from mcm_solarcheck.services import pvis_public_training_data as data
from mcm_solarcheck.services import pvis_instance_training as trainer
from mcm_solarcheck.review.model_lineage import TrainingRun

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
pilot = importlib.import_module('MCM_SolarCheck_PVIS_TRAINING')


def numeric_package(root, *, synthetic=True):
    root.mkdir(parents=True, exist_ok=True)
    count, size = (4, 64) if synthetic else (16, 256)
    rgb = np.zeros((count, size, size, 3), np.uint8)
    instances = np.zeros((count, size, size), np.int32)
    instances[:, 10:30, 8:25] = 1
    instances[:, 10:30, 25:42] = 2  # adjacent modules keep separate identities
    instances[:, 1:5] = -1
    rgb[instances > 0] = (80, 100, 150)
    path = root/'data.npz'; np.savez(path, rgb=rgb, instances=instances)
    rows = [dict(sample_id=f'generated-{i}', station='009' if i < count//2 else '033',
        split='train' if i < count//2 else 'validation', source_record_sha256='a'*64) for i in range(count)]
    config = dict(generator='synthetic-test-only', count=count)
    manifest = data.seal_manifest(dict(check=data.CHECK, preparation_id=data.fingerprint(config), config=config,
        scope='explicit_public_pvis_research_only', source_url=data.SOURCE, dataset_version='1.0.0',
        label_policy='pvis-projected-whole-module-1', profile=data.PROFILE, size=size,
        license_declared='CC-BY-4.0', license_decision='unreviewed', commercial_training_approved=False,
        synthetic_only=synthetic, test_images=0, customer_images=0,
        split_counts=dict(train=count//2, validation=count//2), samples=rows,
        data_sha256=sha256(path.read_bytes()).hexdigest()))
    return path, manifest


def reseal(manifest):
    return data.seal_manifest({k: v for k, v in manifest.items()
        if k not in ('manifest_sha256', 'dataset_id', 'snapshot_id')})


def test_numeric_bridge_preserves_adjacent_ids_and_never_loads_pickle(tmp_path):
    path, manifest = numeric_package(tmp_path)
    rgb, instances = data.read_arrays(path, manifest, allow_synthetic=True)
    assert rgb.dtype == np.uint8 and instances.dtype == np.int32
    assert set(np.unique(instances)) == {-1, 0, 1, 2}
    with pytest.raises(ValueError): data.read_arrays(path, manifest)
    np.savez(path, rgb=np.array([object()], object), instances=instances)
    manifest['data_sha256'] = sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError): data.read_arrays(path, reseal(manifest), allow_synthetic=True)


def test_reduction_uses_all_source_validity_and_nearest_instance_identity():
    rgb = np.full((512, 512, 3), 20, np.uint8)
    rgb[:2, :2] = [[[0, 0, 0], [1, 1, 1]], [[2, 2, 2], [3, 3, 3]]]
    labels = np.zeros((512, 512), np.int32)
    labels[20:40, 20:40] = 1; labels[20:40, 40:60] = 2
    labels[4, 4] = -1  # unselected top-left source pixel still forces ignore
    reduced, target = data.training_arrays(rgb, labels)
    assert reduced[0, 0].tolist() == [2, 2, 2]
    assert target[2, 2] == -1 and target[12, 19] == 1 and target[12, 20] == 2


@pytest.mark.parametrize('field,value', [('test_images', 1), ('customer_images', 1),
    ('commercial_training_approved', True), ('license_decision', 'approved'),
    ('synthetic_only', None), ('size', 480), ('preparation_id', 'a'*64),
    ('label_policy', 'visible-corners'), ('profile', 'cvut-480x270')])
def test_changed_scope_cannot_be_authorized_by_resealing(tmp_path, field, value):
    _, manifest = numeric_package(tmp_path)
    manifest[field] = value
    with pytest.raises(ValueError): data.validate_manifest(reseal(manifest), allow_synthetic=True)


@pytest.mark.parametrize('fault', ['test', 'role', 'duplicate', 'source-hash', 'counts'])
def test_reject_split_leakage_and_unbound_sources(tmp_path, fault):
    _, manifest = numeric_package(tmp_path)
    if fault == 'test': manifest['samples'][0].update(station='024', split='test')
    if fault == 'role': manifest['samples'][0]['split'] = 'validation'
    if fault == 'duplicate': manifest['samples'][1] = dict(manifest['samples'][0])
    if fault == 'source-hash': manifest['samples'][0]['source_record_sha256'] = 'changed'
    if fault == 'counts': manifest['split_counts']['train'] = 3
    with pytest.raises(ValueError): data.validate_manifest(reseal(manifest), allow_synthetic=True)


def test_data_tamper_and_unknown_arrays_do_not_change_manifest(tmp_path):
    path, manifest = numeric_package(tmp_path); before = data.encoded(manifest)
    path.write_bytes(b'changed')
    with pytest.raises(ValueError): data.read_arrays(path, manifest, allow_synthetic=True)
    assert data.encoded(manifest) == before
    np.savez(path, rgb=np.zeros(3), instances=np.zeros(3), extra=np.zeros(3))
    manifest['data_sha256'] = sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError): data.read_arrays(path, reseal(manifest), allow_synthetic=True)


def test_root_guard_does_not_adopt_existing_data_or_git(tmp_path):
    existing = tmp_path/'existing'; existing.mkdir(); (existing/'keep').write_bytes(b'original')
    with pytest.raises(ValueError): pilot._root(existing)
    assert (existing/'keep').read_bytes() == b'original'
    repository = tmp_path/'repo'; (repository/'.git').mkdir(parents=True)
    (repository/'.git/HEAD').write_text('ref: refs/heads/test')
    with pytest.raises(ValueError): pilot._root(repository/'output')
    own = pilot._root(tmp_path/'own')
    assert pilot._root(own) == own


def test_cli_requires_explicit_public_training_mode_and_reports_safe_errors(tmp_path, capsys):
    already_imported = 'torch' in sys.modules
    with pytest.raises(SystemExit): pilot.main([])
    assert pilot.main(['--show', '--prefix', str(tmp_path/'none')]) == 2
    report = json.loads(capsys.readouterr().out)
    assert str(tmp_path) not in json.dumps(report)
    assert report['model_updated'] is report['production_approved'] is False
    assert ('torch' in sys.modules) == already_imported


def test_package_reuses_reviewed_audit_and_cancels_without_sources_changes(public_pixels, tmp_path, monkeypatch):
    # Fixture supplies deliberately invalid test JPEGs; none may be decoded.
    from test_pvis_image_adapter import audit
    _, source = public_pixels
    audit.audit(source)
    before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    monkeypatch.setattr(data, 'SAMPLES', 1)
    root = tmp_path/'public-output'
    with pytest.raises(KeyboardInterrupt):
        pilot.prepare_package(source, root, should_cancel=lambda: True)
    assert all(p.read_bytes() == b for p, b in before.items())
    _, package_id, manifest = pilot.prepare_package(source, root)
    assert manifest['split_counts'] == dict(train=1, validation=1)
    assert manifest['test_images'] == manifest['customer_images'] == 0
    assert all(p.read_bytes() == b for p, b in before.items())
    assert pilot.prepare_package(source, root)[1:] == (package_id, manifest)


@pytest.fixture
def completed(tmp_path):
    root = pilot._root(tmp_path/'owned')
    package, manifest = numeric_package(tmp_path/'generated', synthetic=False)
    package_id = manifest['preparation_id']
    folder = root/'packages'/package_id; folder.mkdir(parents=True)
    (folder/'data.npz').write_bytes(package.read_bytes())
    (folder/'package.json').write_text(data.encoded(manifest))
    run = TrainingRun(manifest['dataset_id'], manifest['snapshot_id'], 'test-fake-no-model',
        'generated-contract', data.PROFILE, dict(trainer.PARAMETERS))
    job = root/'runs'/run.run_id; job.mkdir(parents=True)
    weights = job/trainer.WEIGHTS; weights.write_bytes(b'synthetic contract bytes, never torch-loaded')
    metrics = dict(loss=1., foreground_iou=.5)
    report = dict(check=trainer.CHECK, status='finished_experimental_not_production',
        run_id=run.run_id, dataset_id=run.dataset_id, training_run=asdict(run),
        split_counts=manifest['split_counts'], training_started=True, training_authorized=True,
        authorization_scope=manifest['scope'], public_training_started=True, synthetic_only=False,
        output_channels=4, input_profile=data.PROFILE, initialization='seeded_random_no_published_weights',
        license_declared='CC-BY-4.0', license_decision='unreviewed',
        reload_verified=True, ignore_gradient_verified=True, pixel_test_images_read=0,
        weights_bytes=weights.stat().st_size, weights_sha256=sha256(weights.read_bytes()).hexdigest(),
        epochs_completed=3, steps=24, experimental_weights_changed=True, changed_parameter_tensors=62,
        history=[dict(epoch=i, training_loss=1., validation=metrics) for i in (1, 2, 3)],
        baseline_validation=metrics, final_validation=metrics)
    for name in ('customer_training_started', 'customer_images_read', 'production_approved',
        'automatically_accepted', 'accuracy_verified', 'physical_module_ids_confirmed', 'coverage_verified',
        'georeferencing_verified', 'temperature_verified', 'pair_registered', 'published_weights_loaded',
        'commercial_training_approved', 'instance_detection_ready', 'model_updated',
        'customer_images_exported', 'original_cvut_profile_verified'): report[name] = False
    report['report_sha256'] = data.fingerprint(report)
    (job/'report.json').write_text(data.encoded(report))
    (root/'latest.json').write_text(data.encoded(dict(package_id=package_id, run_id=run.run_id,
        weights_sha256=report['weights_sha256'])))
    return root, job, report


def test_reopen_checks_only_saved_data_and_weights_without_torch_or_pixels(completed, monkeypatch):
    root, _, report = completed
    monkeypatch.setattr(pilot.audited, '_sources', lambda *a: pytest.fail('Reopen read public JPEGs'))
    monkeypatch.setattr(trainer, 'run_training', lambda *a, **k: pytest.fail('Reopen started training'))
    assert pilot.show(root) == report


@pytest.mark.parametrize('target', ['weights', 'package', 'report'])
def test_corruption_blocks_reopen_and_preserves_previous_pointer(completed, target):
    root, job, _ = completed; pointer = (root/'latest.json').read_bytes()
    path = (job/trainer.WEIGHTS if target == 'weights' else job/'report.json' if target == 'report'
        else next((root/'packages').glob('*/data.npz')))
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError): pilot.show(root)
    assert (root/'latest.json').read_bytes() == pointer


@pytest.mark.parametrize('field,value', [('automatically_accepted', True), ('pixel_test_images_read', 1),
    ('customer_images_read', True), ('instance_detection_ready', True), ('steps', 25),
    ('authorization_scope', 'customer'), ('commercial_training_approved', True)])
def test_resealed_report_cannot_grant_acceptance_or_customer_training(completed, field, value):
    root, job, report = completed
    report[field] = value; report.pop('report_sha256'); report['report_sha256'] = data.fingerprint(report)
    (job/'report.json').write_text(data.encoded(report))
    with pytest.raises(ValueError): pilot.show(root)


from test_pvis_image_adapter import public_pixels
from test_pvis_public_reference import reference
