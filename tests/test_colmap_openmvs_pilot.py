"""Real files/CRS/SQLite + fake external tools; NOT a real photogrammetry test."""
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

import numpy as np
from PIL import Image
import pytest
import rasterio

from mcm_solarcheck.services import colmap_openmvs_pilot as pilot
from test_openmvs_orthomap import write_mesh


@pytest.fixture
def scene(tmp_path):
    sources = tmp_path / 'private originals'
    sources.mkdir()
    frames = []
    for i, (lat, lon) in enumerate([(50.1, 8.61), (50.1001, 8.61), (50.1, 8.6101), (50.1001, 8.6101)]):
        path = sources / f'image & ({i}).JPG'
        Image.new('RGB', (32, 24), (30, 60, 90)).save(path)
        frames.append(pilot.RgbPilotFrame(str(i), str(path), lat, lon, 140,
                                         sha256(path.read_bytes()).hexdigest()))
    colmap = tmp_path / 'tool with spaces' / 'bin' / 'colmap.exe'
    colmap.parent.mkdir(parents=True)
    colmap.touch()
    mvs = tmp_path / 'open mvs'
    mvs.mkdir()
    for name in ('InterfaceCOLMAP', 'DensifyPointCloud', 'ReconstructMesh', 'RefineMesh', 'TextureMesh'):
        (mvs / (name + ('.exe' if os.name == 'nt' else ''))).touch()
    output = tmp_path / 'private outputs'
    output.mkdir()
    config = pilot.RgbPilotConfig(colmap, mvs, output, orthomap_resolution=128)
    return tuple(frames), config


def feature_cache(path, count=4):
    """Minimal synthetic COLMAP SQLite data, not extracted image features."""
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE images(image_id INTEGER PRIMARY KEY,name TEXT UNIQUE);'
                        'CREATE TABLE keypoints(image_id INTEGER PRIMARY KEY,rows INTEGER,cols INTEGER,data BLOB);'
                        'CREATE TABLE descriptors(image_id INTEGER PRIMARY KEY,rows INTEGER,cols INTEGER,data BLOB);'
                        'CREATE TABLE matches(pair_id INTEGER PRIMARY KEY,rows INTEGER,cols INTEGER,data BLOB);'
                        'CREATE TABLE two_view_geometries(pair_id INTEGER PRIMARY KEY,rows INTEGER,cols INTEGER,data BLOB);')
        for i in range(1, count + 1):
            db.execute('INSERT INTO images VALUES(?,?)', (i, f'{i:06d}.JPG'))
            db.execute('INSERT INTO keypoints VALUES(?,1,4,?)', (i, bytes(16)))
            db.execute('INSERT INTO descriptors VALUES(?,1,128,?)', (i, bytes(128)))


def cached_pair(path, second=2):
    with sqlite3.connect(path) as db:
        # A completed pair may have zero inliers; COLMAP caches that outcome too.
        for table in ('matches', 'two_view_geometries'):
            db.execute(f'INSERT OR IGNORE INTO {table} VALUES(?,0,2,NULL)', (2147483647 + second,))


