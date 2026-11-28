"""Generated data, provenance and reopening without customer inputs or Torch."""
from dataclasses import asdict
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from mcm_solarcheck.services import pv_synthetic_training as probe
from mcm_solarcheck.review.model_lineage import TrainingRun


def test_generated_dataset_is_reproducible_grouped_and_preserves_ignore_labels():
    first, samples, arrays = probe.synthetic_dataset()
    second, repeated, _ = probe.synthetic_dataset()
    assert first == second and samples == repeated
    assert first.split_counts == {'train': 2, 'validation': 1, 'test': 1}
    assert len({s['group_id'] for s in samples}) == 4
    assert len({s['content_sha256'] for s in samples}) == 4
    for sample in samples:
        rgb, mask = arrays[sample['sample_id']]
        assert rgb.shape == (64, 64, 3) and rgb.dtype == np.uint8
        assert set(np.unique(mask)) == {0, 1, 255}
        assert np.all(mask[:3] == 255)
        assert sha256(rgb.tobytes()+mask.tobytes()).hexdigest() == sample['content_sha256']


@pytest.fixture
def completed(tmp_path):
    job_id = 'probe-00000000000000000001-' + 'a'*32
    folder = tmp_path/probe.FOLDER/job_id
    folder.mkdir(parents=True)
    weights = b'synthetic test bytes, never loaded as a model'
    (folder/probe.WEIGHTS).write_bytes(weights)
    build, _, _ = probe.synthetic_dataset()
    run = TrainingRun(build.dataset_id, build.snapshot_id, 'external-unet-synthetic-probe',
        probe.specification()['source_commit'], probe.PROFILE, probe.PARAMETERS.copy())
    record = dict(check=probe.CHECK, probe_id=job_id, status='passed', synthetic_only=True,
        input_profile=probe.PROFILE, initialization='seeded_random_not_published_weights',
        torch_version=probe.specification()['torch_version'],
        synthetic_training_started=True, synthetic_weights_changed=True, ignore_gradient_verified=True,
        reload_verified=True, training_run=asdict(run), run_id=run.run_id,
        dataset_sha256=build.dataset_id, source_commit=run.trainer_version,
        split_counts=build.split_counts, changed_parameter_tensors=64,
        synthetic_losses=[.7, .5, .4], synthetic_validation_loss=.6, synthetic_test_loss=.65,
        weights_bytes=len(weights), weights_sha256=sha256(weights).hexdigest(),
        **dict.fromkeys(probe.FALSE_FLAGS, False))
    (folder/probe.REPORT).write_text(json.dumps(record), encoding='utf-8')
    return tmp_path, folder, record


def test_read_only_reopening_needs_no_torch_and_ignores_interrupted_jobs(completed, monkeypatch):
    root, folder, record = completed
    (root/probe.FOLDER/('probe-'+'9'*20+'-'+'f'*32+'.next')).mkdir()
    monkeypatch.setitem(sys.modules, 'torch', None)
    assert probe.read_probe(root) == record
    assert probe.read_probe(root, folder.name) == record


@pytest.mark.parametrize('fault', ['weights', 'approval', 'lineage', 'nan', 'incomplete', 'path'])
def test_corrupt_or_misleading_probe_reports_are_rejected(completed, fault):
    root, folder, record = completed
    if fault == 'weights': (folder/probe.WEIGHTS).write_bytes(b'changed')
    if fault == 'approval': record['production_approved'] = True
    if fault == 'lineage': record['training_run']['parameters']['seed'] += 1
    if fault == 'nan': record['synthetic_test_loss'] = float('nan')
    if fault == 'incomplete': del record['reload_verified']
    (folder/probe.REPORT).write_text(json.dumps(record), encoding='utf-8')
    with pytest.raises(ValueError):
        probe.read_probe(root, '../outside' if fault == 'path' else folder.name)


def test_cancel_before_runtime_import_creates_no_job(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'torch', None)
    with pytest.raises(RuntimeError):
        probe.run_probe(tmp_path, should_cancel=lambda: True)
    assert list(tmp_path.iterdir()) == []


def script():
    path = Path(__file__).resolve().parents[1]/'scripts/MCM_SolarCheck_PV_TRAININGSPROBE.py'
    spec = importlib.util.spec_from_file_location('synthetic_training_cli_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_show_is_read_only_and_stdout_has_no_local_paths(completed, monkeypatch, capsys):
    root, folder, record = completed
    monkeypatch.setitem(sys.modules, 'torch', None)
    before = {p: p.read_bytes() for p in folder.iterdir()}
    assert script().main(['--prefix', str(root), '--show']) == 0
    output = capsys.readouterr().out
    assert json.loads(output) == record and str(root) not in output
    assert all(p.read_bytes() == data for p, data in before.items())


def test_cli_failure_discloses_no_local_paths_and_never_trains(tmp_path, capsys):
    assert script().main(['--prefix', str(tmp_path), '--show']) == 2
    output = capsys.readouterr().out
    assert str(tmp_path) not in output
    assert json.loads(output)['customer_training_started'] is False
