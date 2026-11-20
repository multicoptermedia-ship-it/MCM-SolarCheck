"""MicMac orchestration contracts with synthetic rasters and a fake CLI.

These tests DO NOT certify MicMac reconstruction or real orthophoto quality.
"""
import hashlib
import json
from pathlib import Path
import re
import socket
import sys
import time

import numpy as np
from PIL import Image
import pytest
import rasterio
from rasterio.transform import from_origin

from mcm_solarcheck.domain.models import ImageFrame, Position, ThermalFrame
from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.services import micmac_orthophotos as mm
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('local reconstruction must not call a network service')
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture
def scene(tmp_path):
    service = build_offline_services(tmp_path / 'project.sqlite').projects
    service.create_project('P1', 'Synthetic')
    service.create_project('P2', 'Other')
    files = []
    for modality in ('rgb', 'thermal'):
        folder = tmp_path / modality
        folder.mkdir()
        for i, (latitude, longitude) in enumerate(((50.1, 8.61), (50.1001, 8.61), (50.1, 8.6101))):
            path = folder / f'capture & ({i}).JPG'
            cls = ImageFrame if modality == 'rgb' else ThermalFrame
            frame = cls(str(i), path, position=Position(latitude, longitude, 140.), width=32, height=24)
            if modality == 'rgb':
                service.database.save_image_frames('P1', (frame,))
            else:
                quality = ThermalQualityResult(ThermalQualityGrade.PASS, (), RawThermalStatistics(1, 10, 5., 5., 9., 10., 9))
                service.database.save_thermal_frame('P1', frame, quality)
            Image.new('RGB', (32, 24), (70, 80, 90)).save(path)
            files.append(path)
    output = tmp_path / 'private outputs'
    output.mkdir()
    exe = tmp_path / 'tool with spaces' / 'mm3d.exe'
    exe.parent.mkdir()
    exe.write_bytes(b'fake executable: test replaces only process execution')
    return service, exe, output, files


def fake_micmac(monkeypatch, *, fail_layer=None, fail_stage='Tapas', after_command=None, worldfile=True):
    calls = []
    def execute(executable, args, cwd, log, should_cancel):
        calls.append((cwd.name, args))
        log.write_text('synthetic private process output', encoding='utf-8')
        if cwd.name == fail_layer and args[0] == fail_stage:
            raise mm.MicMacError(f'MicMac-Stufe {fail_stage} fehlgeschlagen (Code 1); lokales Protokoll prüfen.')
        if args[0] == 'OriConvert':
            # Upstream OriConvert instantiates cameras even for center-only
            # input. With AddCalib=0 neither Interne nor FileInterne exists:
            # reproduce that CLI boundary, not a photogrammetry algorithm.
            options = dict(arg.split('=', 1) for arg in args[4:] if '=' in arg)
            if options.get('AddCalib', '1') == '0':
                raise mm.MicMacError('Cam_Gen_From_XML, Interne : ni Val ni File')
        if args[0] == 'Malt':
            # Observed nested Malt invocation drops repetition braces. Reproduce
            # that transport boundary: all numbered copies must still match.
            nested_pattern = args[2].replace('{', '').replace('}', '')
            copies = {path.name for path in cwd.glob('*.JPG')}
            selected = {name for name in copies if re.fullmatch(nested_pattern, name)}
            if not selected:
                raise mm.MicMacError('Empty list for StdGetListOfFile')
            assert selected == copies
            for unrelated in ('1.JPG', '1234567.JPG', '000001-small.JPG', 'preview.JPG'):
                assert re.fullmatch(nested_pattern, unrelated) is None
        if args[0] == 'Tawny':
            from pyproj import Transformer
            x, y = Transformer.from_crs(4326, 32632, always_xy=True).transform(8.61, 50.1)
            folder = cwd / 'Ortho-MEC-Malt'
            folder.mkdir()
            path = folder / 'Orthophotomosaic.tif'
            # Known coordinates model an external MicMac worldfile output.
            with pytest.warns(rasterio.errors.NotGeoreferencedWarning):
                with rasterio.open(path, 'w', driver='GTiff', width=32, height=24,
                                   count=3, dtype='uint8') as dataset:
                    dataset.write(np.full((3, 24, 32), 70 if cwd.name == 'rgb' else 180, np.uint8))
                    mask = np.full((24, 32), 255, np.uint8)
                    mask[:, 0] = 0
                    dataset.write_mask(mask)
            if worldfile:
                path.with_suffix('.tfw').write_text(f'1\n0\n0\n-1\n{x+.5}\n{y-.5}\n', encoding='ascii')
        if after_command:
            after_command(cwd.name, args)
    monkeypatch.setattr(mm, '_execute', execute)
    return calls


