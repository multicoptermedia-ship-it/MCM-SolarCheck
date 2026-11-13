"""Thermal modality boundaries; synthetic M3T payloads, no customer sources."""
from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sqlite3

from PIL import Image
import pytest

from mcm_solarcheck.services import opensfm_rgb_pilot as pilot
from mcm_solarcheck.services import opensfm_dense_continuation as resume
from mcm_solarcheck.services.colmap_openmvs_pilot import (
    PilotError, PilotTimeout, ThermalPilotFrame, read_thermal_project, read_rgb_project,
)
from mcm_solarcheck.thermal.m3t_radiometric import M3TRadiometricParser
from test_m3t_radiometric import radiometric_stream
from test_opensfm_rgb_pilot import inputs, fake_engine, metric_path, reconstruction
from test_opensfm_dense_continuation import stopped_job, engine
from test_opensfm_rgb_launcher import launcher, database


def thermal_inputs(tmp_path):
    frames, config = inputs(tmp_path)
    result = []
    for i, frame in enumerate(frames):
        path = Path(frame.source_file)
        Image.new('RGB', (640, 512), (50, 70, i * 50)).save(path)
        # Deliberately changing raw samples with a distinct centre reference.
        raw = bytearray(b'\x34\x12' * (640 * 512))
        raw[2 * (256 * 640 + 320):2 * (256 * 640 + 320) + 2] = b'\x78\x56'
        path.write_bytes(path.read_bytes() + radiometric_stream(bytes(raw)))
        result.append(ThermalPilotFrame(frame.frame_id, str(path), frame.latitude,
            frame.longitude, frame.altitude_m, sha256(path.read_bytes()).hexdigest()))
    return result, replace(config, modality='thermal')


def thermal_engine(calls, *, focal=.75, model=None, fail=None, mutate=False):
    delegate = fake_engine(calls, model=model, fail=fail)
    def execute(executable, args, folder, log, cancel, **kwargs):
        delegate(executable, args, folder, log, cancel, **kwargs)
        stage = args[args.index('-I') + 2]
        if stage == 'extract_metadata':
            for path in (folder / 'exif').iterdir():
                data = json.loads(path.read_text())
                data.update(width=640, height=512, focal_ratio=focal, camera='camera')
                path.write_text(json.dumps(data))
        if stage == 'reconstruct':
            path = folder / 'reconstruction.json'
            models = json.loads(path.read_text())
            for model in models:
                for camera in model['cameras'].values():
                    camera.update(width=640, height=512, focal=.75)
            path.write_text(json.dumps(models))
        if stage == 'dense_merging' and mutate:
            path = next((folder / 'images').iterdir())
            path.write_bytes(path.read_bytes() + b'changed by synthetic engine')
    return execute


def test_thermal_standard_chain_preserves_raw_and_centre_and_reopens_sanitized_report(tmp_path):
    frames, config = thermal_inputs(tmp_path)
    originals = {f.source_file: Path(f.source_file).read_bytes() for f in frames}
    calls = []
    result = pilot.run_opensfm_thermal_pilot(frames, config, executor=thermal_engine(calls))
    assert calls == list(pilot.STAGES)
    assert result.thermal_images == result.registered_images == 3
    assert result.thermal_geotiff.is_file() and '_OpenSfM_THERMAL_' in result.workspace.name
    assert all(Path(path).read_bytes() == data for path, data in originals.items())
    for path in (result.workspace / 'images').iterdir():
        assert path.read_bytes() in originals.values()
        raw = M3TRadiometricParser().parse_file(path)
        assert raw.samples[256 * 640 + 320] == 0x5678
    assert not (result.workspace / 'camera_models_overrides.json').exists()
    assert json.loads((result.workspace / 'config.yaml').read_text()) == pilot.PROFILE
    report = resume.read_opensfm_run_metrics(result.workspace)
    assert report['pipeline'] == 'opensfm_thermal' and report['rgb_images'] == 0
    assert report['thermal_images'] == report['radiometric_sources_preserved'] == 3
    assert report['thermal_value_kind'] == 'visual' and report['thermal_created']
    assert report['orthophoto_created'] and not report['temperature_matrix_created']
    assert not report['temperature_verified'] and not report['georeferencing_verified']
    text = json.dumps(report)
    assert str(tmp_path) not in text and 'latitude' not in text and 'source_file' not in text
    assert 'OpenSfM THERMAL' in pilot.local_run_label(result.workspace)


