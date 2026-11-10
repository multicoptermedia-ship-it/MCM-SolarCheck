"""Pilot boundaries with synthetic JPEGs/SQLite/GeoTIFFs, never real flights."""
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest
import rasterio
from rasterio.transform import from_origin

from mcm_solarcheck.services import opensfm_rgb_pilot as pilot
from mcm_solarcheck.services import colmap_openmvs_pilot as common
from mcm_solarcheck.services.colmap_openmvs_pilot import (
    PilotCancelled, PilotError, PilotProcessExit, PilotTimeout, RgbPilotFrame,
)


def inputs(tmp_path):
    original = tmp_path / 'originals'
    original.mkdir()
    frames = []
    for i in range(3):
        path = original / f'synthetic-{i}.jpg'
        Image.new('RGB', (12, 10), (i * 40, 50, 80)).save(path)
        frames.append(RgbPilotFrame(str(i), str(path), 50.0 + i * .001, 8.0, 100.0,
                                   sha256(path.read_bytes()).hexdigest()))
    output = tmp_path / 'private'
    output.mkdir()
    runner = tmp_path / 'owned-runner.py'
    runner.write_text('pass\n')
    return frames, pilot.OpenSfMPilotConfig((sys.executable,), runner, output)


def metric_path(folder):
    manifest = json.loads((folder / 'job.json').read_text())
    return folder / manifest['metrics_filename']


def reconstruction(names):
    return [{'cameras': {'camera': {'projection_type': 'perspective'}},
             'shots': {name: {'camera': 'camera', 'rotation': [0.0] * 3,
                              'translation': [0.0, 0.0, float(i)]}
                       for i, name in enumerate(names)},
             'points': {'point': {'coordinates': [1.0, 2.0, 3.0]}}}]


def geotiff(path, *, crs='EPSG:32632', empty=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, 'w', driver='GTiff', width=8, height=6, count=4, dtype='uint8',
                       crs=crs, transform=from_origin(500000, 5500000, .1, .1)) as dst:
        pixels = np.full((4, 6, 8), 80, dtype='uint8')
        pixels[3] = 0 if empty else 255
        dst.write(pixels)


def fake_engine(calls, *, model=None, fail=None, crs='EPSG:32632', empty=False):
    def execute(executable, args, folder, log, cancel, *, timeout, env_overrides):
        assert executable == Path(sys.executable)
        assert '-I' in args and timeout <= 3600
        assert env_overrides['TEMP'] == env_overrides['TMP'] == str(folder / 'tmp')
        assert env_overrides['MPLCONFIGDIR'] == str(folder / 'matplotlib')
        assert env_overrides['VSCMD_SKIP_SENDTELEMETRY'] == '1'
        stage = args[args.index('-I') + 2]
        assert args[args.index('-I') + 3] == str(folder)
        if stage == 'dense_merging':
            assert args[-1] == '--georeferenced'
        else:
            assert args[-1] == str(folder)
        calls.append(stage)
        log.write_text('SYNTHETIC PRIVATE RAW OUTPUT - do not share\n')
        if stage == fail:
            raise PilotProcessExit(123)
        if stage == 'extract_metadata':
            exif = folder / 'exif'
            exif.mkdir()
            for image in (folder / 'images').iterdir():
                (exif / (image.name + '.exif')).write_text(json.dumps(
                    {'gps': {'latitude': 50.0, 'longitude': 8.0, 'altitude': 100.0}}))
        if stage == 'reconstruct':
            names = sorted(image.name for image in (folder / 'images').iterdir())
            data = reconstruction(names) if model is None else model(names)
            (folder / 'reconstruction.json').write_text(json.dumps(data))
        if stage == 'dense_merging':
            geotiff(folder / 'undistorted' / 'depthmaps' / 'ortho.tif', crs=crs, empty=empty)
    return execute