def test_standard_pipeline_to_registered_pair_preserves_sources_masks_and_reopens(scene, monkeypatch):
    service, exe, output, files = scene
    original = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before = service.state('P1')
    calls = fake_micmac(monkeypatch)
    result = mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
    assert result.crs == 'EPSG:32632'
    assert [c[1][0] for c in calls] == ['Tapioca', 'Tapas', 'OriConvert', 'CenterBascule', 'Malt', 'Tawny'] * 2
    assert all(c[1][-2:] == ('Detect=mm3d:Digeo', 'Match=mm3d:Ann') for c in calls if c[1][0] == 'Tapioca')
    assert all('RadiomEgal=0' in c[1] for c in calls if c[1][0] == 'Tawny')
    assert service.project_orthophoto_pairs('P1') == ()  # no premature database writes
    positions = (result.workspace / 'rgb' / 'positions.txt').read_text()
    assert positions.startswith('#F=N X Y Z\n000001.JPG ')
    assert positions.splitlines()[1].endswith(' 140.000000000')
    for i, source in enumerate(files[:3], 1):
        assert (result.workspace / 'rgb' / f'{i:06d}.JPG').read_bytes() == source.read_bytes()
    for path in (result.rgb_geotiff, result.thermal_geotiff):
        with rasterio.open(path) as dataset:
            assert dataset.crs.to_epsg() == 32632
            assert dataset.transform.a == 1 and dataset.transform.e == -1
            assert not dataset.dataset_mask()[:, 0].any()
            assert dataset.dataset_mask()[:, 1:].all()
    record = json.loads((result.workspace / 'job.json').read_text())
    assert record['status'] == 'rasters_ready_unverified'
    assert record['georeferencing_verified'] is record['temperature_verified'] is False
    pair = service.register_project_orthophoto_pair('P1', result.rgb_geotiff, result.thermal_geotiff, source_kind='micmac')
    reopened = build_offline_services(service.database.path).projects
    assert reopened.project_orthophoto_pairs('P1') == (pair,)
    assert reopened.project_orthophoto_pairs('P2') == ()
    assert pair['inspection_status'] == 'metadata_only'
    assert service.state('P1') == before
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files} == original


@pytest.mark.parametrize('crs', ('EPSG:4326', 'EPSG:2263', 'invalid'))
def test_invalid_or_nonmetric_crs_never_starts_micmac(scene, monkeypatch, crs):
    service, exe, output, _ = scene
    calls = fake_micmac(monkeypatch)
    with pytest.raises(mm.MicMacError):
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output, target_crs=crs)
    assert calls == [] and list(output.iterdir()) == []


@pytest.mark.parametrize('column', ('latitude', 'longitude', 'altitude_m'))
def test_missing_coordinates_are_not_replaced_with_guesses(scene, monkeypatch, column):
    service, exe, output, _ = scene
    with service.database.connect() as db:
        db.execute(f'UPDATE image_frames SET {column}=NULL WHERE project_id=?', ('P1',))
    calls = fake_micmac(monkeypatch)
    with pytest.raises(mm.MicMacError, match='Kamerapositionen'):
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
    assert calls == [] and list(output.iterdir()) == []


@pytest.mark.parametrize('layer', ('rgb', 'thermal'))
@pytest.mark.parametrize('stage,number', (('Tapas', 2), ('OriConvert', 3)))
def test_failed_stage_does_not_publish_a_pair(scene, monkeypatch, layer, stage, number):
    service, exe, output, _ = scene
    fake_micmac(monkeypatch, fail_layer=layer, fail_stage=stage)
    with pytest.raises(mm.MicMacError, match=stage) as error:
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
    assert str(error.value).startswith(layer.upper() + ': ')
    assert f'{layer}/step-{number:02d}.log' in str(error.value)
    assert str(output) not in str(error.value)
    assert 'synthetic private process output' not in str(error.value)
    assert service.project_orthophoto_pairs('P1') == ()
    assert json.loads(next(output.glob('*/job.json')).read_text())['status'] == 'failed'