@pytest.mark.parametrize('failure', ['mixed', 'rgb', 'no_raw', 'bad_focal', 'partial', 'mutation'])
def test_thermal_rejects_wrong_inputs_unknown_geometry_partial_model_and_changed_copy(tmp_path, failure):
    frames, config = thermal_inputs(tmp_path)
    if failure == 'mixed':
        from mcm_solarcheck.services.colmap_openmvs_pilot import RgbPilotFrame
        frames[0] = RgbPilotFrame(**frames[0].__dict__)
    if failure == 'no_raw':
        path = Path(frames[0].source_file)
        Image.new('RGB', (640, 512)).save(path)
        frames[0] = replace(frames[0], content_sha256=sha256(path.read_bytes()).hexdigest())
    calls = []
    with pytest.raises(PilotError):
        if failure == 'rgb':
            pilot.run_opensfm_rgb_pilot(frames, config, executor=thermal_engine(calls))
        else:
            pilot.run_opensfm_thermal_pilot(frames, config, executor=thermal_engine(calls,
                focal=0 if failure == 'bad_focal' else .75, mutate=failure == 'mutation',
                model=(lambda names: reconstruction(names[:2])) if failure == 'partial' else None))
    if failure in ('mixed', 'rgb', 'no_raw'):
        assert not calls
    if failure in ('bad_focal', 'partial'):
        assert 'undistort' not in calls


def test_thermal_timeout_is_stored_without_approving_an_orthophoto(tmp_path):
    frames, config = thermal_inputs(tmp_path)
    calls, folders = [], []
    delegate = thermal_engine(calls)
    def execute(executable, args, folder, log, cancel, **kwargs):
        if args[args.index('-I') + 2] == 'compute_depthmaps':
            raise PilotTimeout('synthetic')
        delegate(executable, args, folder, log, cancel, **kwargs)
    with pytest.raises(PilotTimeout):
        pilot.run_opensfm_thermal_pilot(frames, config, executor=execute, on_workspace=folders.append)
    report = resume.read_opensfm_run_metrics(folders[0])
    assert report['steps'][-1]['failure_kind'] == 'timeout'
    assert not report['thermal_created'] and not report['orthophoto_created']
    assert report['radiometric_sources_preserved'] == 3


def test_existing_readonly_bridge_separates_modalities_and_launcher_binds_thermal_inputs(tmp_path, monkeypatch):
    db = tmp_path / 'existing.sqlite3'
    database(db)
    with sqlite3.connect(db) as connection:
        connection.executescript('CREATE TABLE thermal_frames AS SELECT * FROM image_frames;'
            "UPDATE thermal_frames SET source_file='thermal.JPG', frame_id='T';"
            "INSERT INTO training_samples VALUES('P','T','thermal','synthetic-thermal-digest');")
    before = db.read_bytes()
    frames = read_thermal_project(db, 'P')
    assert isinstance(frames[0], ThermalPilotFrame) and frames[0].frame_id == 'T'
    assert frames[0].content_sha256 == 'synthetic-thermal-digest'
    assert read_rgb_project(db, 'P')[0].frame_id == 'F'
    module = launcher()
    prefix = tmp_path / 'environment'
    path = prefix / ('python.exe' if os.name == 'nt' else 'bin/python')
    path.parent.mkdir(parents=True)
    path.write_bytes(b'synthetic')
    def run(selected, config, **kwargs):
        assert config.modality == 'thermal' and selected == frames
        assert kwargs['inputs_unchanged']()
        return 'thermal result'
    monkeypatch.setattr(module, 'run_opensfm_thermal_pilot', run)
    monkeypatch.setattr(module, 'run_opensfm_rgb_pilot', lambda *a, **k: pytest.fail('No RGB rerun'))
    assert module.execute(db, 'P', 'conda.exe', prefix, tmp_path,
                          lambda: False, lambda text: None, lambda path: None, modality='thermal') == 'thermal result'
    assert db.read_bytes() == before