def test_full_standard_stage_chain_preserves_sources_and_never_claims_approval(tmp_path):
    frames, config = inputs(tmp_path)
    before = {f.source_file: Path(f.source_file).read_bytes() for f in frames}
    calls, seen = [], []
    result = pilot.run_opensfm_rgb_pilot(frames, config, executor=fake_engine(calls), on_workspace=seen.append)
    assert calls == list(pilot.STAGES)
    assert result.rgb_geotiff.is_file() and seen == [result.workspace]
    assert result.rgb_images == result.registered_images == 3
    assert all(Path(path).read_bytes() == data for path, data in before.items())
    profile = json.loads((result.workspace / 'config.yaml').read_text())
    assert profile['matcher_type'] == 'OPENCL_BF' and profile['proj_cdn_enabled'] is False
    assert not (result.workspace / 'camera_models_overrides.json').exists()
    summary = json.loads(metric_path(result.workspace).read_text())
    assert summary['status'] == 'finished' and summary['orthophoto_created']
    assert summary['registration_complete'] and summary['points'] == 1
    assert not summary['georeferencing_verified'] and not summary['thermal_created']
    assert not summary['temperature_verified']
    text = json.dumps(summary)
    for forbidden in ('synthetic-', str(tmp_path), 'source_file', 'latitude', 'longitude', 'RAW OUTPUT'):
        assert forbidden not in text


@pytest.mark.parametrize('models', [
    lambda names: reconstruction(names[:2]),
    lambda names: reconstruction(names) + reconstruction(names[:1]),
    lambda names: reconstruction(names + ['foreign.JPG']),
    lambda names: [],
])
def test_partial_or_multiple_or_foreign_models_stop_before_dense(tmp_path, models):
    frames, config = inputs(tmp_path)
    calls = []
    with pytest.raises(PilotError, match='Kameraverbund'):
        pilot.run_opensfm_rgb_pilot(frames, config, executor=fake_engine(calls, model=models))
    assert calls == list(pilot.STAGES[:5])
    folder, = config.output_parent.iterdir()
    summary = json.loads(metric_path(folder).read_text())
    assert summary['status'] == 'failed' and not summary['registration_complete']
    assert not summary['orthophoto_created']


@pytest.mark.parametrize('problem', ['pose', 'camera', 'points'])
def test_invalid_native_pose_or_points_are_not_dense_inputs(tmp_path, problem):
    path = tmp_path / 'native.json'
    data = reconstruction(['000001.JPG'])
    if problem == 'pose':
        data[0]['shots']['000001.JPG']['translation'] = [0, float('nan'), 1]
    elif problem == 'camera':
        data[0]['shots']['000001.JPG']['camera'] = 'missing'
    else:
        data[0]['points']['point']['coordinates'] = []
    path.write_text(json.dumps(data))
    assert not pilot.reconstruction_summary(path, {'000001.JPG'})['registration_complete']


def test_failure_retains_workspace_and_only_sanitized_stage_exit(tmp_path):
    frames, config = inputs(tmp_path)
    seen = []
    with pytest.raises(PilotError, match='Code 123'):
        pilot.run_opensfm_rgb_pilot(frames, config,
            executor=fake_engine([], fail='match_features'), on_workspace=seen.append)
    assert len(seen) == 1 and (seen[0] / 'step-03.log').is_file()
    result = json.loads(metric_path(seen[0]).read_text())
    assert result['steps'][-1]['failure_kind'] == 'process_exit'
    assert result['steps'][-1]['exit_code'] == 123
    assert result['status'] == 'failed'


def test_cancellation_and_timeout_keep_distinct_status(tmp_path):
    frames, config = inputs(tmp_path)
    def cancelled(*args, **kwargs):
        raise PilotCancelled('synthetic')
    with pytest.raises(PilotCancelled):
        pilot.run_opensfm_rgb_pilot(frames, config, executor=cancelled)
    folder, = config.output_parent.iterdir()
    assert json.loads(metric_path(folder).read_text())['status'] == 'cancelled'
    def timed_out(*args, **kwargs):
        raise PilotTimeout('synthetic')
    with pytest.raises(PilotTimeout):
        pilot.run_opensfm_rgb_pilot(frames, config, executor=timed_out)
    folder = max(config.output_parent.iterdir(), key=lambda path: path.stat().st_mtime_ns)
    summary = json.loads(metric_path(folder).read_text())
    assert summary['status'] == 'failed' and summary['steps'][-1]['failure_kind'] == 'timeout'