def fake_tools(monkeypatch, *, count=4, models=1, fail=None, failure=None, version='3.12.6', after=None, help_hook=None):
    calls = []
    def execute(executable, args, folder, log, cancel, **kwargs):
        args = tuple(map(str, args))
        calls.append((executable.name, args))
        if args[0] in ('-h', '--help'):
            log.write_text('COLMAP ' + version if executable.name.lower().startswith('colmap')
                           else 'OpenMVS x64 v2.4.0\n--cuda-device', encoding='utf-8')
            if help_hook:
                help_hook(executable, args, folder, log)
            return
        log.write_text('Synthetic private tool output; not user data.')
        if args[0] == 'feature_extractor':
            feature_cache(folder / 'features.db')
        if args[0] == 'exhaustive_matcher':
            cached_pair(folder / 'features.db')
        if args[0] == fail:
            raise failure or pilot.PilotError('PRIVATE_RAW_EXCEPTION_MUST_NOT_ESCAPE')
        if executable.stem == 'TextureMesh' and args[0] == 'refined.mvs' and '--orthographic-image-resolution' in args:
            raise pilot.PilotError('upstream early branch skips necessary texturing')
        if args[0] == 'mapper':
            for i in range(models):
                p = folder / 'sparse' / str(i)
                p.mkdir()
                (p / 'images.bin').touch()
        if args[0] == 'model_converter':
            text = '# COLMAP images\n'
            for i in range(1, count + 1):
                text += f'{i} 1 0 0 0 0 0 0 1 {i:06d}.JPG\n\n'
            (folder / 'model-text' / 'images.txt').write_text(text)
        if executable.stem == 'TextureMesh' and '--orthographic-image-resolution' in args:
            write_mesh(folder / 'ortho.ply')
            pixels = np.full((64, 128, 4), (30, 60, 90, 255), dtype='uint8')
            pixels[:, 0, 3] = 0
            Image.fromarray(pixels).save(folder / 'ortho_orthomap.png')
        if after:
            after(executable, args, folder)
    monkeypatch.setattr(pilot, '_execute', execute)
    return calls


def test_pilot_to_persisted_geotiff_preserves_sources_and_times_each_stage(scene, monkeypatch):
    frames, config = scene
    before = {f.source_file: Path(f.source_file).read_bytes() for f in frames}
    calls = fake_tools(monkeypatch)
    result = pilot.run_rgb_pilot(frames, config)
    assert result.rgb_geotiff.exists()
    assert {f.source_file: Path(f.source_file).read_bytes() for f in frames} == before
    for i, frame in enumerate(frames, 1):
        assert (result.workspace / 'images' / f'{i:06d}.JPG').read_bytes() == before[frame.source_file]
    mapping = json.loads((result.workspace/'input-map.json').read_text())
    assert [item['frame_id'] for item in mapping] == [frame.frame_id for frame in frames]
    assert [item['content_sha256'] for item in mapping] == [frame.content_sha256 for frame in frames]
    refs = [list(map(float, line.split()[1:])) for line in (result.workspace/'references.txt').read_text().splitlines()]
    assert np.abs(refs).max() < 100  # actual local metric coordinates, not float UTM mesh coordinates
    record = json.loads((result.workspace/'job.json').read_text())
    assert record['status'] == 'rgb_ready_unverified'
    assert record['crs'] == 'EPSG:32632'
    assert record['temperature_verified'] is record['georeferencing_verified'] is record['thermal_created'] is False
    assert all(step['seconds'] >= 0 and step['status'] == 'finished' for step in record['steps'])
    summary = (result.workspace / 'laufzeiten.json').read_text()
    assert 'source_file' not in summary and 'origin_projected' not in summary
    with rasterio.open(result.rgb_geotiff) as src:
        assert src.crs.to_epsg() == 32632
        assert src.transform.c > 100000 and src.transform.f > 5000000
        assert src.dataset_mask()[:, 0].sum() == 0
    assert all(('--cuda-device', '-2') == args[-4:-2] or '-2' in args
               for name, args in calls if name.startswith('Densify') and args[0] != '--help')
    for name, args in calls:
        if name.startswith(('ReconstructMesh', 'RefineMesh', 'TextureMesh')) and args[0] != '--help':
            assert args[-2:] == ('--archive-type', '2')
    texture_calls = [args for name, args in calls if name.startswith('TextureMesh') and args[0] != '--help']
    assert len(texture_calls) == 2
    assert '--orthographic-image-resolution' not in texture_calls[0]
    assert texture_calls[1][0] == 'textured.mvs' and '--mesh-file' in texture_calls[1]