def test_thermal_continuation_uses_only_dense_and_reopens_separate_thermal_result(stopped_job):
    folder, config = stopped_job
    for path in [folder / 'job.json', folder / 'laufzeiten.json',
                 folder / 'cache-check-abc12345/Kennzahlen.json']:
        report = json.loads(path.read_text())
        report.update(pipeline='opensfm_thermal', rgb_images=0, thermal_images=3,
            radiometric_sources_preserved=3, thermal_value_kind='visual',
            thermal_created=False, temperature_verified=False, georeferencing_verified=False,
            temperature_matrix_created=False)
        path.write_text(json.dumps(report))
    (folder / 'exif').mkdir()
    for i in range(1, 4):
        (folder / 'exif' / f'{i:06d}.JPG.exif').write_text(json.dumps(dict(
            width=640, height=512, focal_ratio=.75, camera='camera')))
    path = folder / 'reconstruction.json'
    model = json.loads(path.read_text())
    model[0]['cameras']['camera'].update(width=640, height=512, focal=.75)
    path.write_text(json.dumps(model))
    calls = []
    with pytest.raises(PilotError, match='getrennt'):
        resume.run_opensfm_dense_continuation(folder, config, executor=engine(calls))
    result = resume.run_opensfm_dense_continuation(folder, replace(config, modality='thermal'), executor=engine(calls))
    assert calls == ['cache_check', *pilot.STAGES[7:]]
    assert result.thermal_images == 3 and result.thermal_geotiff.is_file()
    report = resume.read_opensfm_run_metrics(folder)
    assert report['status'] == 'failed' and report['dense_continuation']['status'] == 'finished'
    assert report['dense_continuation']['thermal_created'] and not report['temperature_matrix_created']
    assert not resume.can_continue_opensfm(report)


def test_thermal_entry_point_opens_only_explicit_thermal_mode(monkeypatch):
    import sys
    module = launcher()
    monkeypatch.setitem(sys.modules, 'MCM_SolarCheck_OPENSFM_RGB_PILOT', module)
    path = Path(__file__).resolve().parents[1] / 'scripts/MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py'
    spec = importlib.util.spec_from_file_location('thermal_launcher', path)
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    seen = []
    monkeypatch.setattr(module, 'window', lambda **kwargs: seen.append(kwargs))
    assert entry.main([], modality='thermal') == 0
    assert seen == [dict(conda=module.CONDA, environment=module.ENVIRONMENT, modality='thermal')]


def test_rgb_camera_geometry_cannot_be_accepted_as_thermal(tmp_path):
    frames, config = thermal_inputs(tmp_path)
    calls = []
    delegate = thermal_engine(calls)
    def execute(executable, args, folder, log, cancel, **kwargs):
        delegate(executable, args, folder, log, cancel, **kwargs)
        if args[args.index('-I') + 2] == 'reconstruct':
            path = folder / 'reconstruction.json'
            models = json.loads(path.read_text())
            models[0]['cameras']['camera'].update(width=4000, height=3000)
            path.write_text(json.dumps(models))
    with pytest.raises(PilotError, match='Thermal-Kameramodell'):
        pilot.run_opensfm_thermal_pilot(frames, config, executor=execute)
    assert calls[-1] == 'reconstruct'


@pytest.mark.parametrize('name', ['src/mcm_solarcheck/services/opensfm_rgb_pilot.py',
    'src/mcm_solarcheck/services/opensfm_dense_continuation.py',
    'scripts/MCM_SolarCheck_OPENSFM_RGB_PILOT.py', 'scripts/MCM_SolarCheck_OPENSFM_STAGE.py'])
