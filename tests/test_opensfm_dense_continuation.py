"""Bounded continuation of synthetic existing jobs, without original/DB access."""
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from mcm_solarcheck.services import opensfm_rgb_pilot as pilot
from mcm_solarcheck.services import opensfm_dense_continuation as resume
from mcm_solarcheck.services.colmap_openmvs_pilot import PilotCancelled, PilotError, PilotTimeout
from test_opensfm_rgb_pilot import geotiff, reconstruction


def cache_detail():
    values = dict.fromkeys(pilot.CACHE_COUNTS, 0)
    values.update(working_images=3, clusters=2, raw_readable=2, clusters_fully_cached=1,
                  clusters_without_cache=1, clustered_images=3, check='solarcheck-opensfm-cache-1',
                  status='completed', changed_during_check=False, geometric_quality_verified=False,
                  resume_implemented=False)
    return values


@pytest.fixture
def stopped_job(tmp_path):
    folder = tmp_path / 'opensfm-rgb-synthetic'
    folder.mkdir()
    names = [f'{i:06d}.JPG' for i in range(1, 4)]
    root = Path(__file__).resolve().parents[1]
    config = pilot.OpenSfMPilotConfig((sys.executable,), root / 'scripts/MCM_SolarCheck_OPENSFM_STAGE.py', tmp_path)
    for relative in resume.PROTECTED_METADATA:
        path = folder / relative
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text('synthetic immutable metadata')
    report = dict(pipeline='opensfm_rgb', status='failed', registration_complete=True,
                  rgb_images=3, registered_images=3, models=1, missing_images=0, foreign_images=0,
                  steps=[dict(stage=s, status='finished' if i < 7 else 'failed') for i, s in enumerate(pilot.STAGES[:8])])
    (folder / 'job.json').write_text(json.dumps({**report, 'expected_engine_source': pilot.ENGINE_SOURCE, 'profile': pilot.PROFILE}))
    (folder / 'laufzeiten.json').write_text(json.dumps(report))
    (folder / 'config.yaml').write_text(json.dumps(pilot.PROFILE))
    (folder / 'images').mkdir()
    (folder / 'undistorted/images').mkdir()
    mapping = []
    for name in names:
        content = b'synthetic working copy ' + name.encode()
        (folder / 'images' / name).write_bytes(content)
        (folder / 'undistorted/images' / (name + '.jpg')).write_bytes(b'synthetic undistorted pixels')
        mapping.append(dict(working_name=name, content_sha256=sha256(content).hexdigest().upper(),
                            source_file='PRIVATE ORIGINAL MUST NEVER BE OPENED'))
    (folder / 'input-map.json').write_text(json.dumps(mapping))
    (folder / 'reconstruction.json').write_text(json.dumps(reconstruction(names)))
    (folder / 'undistorted/undistorted_shot_ids.json').write_text(json.dumps({name: [name + '.jpg'] for name in names}))
    (folder / 'undistorted/depthmaps').mkdir()
    for name in names[:2]:
        (folder / 'undistorted/depthmaps' / (name + '.jpg.raw.npz')).write_bytes(b'synthetic existing raw cache')
    check = folder / 'cache-check-abc12345'
    check.mkdir()
    (check / 'Kennzahlen.json').write_text(json.dumps({**report, 'depthmap_cache_check': cache_detail()}))
    (folder / 'step-08.log').write_text('original timeout evidence')
    return folder, config


def engine(calls, *, failure=None, cancelled=None):
    def execute(executable, args, folder, log, cancel, *, timeout, env_overrides):
        assert executable == Path(sys.executable)
        assert env_overrides['VSCMD_SKIP_SENDTELEMETRY'] == '1'
        script = Path(args[args.index('-I') + 1]).name
        if script == 'MCM_SolarCheck_OPENSFM_CACHE_WORKER.py':
            calls.append('cache_check')
            assert timeout == 600
            detail = cache_detail()
            if failure == 'cache': detail.update(status='attention_required', raw_unreadable=1)
            (Path(args[-1]) / 'worker-result.json').write_text(json.dumps(detail))
            return
        stage = args[args.index('-I') + 2]
        calls.append(stage)
        assert stage in pilot.STAGES[7:] and timeout == resume.STAGE_LIMITS[stage]
        assert Path(log).parent != folder and Path(args[args.index('-I') + 3]) == folder
        assert args[-1] == ('--georeferenced' if stage == 'dense_merging' else str(folder))
        log.write_text('synthetic private process log')
        if stage == 'compute_depthmaps':
            if failure == 'timeout': raise PilotTimeout('synthetic timeout')
            if failure == 'mutation': (folder / 'config.yaml').write_text('{}')
            if cancelled is not None: cancelled[0] = True
            # Native cleaning is allowed to reclaim raw cache files after saving clean ones.
            for path in (folder / 'undistorted/depthmaps').glob('*.raw.npz'): path.unlink()
            for i in range(1, 4):
                (folder / 'undistorted/depthmaps' / f'{i:06d}.JPG.jpg.clean.npz').write_bytes(b'synthetic clean')
        if stage == 'dense_merging':
            geotiff(folder / 'undistorted/depthmaps/ortho.tif', crs='EPSG:4326' if failure == 'raster' else 'EPSG:32632')
    return execute