@pytest.mark.parametrize('count,models', [(3, 1), (4, 2), (4, 0)])
def test_incomplete_or_split_camera_solution_never_produces_a_partial_overview(scene, monkeypatch, count, models):
    frames, config = scene
    calls = fake_tools(monkeypatch, count=count, models=models)
    with pytest.raises(pilot.PilotError):
        pilot.run_rgb_pilot(frames, config)
    job = next(config.output_parent.iterdir())
    assert json.loads((job/'job.json').read_text())['status'] == 'failed'
    assert not (job/'rgb_ortho.tif').exists()
    assert not any(name.startswith('Densify') and args[0] != '--help' for name, args in calls)


def test_changed_project_signature_and_changed_source_do_not_publish(scene, monkeypatch):
    frames, config = scene
    fake_tools(monkeypatch)
    with pytest.raises(pilot.PilotError, match='Projekteingaben'):
        pilot.run_rgb_pilot(frames, config, inputs_unchanged=lambda: False)
    def alter(exe, args, folder):
        if exe.stem == 'TextureMesh':
            path = Path(frames[0].source_file)
            path.write_bytes(path.read_bytes() + b'changed')
    fake_tools(monkeypatch, after=alter)
    with pytest.raises(pilot.PilotError, match='Originalquelle'):
        pilot.run_rgb_pilot(frames, config)
    assert not list(config.output_parent.glob('*/rgb_ortho.tif'))


def test_wrong_colmap_version_fails_before_any_original_copy(scene, monkeypatch):
    frames, config = scene
    fake_tools(monkeypatch, version='4.2.1')
    with pytest.raises(pilot.PilotError, match='3.12.6'):
        pilot.run_rgb_pilot(frames, config)
    assert not list(config.output_parent.glob('*/images'))


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16'])
def test_openmvs_native_log_only_help_can_complete_pilot(scene, monkeypatch, encoding):
    """Windows CONOUT$ may leave captured stdout empty; app logs remain usable."""
    frames, config = scene
    def native_help(executable, args, folder, log):
        if args[0] != '--help':
            return
        assert args[1:] == ('--working-folder', str(folder) + os.sep)
        assert not (folder / 'images').exists()
        log.write_bytes(b'')
        (folder / (executable.stem + '-fresh.log')).write_text(
            '16:30:00 [App     ] OpenMVS x64 v2.4.0\n--cuda-device\n', encoding=encoding)
    calls = fake_tools(monkeypatch, help_hook=native_help)
    result = pilot.run_rgb_pilot(frames, config)
    assert result.rgb_geotiff.exists()
    assert len(list(result.workspace.glob('*-fresh.log'))) == 5
    # CPU selection must also be read from the native help, not empty stdout.
    assert all('--cuda-device' in args and args[args.index('--cuda-device') + 1] == '-2'
               for name, args in calls if name.startswith('Densify') and args[0] != '--help')


@pytest.mark.parametrize('case,reason', [
    ('different', 'OpenMVS 2.4.1 erkannt'),
    ('missing', 'Versionsausgabe nicht erkannt'),
    ('stale', 'Versionsausgabe nicht erkannt'),
    ('unrelated', 'Versionsausgabe nicht erkannt'),
    ('conflicting', 'widerspruechliche Versionsangaben'),
])
def test_openmvs_rejects_wrong_missing_stale_or_foreign_version_before_copy(scene, monkeypatch, case, reason):
    frames, config = scene
    def version_help(executable, args, folder, log):
        if args[0] == '-h':
            if case == 'stale':
                (folder / 'InterfaceCOLMAP-old.log').write_text('OpenMVS x64 v2.4.0')
            return
        log.write_text('OpenMVS x64 v2.4.1' if case == 'conflicting' else '')
        if case in ('different', 'conflicting', 'unrelated'):
            prefix = 'TextureMesh' if case == 'unrelated' else executable.stem
            version = '2.4.1' if case == 'different' else '2.4.0'
            (folder / (prefix + '-fresh.log')).write_text('OpenMVS x64 v' + version)
    calls = fake_tools(monkeypatch, help_hook=version_help)
    with pytest.raises(pilot.PilotError, match='InterfaceCOLMAP: ' + reason) as error:
        pilot.run_rgb_pilot(frames, config)
    assert 'installieren' not in str(error.value).lower()
    assert not list(config.output_parent.glob('*/images'))
    assert not any(args[0] == 'feature_extractor' for _, args in calls)
    job = next(config.output_parent.iterdir())
    assert json.loads((job / 'job.json').read_text())['status'] == 'failed'