def test_job_total_budget_reduces_each_stage_limit(tmp_path, monkeypatch):
    frames, config = inputs(tmp_path)
    now = [0.0]
    monkeypatch.setattr(pilot.time, 'monotonic', lambda: now[0])
    seen = []
    engine = fake_engine([])
    def advance(*args, **kwargs):
        seen.append(kwargs['timeout'])
        engine(*args, **kwargs)
        now[0] += 1
    with pytest.raises(PilotTimeout, match='Gesamtzeitlimit'):
        pilot.run_opensfm_rgb_pilot(frames, replace(config, total_timeout_seconds=3), executor=advance)
    assert seen == [3, 2, 1]


@pytest.mark.parametrize('crs,empty', [(None, False), ('EPSG:4326', False), ('EPSG:32632', True)])
def test_missing_or_unprojected_crs_or_empty_output_is_not_published(tmp_path, crs, empty):
    frames, config = inputs(tmp_path)
    with pytest.raises(PilotError, match='GeoTIFF'):
        pilot.run_opensfm_rgb_pilot(frames, config, executor=fake_engine([], crs=crs, empty=empty))
    folder, = config.output_parent.iterdir()
    assert not json.loads(metric_path(folder).read_text())['orthophoto_created']


def test_changed_database_inputs_prevent_result_acceptance(tmp_path):
    frames, config = inputs(tmp_path)
    with pytest.raises(PilotError, match='Projekteingaben'):
        pilot.run_opensfm_rgb_pilot(frames, config, executor=fake_engine([]), inputs_unchanged=lambda: False)


def test_bad_import_hash_fails_before_any_engine_stage(tmp_path):
    frames, config = inputs(tmp_path)
    frames[0] = replace(frames[0], content_sha256='f' * 64)
    calls = []
    with pytest.raises(PilotError, match='Arbeitskopie'):
        pilot.run_opensfm_rgb_pilot(frames, config, executor=fake_engine(calls))
    assert calls == []


def test_git_output_or_original_output_and_excessive_budget_write_nothing(tmp_path):
    frames, config = inputs(tmp_path)
    for invalid in (replace(config, output_parent=Path(frames[0].source_file).parent),
                    replace(config, stage_timeout_seconds=3601)):
        with pytest.raises(PilotError):
            pilot.run_opensfm_rgb_pilot(frames, invalid)
    (config.output_parent / '.git').mkdir()
    (config.output_parent / '.git' / 'HEAD').write_text('ref: refs/heads/synthetic\n')
    with pytest.raises(PilotError, match='Git'):
        pilot.run_opensfm_rgb_pilot(frames, config)
    assert list(config.output_parent.iterdir()) == [config.output_parent / '.git']


def test_missing_engine_gps_is_not_replaced_with_camera_guesses(tmp_path):
    frames, config = inputs(tmp_path)
    calls = []
    engine = fake_engine(calls)
    def missing(*args, **kwargs):
        engine(*args, **kwargs)
        folder = args[2]
        if calls[-1] == 'extract_metadata':
            next((folder / 'exif').iterdir()).write_text('{"gps":{}}')
    with pytest.raises(PilotError, match='Kamerapositionen'):
        pilot.run_opensfm_rgb_pilot(frames, config, executor=missing)
    assert calls == ['extract_metadata']