def test_cancellation_and_changed_inputs_never_publish_a_pair(scene, monkeypatch):
    service, exe, output, files = scene
    cancel = []
    def after(layer, args):
        if args[0] == 'Tapas': cancel.append(True)
    fake_micmac(monkeypatch, after_command=after)
    with pytest.raises(mm.MicMacCancelled):
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output, should_cancel=lambda: bool(cancel))
    assert json.loads(next(output.glob('*/job.json')).read_text())['status'] == 'cancelled'
    def change(layer, args):
        if layer == 'thermal' and args[0] == 'Tawny':
            with service.database.connect() as db:
                db.execute('UPDATE image_frames SET altitude_m=altitude_m+1 WHERE project_id=?', ('P1',))
    fake_micmac(monkeypatch, after_command=change)
    with pytest.raises(mm.MicMacError, match='Projekteingaben'):
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
    assert service.project_orthophoto_pairs('P1') == ()
    def change_source(layer, args):
        if layer == 'thermal' and args[0] == 'Tawny':
            files[0].write_bytes(files[0].read_bytes() + b'changed during reconstruction')
    fake_micmac(monkeypatch, after_command=change_source)
    with pytest.raises(mm.MicMacError, match='Bildquelle während'):
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
    assert service.project_orthophoto_pairs('P1') == ()


def test_missing_georeference_is_not_replaced_by_crs_label(scene, monkeypatch):
    service, exe, output, _ = scene
    fake_micmac(monkeypatch, worldfile=False)
    with pytest.raises(mm.MicMacError, match='Rastertransform'):
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
    assert service.project_orthophoto_pairs('P1') == ()


def test_private_outputs_cannot_be_in_git_or_original_folder(scene, monkeypatch):
    service, exe, output, files = scene
    calls = fake_micmac(monkeypatch)
    (output / '.git').mkdir()
    (output / '.git' / 'HEAD').write_text('ref: refs/heads/test\n')
    for folder in (output, files[0].parent):
        with pytest.raises(mm.MicMacError):
            mm.generate_micmac_orthophotos(service.database, 'P1', exe, folder)
    assert calls == []


def test_import_checksum_mismatch_stops_before_external_processing(scene, monkeypatch):
    service, exe, output, files = scene
    source = files[0]
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    with service.database.connect() as db:
        db.execute(
            "INSERT INTO training_samples(sample_id,project_id,source_frame_id,source_file,"
            "modality,content_sha256,label_status,rights_status) VALUES (?,?,?,?,?,?,?,?)",
            ('synthetic', 'P1', '0', str(source), 'rgb', expected, 'unreviewed', 'unknown'),
        )
    source.write_bytes(source.read_bytes() + b'changed after import')
    calls = fake_micmac(monkeypatch)
    with pytest.raises(mm.MicMacError, match='Bildquelle wurde geändert'):
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
    assert calls == []
    assert service.project_orthophoto_pairs('P1') == ()


def test_coordinate_conversion_disables_proj_network_access(scene, monkeypatch):
    from pyproj import network
    service, exe, output, _ = scene
    fake_micmac(monkeypatch)
    previous = network.is_network_enabled()
    try:
        network.set_network_enabled(True)
        mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
        assert not network.is_network_enabled()
    finally:
        network.set_network_enabled(previous)


def test_process_argv_is_literal_and_errors_do_not_disclose_output(tmp_path):
    log = tmp_path / 'private.log'
    literal = 'name & not-a-shell-command'
    mm._execute(Path(sys.executable), ('-c', 'import sys;print(sys.argv[1])', literal), tmp_path, log, lambda: False)
    assert log.read_text().strip() == literal
    with pytest.raises(mm.MicMacError) as error:
        mm._execute(Path(sys.executable), ('-c', 'print("private GPS secret");raise SystemExit(4)'),
                    tmp_path, tmp_path / 'failure.log', lambda: False)
    assert 'private GPS secret' not in str(error.value)


@pytest.mark.parametrize('timeout', (False, True))
def test_process_cancellation_or_timeout_stops_owned_children(tmp_path, timeout):
    ready, survived = tmp_path / 'ready', tmp_path / 'survived'
    child = f'from pathlib import Path;import time;Path({str(ready)!r}).touch();time.sleep(1);Path({str(survived)!r}).touch()'
    parent = f'import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",{child!r}]);time.sleep(30)'
    expected = mm.MicMacError if timeout else mm.MicMacCancelled
    with pytest.raises(expected):
        mm._execute(Path(sys.executable), ('-c', parent), tmp_path, tmp_path / 'process.log',
                    (lambda: False) if timeout else ready.exists, timeout=.3 if timeout else 10)
    time.sleep(1.1)
    assert not survived.exists()