def test_existing_job_continues_only_three_standard_stages_and_reopens_result(stopped_job):
    folder, config = stopped_job
    before = {p: p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    calls = []
    result = resume.run_opensfm_dense_continuation(folder, config, executor=engine(calls))
    assert result.workspace == folder and result.rgb_geotiff.is_file()
    assert calls == ['cache_check', *pilot.STAGES[7:]]
    for p, value in before.items():
        if not p.name.endswith('.raw.npz'): assert p.read_bytes() == value
    report = resume.read_opensfm_run_metrics(folder)
    continuation = report['dense_continuation']
    assert report['status'] == 'failed'  # Original report is retained as history.
    assert continuation['status'] == 'finished' and continuation['orthophoto_created']
    assert continuation['stored_depthmaps'] == {'raw': 0, 'clean': 3}
    assert continuation['reused_initial_stages'] == 7
    assert not continuation['georeferencing_verified'] and not continuation['thermal_created']
    assert 'PRIVATE ORIGINAL' not in json.dumps(report) and 'protected_digests' not in json.dumps(report)
    assert not resume.can_continue_opensfm(report)
    with pytest.raises(PilotError):
        resume.run_opensfm_dense_continuation(folder, config, executor=lambda *a, **kw: pytest.fail('No restart of completed result'))


@pytest.mark.parametrize('failure,expected', [('cache', ['cache_check']),
    ('timeout', ['cache_check', 'compute_depthmaps']), ('mutation', ['cache_check', 'compute_depthmaps']),
    ('raster', ['cache_check', *pilot.STAGES[7:]])])
def test_bad_cache_time_limit_changed_inputs_or_bad_raster_cannot_be_success(stopped_job, failure, expected):
    folder, config = stopped_job
    calls = []
    with pytest.raises(PilotError):
        resume.run_opensfm_dense_continuation(folder, config, executor=engine(calls, failure=failure))
    assert calls == expected
    report = resume.read_opensfm_run_metrics(folder)['dense_continuation']
    assert report['status'] == 'failed' and not report['orthophoto_created']
    if failure == 'timeout':
        assert report['steps'][-1]['failure_kind'] == 'timeout'


def test_changed_working_copy_stops_before_any_engine_call(stopped_job):
    folder, config = stopped_job
    (folder / 'images/000001.JPG').write_bytes(b'changed working copy')
    with pytest.raises(PilotError, match='Pruefsumme'):
        resume.run_opensfm_dense_continuation(folder, config, executor=lambda *a, **kw: pytest.fail('Must not start engine'))


def test_cancel_preserves_completed_stage_and_os_lock_prevents_parallel_resume(stopped_job):
    folder, config = stopped_job
    with resume._exclusive_job(folder), pytest.raises(PilotError, match='bereits fortgesetzt'):
        resume.run_opensfm_dense_continuation(folder, config, executor=lambda *a, **kw: pytest.fail('Locked job'))
    cancelled, calls = [False], []
    with pytest.raises(PilotCancelled):
        resume.run_opensfm_dense_continuation(folder, config, should_cancel=lambda: cancelled[0],
                                              executor=engine(calls, cancelled=cancelled))
    assert calls == ['cache_check', 'compute_depthmaps']
    report = resume.read_opensfm_run_metrics(folder)['dense_continuation']
    assert report['status'] == 'cancelled' and report['steps'][0]['status'] == 'finished'


@pytest.mark.parametrize('change_metadata', [False, True])
def test_explicit_later_attempt_reuses_work_and_refuses_changed_prior_metadata(stopped_job, change_metadata):
    folder, config = stopped_job
    with pytest.raises(PilotTimeout):
        resume.run_opensfm_dense_continuation(folder, config, executor=engine([], failure='timeout'))
    previous = resume._latest(folder)
    evidence = previous.read_bytes()
    if change_metadata:
        path = folder / 'undistorted/neighbors_best.json'
        path.write_bytes(path.read_bytes() + b'changed metadata')
        with pytest.raises(PilotError, match='seit vorheriger'):
            resume.run_opensfm_dense_continuation(folder, config,
                executor=lambda *a, **kw: pytest.fail('Changed metadata must stop before engine'))
    else:
        calls = []
        result = resume.run_opensfm_dense_continuation(folder, config, executor=engine(calls))
        assert result.rgb_geotiff.exists() and calls == ['cache_check', *pilot.STAGES[7:]]
    assert previous.read_bytes() == evidence