def test_job_environment_is_child_scoped_before_launcher_activation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    seen = []
    monkeypatch.setenv('MPLCONFIGDIR', 'parent-cache-must-remain')
    def launch(args, **kwargs):
        seen.append(kwargs['env'])
        return SimpleNamespace(poll=lambda: 0, returncode=0)
    monkeypatch.setattr(common.subprocess, 'Popen', launch)
    common._execute(Path(sys.executable), ('-I', 'owned.py'), tmp_path, tmp_path / 'own.log',
        lambda: False, env_overrides={'MPLCONFIGDIR': str(tmp_path / 'cache'),
                                     'TEMP': str(tmp_path / 'tmp'), 'VSCMD_SKIP_SENDTELEMETRY': '1'})
    assert os.environ['MPLCONFIGDIR'] == 'parent-cache-must-remain'
    assert seen[0]['MPLCONFIGDIR'] == str(tmp_path / 'cache')
    assert seen[0]['TEMP'] == str(tmp_path / 'tmp')
    assert seen[0]['PROJ_NETWORK'] == 'OFF' and seen[0]['VSCMD_SKIP_SENDTELEMETRY'] == '1'


def test_time_first_folder_and_report_identify_engine_without_sharing_project_name(tmp_path):
    frames, config = inputs(tmp_path)
    result = pilot.run_opensfm_rgb_pilot(frames, replace(config, project_label='Privates Demo-Dach'),
                                       executor=fake_engine([]))
    import re
    assert re.fullmatch(r'[0-9]{8}_[0-9]{6}_OpenSfM_RGB_Privates-Demo-Dach_[a-z0-9_]{8}', result.workspace.name)
    assert metric_path(result.workspace).name.startswith('OpenSfM_RGB_')
    assert not (result.workspace / 'laufzeiten.json').exists()
    report = pilot.read_opensfm_metrics(result.workspace)
    assert report['pipeline'] == 'opensfm_rgb'
    assert report['started_at'] and report['run_id']
    assert 'Privates' not in json.dumps(report) and 'project_label' not in report
    label = pilot.local_run_label(result.workspace)
    assert 'Privates Demo-Dach' in label and 'Start ' in label


def test_old_opensfm_metrics_remain_readable_but_colmap_reports_are_refused(tmp_path):
    folder = tmp_path / 'opensfm-rgb-legacy'
    folder.mkdir()
    manifest = folder / 'job.json'
    manifest.write_text(json.dumps({'expected_engine_source': pilot.ENGINE_SOURCE}))
    report = folder / 'laufzeiten.json'
    report.write_text(json.dumps({'status': 'failed', 'rgb_images': 3,
        'source_file': 'private-must-not-leak',
        'steps': [{'stage': 'extract_metadata', 'status': 'finished',
                   'seconds': 1, 'private_path': 'must-not-leak'}]}))
    assert pilot.read_opensfm_metrics(folder)['pipeline'] == 'opensfm_rgb'
    assert 'leak' not in json.dumps(pilot.read_opensfm_metrics(folder))
    assert 'Berichtsstand' in pilot.local_run_label(folder)
    cache = folder / 'undistorted' / 'depthmaps'
    cache.mkdir(parents=True)
    (cache / 'synthetic.JPG.raw.npz').write_bytes(b'count only; deliberately not a valid depthmap')
    (cache / 'synthetic.JPG.clean.npz').write_bytes(b'count only')
    assert pilot.read_opensfm_metrics(folder)['stored_depthmaps'] == {'raw': 1, 'clean': 1}
    report.write_text(json.dumps({'status': 'failed', 'steps': [
        {'stage': 'COLMAP-Bildabgleich', 'status': 'failed'}]}))
    with pytest.raises(PilotError, match='OpenSfM'):
        pilot.read_opensfm_metrics(folder)
    manifest.write_text('{}')
    with pytest.raises(PilotError, match='OpenSfM'):
        pilot.read_opensfm_metrics(folder)


def test_report_filename_cannot_escape_private_job_folder(tmp_path):
    folder = tmp_path / 'opensfm-rgb-legacy'
    folder.mkdir()
    (folder / 'job.json').write_text(json.dumps({'expected_engine_source': pilot.ENGINE_SOURCE,
                                               'metrics_filename': '../do-not-open.json'}))
    with pytest.raises(PilotError, match='Namen'):
        pilot.read_opensfm_metrics(folder)