def test_errors_are_stage_only_and_cancelled_job_stays_private(scene, monkeypatch):
    frames, config = scene
    fake_tools(monkeypatch, fail='mapper')
    with pytest.raises(pilot.PilotError) as info:
        pilot.run_rgb_pilot(frames, config)
    assert 'Kameraloesung' in str(info.value) and 'PRIVATE_RAW' not in str(info.value)
    assert all('PRIVATE_RAW' not in p.read_text() for p in config.output_parent.glob('*/laufzeiten.json'))
    flag = []
    fake_tools(monkeypatch, after=lambda exe, args, folder: flag.append(True) if args[0]=='mapper' else None)
    with pytest.raises(pilot.PilotCancelled):
        pilot.run_rgb_pilot(frames, config, should_cancel=lambda: bool(flag))
    assert any(json.loads(p.read_text())['status']=='cancelled' for p in config.output_parent.glob('*/job.json'))


@pytest.mark.parametrize('failure', ['gps', 'checksum', 'nested', 'git', 'missing_tool'])
def test_invalid_inputs_cannot_run_a_reconstruction(scene, monkeypatch, failure):
    frames, config = scene
    if failure == 'gps':
        frames = (replace(frames[0], latitude=None), *frames[1:])
    elif failure == 'checksum':
        frames = (replace(frames[0], content_sha256='0'*64), *frames[1:])
    elif failure == 'nested':
        config = replace(config, output_parent=Path(frames[0].source_file).parent)
    elif failure == 'git':
        (config.output_parent/'.git').mkdir()
        (config.output_parent/'.git'/'HEAD').touch()
    else:
        next(config.openmvs.iterdir()).unlink()
    calls = fake_tools(monkeypatch)
    with pytest.raises((pilot.PilotError, RuntimeError)):
        pilot.run_rgb_pilot(frames, config)
    assert not any(args and args[0]=='feature_extractor' for _, args in calls)


def test_sqlite_loader_is_read_only_no_schema_changes_and_resolves_existing_paths(tmp_path):
    path = tmp_path/'existing.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE projects(project_id TEXT,name TEXT);'
          'CREATE TABLE image_frames(project_id TEXT,frame_id TEXT,source_file TEXT,latitude REAL,longitude REAL,altitude_m REAL);'
          'CREATE TABLE training_samples(project_id TEXT,source_frame_id TEXT,modality TEXT,content_sha256 TEXT);'
          "INSERT INTO projects VALUES('P','Existing');"
          "INSERT INTO image_frames VALUES('P','F','images/photo.JPG',50.1,8.6,140);")
    before = path.read_bytes()
    assert pilot.project_choices(path) == (('P', 'Existing'),)
    frame, = pilot.read_rgb_project(path, 'P')
    assert frame.source_file == str(tmp_path/'images'/'photo.JPG')
    assert path.read_bytes() == before
    with pytest.raises(pilot.PilotError):
        pilot.read_rgb_project(path, 'not-an-existing-project')


def test_process_argv_is_literal_and_proj_is_offline(tmp_path):
    executable = Path(sys.executable)
    payload = 'literal & $(not a shell command)'
    log = tmp_path/'process.log'
    pilot._execute(executable, ('-c', 'import os,sys;print(sys.argv[1]);print(os.environ["PROJ_NETWORK"])', payload),
                   tmp_path, log, lambda: False)
    assert log.read_text().splitlines() == [payload, 'OFF']


def test_owned_process_is_cancelled_and_returns_promptly(tmp_path):
    start = time.monotonic()
    with pytest.raises(pilot.PilotCancelled):
        pilot._execute(Path(sys.executable), ('-c', 'import time;time.sleep(60)'), tmp_path,
                       tmp_path/'process.log', lambda: time.monotonic()-start > .3)
    assert time.monotonic()-start < 10


