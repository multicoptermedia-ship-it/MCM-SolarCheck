"""Only generated ZIP/COCO fixtures; no public/customer images or network in CI."""
from dataclasses import replace
from hashlib import sha256
import importlib
import io
import json
from pathlib import Path
import ssl
import sys
import urllib.error
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
pv = importlib.import_module('MCM_SolarCheck_PVIS_REFERENZ')


def fixture_zip(source, station, mutate=None, extra=None):
    data = dict(categories=[dict(id=1, name='pv_panel')],
        images=[dict(id=1, file_name='generated.jpg', width=64, height=64)],
        annotations=[dict(id=1, image_id=1, category_id=1, bbox=[5, 5, 20, 10],
                          area=200, segmentation=[[5, 5, 25, 5, 25, 15, 5, 15]])])
    if mutate:
        mutate(data)
    payload = {station.prefix+'images/generated.jpg': b'generated-not-decoded-image',
               station.prefix+'instances.json': json.dumps(data).encode()}
    payload.update(extra or {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, content in payload.items():
            entry = zipfile.ZipInfo()
            entry.filename = entry.orig_filename = name
            archive.writestr(entry, content)
    content = buffer.getvalue()
    path = source/station.name
    path.write_bytes(content)
    return replace(station, size=len(content), sha256=sha256(content).hexdigest(),
                   images=1, annotations=len(data['annotations']), unpacked=sum(map(len, payload.values())))


@pytest.fixture
def reference(tmp_path, monkeypatch):
    source = tmp_path/'public-synthetic-source'
    source.mkdir()
    stations = tuple(fixture_zip(source, station) for station in pv.STATIONS)
    documents = {}
    for name in pv.DOCUMENTS:
        content = b'generated source evidence, not a real license review'
        (source/name).write_bytes(content)
        documents[name] = (len(content), sha256(content).hexdigest())
    monkeypatch.setattr(pv, 'STATIONS', stations)
    monkeypatch.setattr(pv, 'DOCUMENTS', documents)
    monkeypatch.setattr(pv.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('Unexpected network'))
    return source, tmp_path/'reference', stations


def test_reopen_is_identical_without_network_or_original_sources(reference):
    source, root, stations = reference
    originals = {p.name: p.read_bytes() for p in source.iterdir()}
    result = pv.intake(root, source)
    assert result['images'] == result['annotation_observations'] == 2
    assert [(r['split'], r['station']) for r in result['stations']] == [('train', '009'), ('test', '024')]
    assert result['station_disjoint'] and result['validation_stations'] == 0
    assert result['license_decision'] == 'unreviewed'
    for key in ('commercial_training_approved', 'training_started', 'training_authorized',
                'image_decoding_verified', 'visible_corner_eligibility_verified',
                'physical_module_ids_confirmed', 'model_updated', 'accuracy_verified',
                'coverage_verified', 'temperature_verified', 'production_approved', 'customer_images_read'):
        assert result[key] is False
    assert {p.name: p.read_bytes() for p in source.iterdir()} == originals
    for p in source.iterdir():
        p.unlink()
    assert pv.intake(root, show=True) == result
    assert not list(root.rglob('*.jpg'))


def test_interrupt_second_archive_reuses_completed_first(reference, monkeypatch):
    source, root, stations = reference
    with pytest.raises(KeyboardInterrupt):
        pv.intake(root, source, should_cancel=lambda: (root/stations[0].name).exists())
    assert (root/stations[0].name).read_bytes() == (source/stations[0].name).read_bytes()
    assert not (root/'reference.json').exists()
    assert not list(root.glob('*.download'))
    (source/stations[0].name).unlink()  # retry must use verified complete archive
    assert pv.intake(root, source)['images'] == 2


def test_failed_recheck_preserves_previous_report(reference, monkeypatch):
    source, root, stations = reference
    pv.intake(root, source)
    before = (root/'reference.json').read_bytes()
    real = pv.inspect_station
    def abort(path, station, should_cancel):
        if station.split == 'test':
            raise KeyboardInterrupt
        return real(path, station, should_cancel)
    monkeypatch.setattr(pv, 'inspect_station', abort)
    with pytest.raises(KeyboardInterrupt):
        pv.intake(root, source)
    assert (root/'reference.json').read_bytes() == before


@pytest.mark.parametrize('filename', ['reference.json', 'PVDataset_train_009.zip', 'LICENSE.md'])
def test_tampering_blocks_reopen(reference, filename):
    source, root, _ = reference
    pv.intake(root, source)
    path = root/filename
    if filename == 'reference.json':
        data = json.loads(path.read_text())
        data['production_approved'] = True
        path.write_text(json.dumps(data))
    else:
        content = path.read_bytes()
        path.write_bytes(content[:-1]+bytes([content[-1] ^ 1]))
    with pytest.raises(ValueError):
        pv.intake(root, show=True)


def test_rejects_unowned_destination(reference):
    source, root, _ = reference
    root.mkdir()
    (root/'customer.txt').write_text('must remain unchanged')
    with pytest.raises(ValueError):
        pv.intake(root, source)
    assert list(p.name for p in root.iterdir()) == ['customer.txt']


def test_source_inside_git_is_rejected(reference):
    source, root, _ = reference
    (source/'.git').write_text('gitdir: elsewhere')
    with pytest.raises(ValueError):
        pv.intake(root, source)


def test_parallel_process_is_blocked_and_lock_released(reference):
    import subprocess
    source, root, _ = reference
    pv.intake(root, source)
    # The same OS lock helper is used by both intake and read-only reopen.
    with pv.package_lock(root, 'pvis-package.lock'):
        script = Path(pv.__file__)
        child = subprocess.run([sys.executable, str(script), '--prefix', str(root), '--show'],
                               capture_output=True, text=True, timeout=15)
    assert child.returncode == 2
    assert json.loads(child.stdout)['error_code'] == 'LOCAL_IO'
    assert pv.intake(root, show=True)['images'] == 2


@pytest.mark.parametrize('case', ['reference', 'duplicate', 'category', 'nan', 'bbox', 'polygon', 'filename', 'dimensions'])
def test_invalid_coco_is_not_published(reference, monkeypatch, case):
    source, root, stations = reference
    def change(data):
        a = data['annotations'][0]
        if case == 'reference': a['image_id'] = 200
        elif case == 'duplicate': data['annotations'].append(a.copy())
        elif case == 'category': data['categories'][0]['name'] = 'cell'
        elif case == 'nan': a['segmentation'][0][0] = float('nan')
        elif case == 'bbox': a['bbox'][2] = 200
        elif case == 'polygon': a['segmentation'][0][0] = -1
        elif case == 'filename': data['images'][0]['file_name'] = '../secret.jpg'
        elif case == 'dimensions': data['images'][0]['width'] = True
    damaged = fixture_zip(source, stations[0], change)
    monkeypatch.setattr(pv, 'STATIONS', (damaged, stations[1]))
    with pytest.raises(ValueError):
        pv.intake(root, source)
    assert not (root/'reference.json').exists()


@pytest.mark.parametrize('path', ['../escape.jpg', '/absolute.jpg', 'train/009/images\\bad.jpg',
                                'train/009/images/a.jpg:stream', 'test/024/images/wrong.jpg'])
def test_unsafe_zip_members_not_extracted(reference, monkeypatch, path):
    source, root, stations = reference
    damaged = fixture_zip(source, stations[0], extra={path: b'generated'})
    monkeypatch.setattr(pv, 'STATIONS', (damaged, stations[1]))
    with pytest.raises(ValueError):
        pv.intake(root, source)
    assert not (root/'reference.json').exists()
    assert not list(root.rglob('*.jpg'))


def test_download_is_bounded_and_tls_error_is_path_free(reference, monkeypatch, capsys):
    source, root, _ = reference
    calls = []
    def download(url, timeout):
        calls.append(url)
        return io.BytesIO(b'too much data' * 100)
    monkeypatch.setattr(pv.urllib.request, 'urlopen', download)
    with pytest.raises(ValueError):
        pv._receive(source/'newfile', 10, '0'*64, None, lambda: False)
    assert not (source/'newfile').exists()
    assert not (source/'newfile.download').exists()
    def tls(*a, **k):
        raise urllib.error.URLError(ssl.SSLCertVerificationError('sensitive local path'))
    monkeypatch.setattr(pv.urllib.request, 'urlopen', tls)
    assert pv.main(['--prefix', str(root)]) == 2
    out = capsys.readouterr().out
    assert json.loads(out)['error_code'] == 'TLS_CERTIFICATE'
    assert str(root) not in out and 'sensitive' not in out


def test_multifragment_policy_is_not_lost(reference, monkeypatch):
    source, root, stations = reference
    def fragments(data):
        data['annotations'][0]['segmentation'].append([30, 5, 40, 5, 40, 15])
    updated = fixture_zip(source, stations[0], fragments)
    monkeypatch.setattr(pv, 'STATIONS', (updated, stations[1]))
    result = pv.intake(root, source)
    assert result['stations'][0]['multi_fragment_instances'] == 1
    assert result['stations'][0]['annotation_observations'] == 1
    assert result['annotation_policy'] == 'whole_module_projected_including_occluded_parts'


def test_published_bounds_and_site_holdout_are_fixed():
    assert [(s.split, s.station, s.images, s.annotations) for s in pv.STATIONS] == [
        ('train', '009', 58, 16697), ('test', '024', 84, 20766)]
    assert sum(s.size for s in pv.STATIONS) == 452609478
    assert all(len(s.sha256) == 64 for s in pv.STATIONS)


def test_full_disk_preserves_finished_report(reference, monkeypatch):
    source, root, _ = reference
    pv.intake(root, source)
    before = (root/'reference.json').read_bytes()
    monkeypatch.setattr(pv.shutil, 'disk_usage', lambda _: type('Usage', (), {'free': 0})())
    with pytest.raises(OSError) as error:
        pv.intake(root, source)
    assert error.value.errno == 28
    assert (root/'reference.json').read_bytes() == before


def test_invalid_source_checksum_never_replaces_completed_archive(reference):
    source, root, stations = reference
    path = source/stations[0].name
    content = path.read_bytes()
    path.write_bytes(content[:-1]+bytes([content[-1] ^ 1]))
    with pytest.raises(ValueError):
        pv.intake(root, source)
    assert not (root/stations[0].name).exists()
    assert path.read_bytes() != content  # no attempt to repair/overwrite the source


def test_symlink_target_is_rejected(reference, tmp_path):
    source, root, stations = reference
    root.mkdir()
    pv.atomic_json(root/'pvis-intake.json', {'check': pv.CHECK})
    outside = tmp_path/'do-not-change'
    outside.write_bytes(b'protected')
    try:
        (root/'LICENSE.md.download').symlink_to(outside)
    except OSError:
        pytest.skip('Host does not permit creating symlinks')
    with pytest.raises(ValueError):
        pv.intake(root, source)
    assert outside.read_bytes() == b'protected'


def test_cli_show_does_not_start_a_download(reference, capsys):
    source, root, _ = reference
    pv.intake(root, source)
    assert pv.main(['--prefix', str(root), '--show']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['training_started'] is False and report['images'] == 2
