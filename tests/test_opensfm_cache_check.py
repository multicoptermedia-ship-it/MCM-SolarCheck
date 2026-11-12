"""Saved-cache inspection: no original images or real reconstruction needed."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from mcm_solarcheck.services import opensfm_rgb_pilot as pilot
from mcm_solarcheck.services.colmap_openmvs_pilot import PilotError, PilotProcessExit, PilotTimeout

ROOT = Path(__file__).resolve().parents[1]


def worker():
    spec = importlib.util.spec_from_file_location('cache_worker', ROOT / 'scripts/MCM_SolarCheck_OPENSFM_CACHE_WORKER.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dataset(folder):
    directory = folder / 'undistorted/depthmaps'
    directory.mkdir(parents=True)
    names = ['000001.JPG', '000002.JPG', '000003.JPG']
    for name in names[:2]:
        (directory / (name + '.raw.npz')).write_bytes(b'opaque-engine-owned-LZ4-payload')
    (directory / (names[0] + '.clean.npz')).write_bytes(b'opaque-clean-payload')
    calls = []
    def load(name, clean=False):
        calls.append((name, clean))
        depth = np.ones((3, 4), dtype=np.float32)
        normal = np.ones((3, 4, 3), dtype=np.float32)
        return (depth, normal, depth, None) if clean else (depth, normal, None, None, None, None)
    undistorted = SimpleNamespace(load_clusters=lambda: [names[:2], names[2:]],
        load_raw_depthmap=lambda s: load(s), load_clean_depthmap=lambda s: load(s, True))
    data = SimpleNamespace(images=lambda: names, undistorted_dataset=lambda: undistorted)
    return data, undistorted, directory, calls


def test_only_engine_loaders_read_existing_payload_and_clusters(tmp_path):
    data, _, directory, calls = dataset(tmp_path)
    before = {p: p.read_bytes() for p in directory.iterdir()}
    result = worker().inspect_cache(tmp_path, data)
    assert result['status'] == 'completed'
    assert (result['raw_readable'], result['clean_readable']) == (2, 1)
    assert (result['clusters_fully_cached'], result['clusters_partly_cached'], result['clusters_without_cache']) == (1, 0, 1)
    assert len(calls) == 3
    assert all(p.read_bytes() == value for p, value in before.items())
    assert not result['geometric_quality_verified'] and not result['resume_implemented']
    assert '000001' not in json.dumps(result)


@pytest.mark.parametrize('failure', ['loader_error', 'shape', 'changing'])
def test_interrupted_invalid_or_changing_cache_is_preserved_and_not_accepted(tmp_path, failure):
    data, undistorted, directory, _ = dataset(tmp_path)
    original = undistorted.load_raw_depthmap
    def load(name):
        if failure == 'loader_error':
            raise ValueError('Private path from external LZ4 loader MUST NOT LEAK')
        result = list(original(name))
        if failure == 'shape':
            result[1] = np.ones((1, 1), dtype=np.float32)
        else:
            with (directory / (name + '.raw.npz')).open('ab') as stream:
                stream.write(b'simulated concurrent writer')
        return result
    undistorted.load_raw_depthmap = load
    result = worker().inspect_cache(tmp_path, data)
    assert result['status'] == 'attention_required'
    assert result['raw_unreadable'] == (0 if failure == 'changing' else 2)
    assert 'Private' not in json.dumps(result)
    assert len(list(directory.iterdir())) == 3


def stopped_job(folder):
    folder.mkdir()
    record = {'expected_engine_source': pilot.ENGINE_SOURCE, 'status': 'failed', 'profile': pilot.PROFILE,
        'registration_complete': True, 'rgb_images': 3,
        'steps': [{'stage': s, 'status': 'finished' if i < 7 else 'failed'}
                  for i, s in enumerate(pilot.STAGES[:8])]}
    (folder / 'job.json').write_text(json.dumps(record))
    (folder / 'laufzeiten.json').write_text(json.dumps(record))
    (folder / 'config.yaml').write_text(json.dumps(pilot.PROFILE))
    config = pilot.OpenSfMPilotConfig((sys.executable,), ROOT / 'scripts/MCM_SolarCheck_OPENSFM_STAGE.py', folder.parent)
    return config


@pytest.mark.parametrize('failure', [None, 'exit_after_result', 'timeout', 'cancel'])
def test_inspection_never_dispatches_photo_stages_and_requires_clean_worker_exit(tmp_path, failure):
    folder = tmp_path / 'opensfm-rgb-synthetic'
    config = stopped_job(folder)
    before = {p: p.read_bytes() for p in folder.iterdir()}
    def execute(executable, args, cwd, log, cancel, *, timeout, env_overrides):
        assert executable == Path(sys.executable) and timeout == 600
        assert Path(args[1]).name == 'MCM_SolarCheck_OPENSFM_CACHE_WORKER.py'
        assert not any(s in args for s in pilot.STAGES)
        inspection = Path(args[-1])
        assert inspection.parent == folder and cwd == folder
        assert Path(env_overrides['TEMP']) == inspection
        data, _, _, _ = dataset(inspection)
        result = worker().inspect_cache(inspection, data)
        (inspection / 'worker-result.json').write_text(json.dumps(result))
        if failure == 'exit_after_result': raise PilotProcessExit(3221225477)
        if failure == 'timeout': raise PilotTimeout('synthetic')
        if failure == 'cancel': raise pilot.PilotCancelled('synthetic')
    if failure:
        with pytest.raises(PilotError):
            pilot.check_opensfm_depthmap_cache(folder, config, executor=execute)
    else:
        result = pilot.check_opensfm_depthmap_cache(folder, config, executor=execute)
        assert result['depthmap_cache_check']['raw_readable'] == 2
    saved = pilot.read_opensfm_cache_metrics(folder)['depthmap_cache_check']
    if failure:
        assert saved['status'] == {'exit_after_result': 'failed', 'timeout': 'timeout', 'cancel': 'cancelled'}[failure]
        assert saved['accepted_as_readable'] is False and 'raw_readable' not in saved
    else:
        assert saved['status'] == 'completed'
    assert all(p.read_bytes() == value for p, value in before.items())


def test_active_or_modified_job_cannot_start_inspection(tmp_path):
    folder = tmp_path / 'opensfm-rgb-synthetic'
    config = stopped_job(folder)
    (folder / 'config.yaml').write_text('{}')
    with pytest.raises(PilotError, match='unveraendertem Profil'):
        pilot.check_opensfm_depthmap_cache(folder, config, executor=lambda *a, **kw: pytest.fail('must not start'))
    assert not list(folder.glob('cache-check-*'))