def test_real_process_timeout_is_distinct_and_owned_process_is_stopped(tmp_path, monkeypatch):
    stopped = []
    original_stop = pilot._stop_process
    def stop(process):
        original_stop(process)
        stopped.append(process.poll())
    monkeypatch.setattr(pilot, '_stop_process', stop)
    with pytest.raises(pilot.PilotTimeout):
        pilot._execute(Path(sys.executable), ('-c', 'import time;time.sleep(60)'), tmp_path,
                       tmp_path / 'timeout.log', lambda: False, timeout=.1)
    assert len(stopped) == 1 and stopped[0] is not None
    with pytest.raises(pilot.PilotProcessExit) as error:
        pilot._execute(Path(sys.executable), ('-c', 'raise SystemExit(7)'), tmp_path,
                       tmp_path / 'exit.log', lambda: False)
    assert error.value.returncode == 7


@pytest.mark.parametrize('failure,kind,message', [
    (pilot.PilotTimeout('PRIVATE_MESSAGE'), 'timeout', 'Zeitlimit nach 24 Stunden'),
    (pilot.PilotProcessExit(17), 'process_exit', 'Programm mit Code 17'),
])
def test_stage_failure_reason_is_visible_and_persisted_without_raw_output(scene, monkeypatch, failure, kind, message):
    frames, config = scene
    calls = fake_tools(monkeypatch, fail='exhaustive_matcher', failure=failure)
    with pytest.raises(pilot.PilotError, match=message) as error:
        pilot.run_rgb_pilot(frames, config)
    assert 'PRIVATE' not in str(error.value)
    summary = json.loads(next(config.output_parent.glob('*/laufzeiten.json')).read_text())
    assert summary['status'] == 'failed'
    step = summary['steps'][-1]
    assert step['failure_kind'] == kind and step['timeout_seconds'] == 86400
    assert not any(args[0] == 'mapper' for _, args in calls)


def stopped_job(scene, monkeypatch):
    frames, config = scene
    fake_tools(monkeypatch, fail='exhaustive_matcher', failure=pilot.PilotTimeout())
    with pytest.raises(pilot.PilotTimeout):
        pilot.run_rgb_pilot(frames, config)
    return next(config.output_parent.iterdir())


def test_resume_preserves_committed_wal_pairs_skips_features_and_reaches_saved_geotiff(scene, monkeypatch):
    frames, config = scene
    old = stopped_job(scene, monkeypatch)
    metadata = {name: (old / name).read_bytes() for name in ('job.json', 'laufzeiten.json', 'input-map.json')}
    with sqlite3.connect(old / 'features.db') as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        for table in ('matches', 'two_view_geometries'):
            writer.execute(f'INSERT INTO {table} VALUES(?,0,2,NULL)', (2147483650,))
        writer.commit()  # keep writer open: the committed second pair remains in WAL
        before_db = (old / 'features.db').read_bytes()
        seen = []
        def observe(executable, args, folder):
            if args[0] == 'exhaustive_matcher':
                with sqlite3.connect(folder / 'features.db') as copied:
                    seen.append(copied.execute('SELECT count(*) FROM matches').fetchone()[0])
        calls = fake_tools(monkeypatch, after=observe)
        result = pilot.run_rgb_pilot(frames, replace(config, resume_job=old))
        assert seen == [2]
        assert (old / 'features.db').read_bytes() == before_db
        assert writer.execute('SELECT count(*) FROM matches').fetchone()[0] == 2
    assert {name: (old / name).read_bytes() for name in metadata} == metadata
    assert result.workspace != old and result.rgb_geotiff.exists()
    assert not any(args[0] == 'feature_extractor' for _, args in calls)
    saved = json.loads((result.workspace / 'laufzeiten.json').read_text())
    reused, = [s for s in saved['steps'] if s['status'] == 'reused']
    assert reused['cached_images'] == 4 and reused['cached_pairs'] == 2
    assert str(old) not in (result.workspace / 'laufzeiten.json').read_text()