def test_delivered_runtime_files_compile_with_the_tested_interpreter(name):
    path = Path(__file__).resolve().parents[1] / name
    # Each native CI interpreter must compile the actual delivered scripts.
    # ast feature_version on 3.12 does not reject every PEP701-only expression.
    compile(path.read_text(encoding='utf-8'), name, 'exec')



def test_mpo_working_copies_reach_the_full_pipeline_and_opencv_reads_the_same_primary_image(tmp_path):
    import cv2
    frames, config = thermal_inputs(tmp_path)
    for i, frame in enumerate(frames):
        path = Path(frame.source_file)
        Image.new('RGB', (640, 512), (20, 80, 140)).save(path, format='MPO', save_all=True,
            append_images=[Image.new('RGB', (640, 512), (200, 60, 20))])
        path.write_bytes(path.read_bytes() + radiometric_stream(b'\x34\x12' * (640 * 512)))
        frames[i] = replace(frame, content_sha256=sha256(path.read_bytes()).hexdigest())
        with Image.open(path) as picture:
            assert picture.format == 'MPO' and picture.n_frames == 2
            expected = picture.convert('RGB').getpixel((320, 256))
        decoded = cv2.imread(str(path))
        assert decoded.shape == (512, 640, 3)
        assert max(abs(int(a) - int(b)) for a, b in zip(decoded[256, 320, ::-1], expected)) <= 2
    before = {frame.source_file: Path(frame.source_file).read_bytes() for frame in frames}
    calls = []
    result = pilot.run_opensfm_thermal_pilot(frames, config, executor=thermal_engine(calls))
    assert calls == list(pilot.STAGES)
    assert result.thermal_geotiff.is_file()
    report = resume.read_opensfm_run_metrics(result.workspace)
    assert report['thermal_images'] == report['radiometric_sources_preserved'] == 3
    assert report['thermal_input_failure'] is None
    assert not report['temperature_verified'] and not report['temperature_matrix_created']
    assert all(Path(name).read_bytes() == content for name, content in before.items())
    assert all(path.read_bytes() in before.values() for path in (result.workspace / 'images').iterdir())


@pytest.mark.parametrize('kind', ['raw_raster', 'preview_unreadable', 'preview_format', 'preview_dimensions'])
def test_failed_copy_check_reports_a_fixed_reason_without_starting_engine_or_exposing_sources(tmp_path, kind):
    frames, config = thermal_inputs(tmp_path)
    path = Path(frames[0].source_file)
    if kind == 'preview_unreadable':
        path.write_bytes(b'not an image')
    elif kind == 'preview_format':
        Image.new('RGB', (640, 512)).save(path, format='PNG')
    elif kind == 'preview_dimensions':
        # Primary RGB-sized component must not silently switch to secondary thermal.
        Image.new('RGB', (1200, 900)).save(path, format='MPO', save_all=True,
            append_images=[Image.new('RGB', (640, 512))])
    else:
        Image.new('RGB', (640, 512)).save(path, format='JPEG')
    if kind != 'raw_raster':
        path.write_bytes(path.read_bytes() + radiometric_stream(b'\x34\x12' * (640 * 512)))
    frames[0] = replace(frames[0], content_sha256=sha256(path.read_bytes()).hexdigest())
    calls, folders = [], []
    with pytest.raises(pilot.ThermalInputError) as caught:
        pilot.run_opensfm_thermal_pilot(frames, config, executor=thermal_engine(calls), on_workspace=folders.append)
    assert caught.value.kind == kind
    assert str(tmp_path) not in str(caught.value) and not calls
    report = resume.read_opensfm_run_metrics(folders[0])
    assert report['thermal_images'] == 3 and report['thermal_input_failure'] == kind
    assert report['status'] == 'failed' and not report['orthophoto_created']
    assert not report['thermal_created'] and report['steps'] == []
    assert 'source_file' not in json.dumps(report) and str(tmp_path) not in json.dumps(report)