@pytest.mark.parametrize('damage', ['signature', 'mapping', 'running', 'other_stage', 'cache_names', 'cache_features', 'corrupt'])
def test_bad_resume_never_silently_reextracts_features_or_publishes(scene, monkeypatch, damage):
    frames, config = scene
    old = stopped_job(scene, monkeypatch)
    record = json.loads((old / 'job.json').read_text())
    if damage == 'signature':
        record['input_signature'] = '0' * 64
    elif damage == 'running':
        record['status'] = 'running'
    elif damage == 'other_stage':
        record['steps'][-1]['stage'] = 'COLMAP-Kameraloesung'
    elif damage == 'mapping':
        mapping = json.loads((old / 'input-map.json').read_text())
        mapping[0]['frame_id'] = 'wrong frame'
        (old / 'input-map.json').write_text(json.dumps(mapping))
    elif damage in ('cache_names', 'cache_features'):
        with sqlite3.connect(old / 'features.db') as db:
            db.execute("UPDATE images SET name='wrong.JPG' WHERE image_id=1" if damage == 'cache_names'
                       else 'DELETE FROM descriptors WHERE image_id=1')
    else:
        (old / 'features.db').write_bytes(b'not sqlite')
    (old / 'job.json').write_text(json.dumps(record))
    calls = fake_tools(monkeypatch)
    with pytest.raises(pilot.PilotError):
        pilot.run_rgb_pilot(frames, replace(config, resume_job=old))
    assert not any(args[0] in ('feature_extractor', 'exhaustive_matcher', 'mapper') for _, args in calls)
    assert not list(config.output_parent.glob('*/rgb_ortho.tif'))


def test_resume_binds_original_bytes_even_when_import_has_no_checksum(scene, monkeypatch):
    frames, config = scene
    frames = tuple(replace(f, content_sha256=None) for f in frames)
    old = stopped_job((frames, config), monkeypatch)
    path = Path(frames[0].source_file)
    path.write_bytes(path.read_bytes() + b'changed')
    calls = fake_tools(monkeypatch)
    with pytest.raises((pilot.PilotError, RuntimeError)):
        pilot.run_rgb_pilot(frames, replace(config, resume_job=old))
    assert not any(args[0] == 'exhaustive_matcher' for _, args in calls)
    assert not list(config.output_parent.glob('*/rgb_ortho.tif'))


def test_cancel_during_sqlite_snapshot_preserves_old_job_and_does_not_start_matching(scene, monkeypatch):
    frames, config = scene
    old = stopped_job(scene, monkeypatch)
    before = (old / 'features.db').read_bytes()
    cancelled = []
    calls = fake_tools(monkeypatch)
    def progress(text):
        if text.startswith('Vorhandene Merkmale'):
            cancelled.append(True)
    with pytest.raises(pilot.PilotCancelled):
        pilot.run_rgb_pilot(frames, replace(config, resume_job=old),
                            should_cancel=lambda: bool(cancelled), on_progress=progress)
    assert (old / 'features.db').read_bytes() == before
    assert not any(args[0] in ('feature_extractor', 'exhaustive_matcher') for _, args in calls)
    assert any(json.loads(p.read_text())['status'] == 'cancelled' for p in config.output_parent.glob('*/job.json'))


def test_sqlite_validation_can_be_cancelled_after_backup(tmp_path):
    source = tmp_path / 'features.db'
    feature_cache(source, count=1000)
    before = source.read_bytes()
    polls = []
    def cancel():
        polls.append(True)
        return len(polls) > 1  # first poll is the small backup; then interrupt SQL
    with pytest.raises(pilot.PilotCancelled):
        pilot._snapshot_feature_cache(source, tmp_path / 'copy.db',
                                      {f'{i:06d}.JPG' for i in range(1, 1001)}, cancel)
    assert len(polls) > 1 and source.read_bytes() == before
