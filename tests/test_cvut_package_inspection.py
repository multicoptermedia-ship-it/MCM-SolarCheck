"""Public model intake: inventory only, no dependency/model execution."""
import importlib.util
import errno
import http.client
import io
import json
import pickle
from collections import OrderedDict
from pathlib import Path
import stat
import socket
import ssl
import urllib.error
import zipfile

import pytest


@pytest.fixture
def intake():
    spec = importlib.util.spec_from_file_location(
        'cvut_intake', Path(__file__).resolve().parents[1] / 'scripts/MCM_SolarCheck_CVUT_PAKETPRUEFUNG.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def package(entries=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, data in (entries or {
            'modules_rgb/model.pth': b'synthetic-not-a-real-model',
            'README.md': b'Public test fixture; license still requires review.',
            'run.py': b'raise RuntimeError("must never execute")',
        }).items():
            # Preserve deliberately malformed names even on Windows, whose
            # ZipInfo constructor otherwise converts backslashes to slashes.
            entry = zipfile.ZipInfo()
            entry.filename = entry.orig_filename = name
            archive.writestr(entry, data)
    return stream.getvalue()


def response(intake, data):
    result = io.BytesIO(data)
    result.status = 200
    result.geturl = lambda: intake.URL
    return result


def test_download_inventory_reuse_reopen_and_no_execution(intake, tmp_path, monkeypatch, capsys):
    prefix = tmp_path / 'pilot'
    source = package()
    calls = []
    def open_url(url, timeout):
        calls.append(url)
        return response(intake, source)
    monkeypatch.setattr(intake.urllib.request, 'urlopen', open_url)
    assert intake.main(['--prefix', str(prefix)]) == 0
    before = (prefix / intake.REPORT).read_bytes()
    record = json.loads(before)
    assert record['archive_sha256'] == intake.sha256(source).hexdigest()
    assert record['documentation'][0]['name'] == 'README.md'
    assert sum(e['possible_weights'] for e in record['entries']) == 1
    for field in ('training_started', 'inference_started', 'dependencies_installed',
                  'model_license_verified', 'production_approved', 'accuracy_verified', 'automatically_accepted'):
        assert record[field] is False
    assert sorted(p.name for p in prefix.iterdir()) == sorted([
        intake.ARCHIVE, intake.REPORT, 'cvut-intake.json', 'cvut-package.lock'])
    assert intake.main(['--prefix', str(prefix)]) == 0
    assert calls == [intake.URL]
    assert (prefix / intake.REPORT).read_bytes() == before
    output = capsys.readouterr().out
    assert str(tmp_path) not in output
    assert 'Public test fixture' not in output
    assert 'Noch kein KI-Ergebnis' in output


def test_http_failure_then_explicit_continuation(intake, tmp_path, monkeypatch):
    prefix = tmp_path / 'pilot'
    def unavailable(*args, **kwargs):
        raise urllib.error.HTTPError(intake.URL, 503, 'Unavailable', {}, None)
    monkeypatch.setattr(intake.urllib.request, 'urlopen', unavailable)
    assert intake.main(['--prefix', str(prefix)]) == 2
    assert not (prefix / intake.REPORT).exists()
    assert not (prefix / intake.ARCHIVE).exists()
    monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: response(intake, package()))
    assert intake.main(['--prefix', str(prefix)]) == 0


def test_cancel_cleans_partial_and_continuation_preserves_valid_source(intake, tmp_path, monkeypatch):
    prefix = tmp_path / 'pilot'
    class Cancelled(io.BytesIO):
        status = 200
        def geturl(self):
            return intake.URL
        def read(self, n=-1):
            raise KeyboardInterrupt
    monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: Cancelled(b'partial'))
    assert intake.main(['--prefix', str(prefix)]) == 130
    assert not (prefix / (intake.ARCHIVE + '.download')).exists()
    assert not (prefix / intake.REPORT).exists()
    original = tmp_path / intake.ARCHIVE
    data = package()
    original.write_bytes(data)
    monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('unexpected network'))
    assert intake.main(['--prefix', str(prefix), '--archive', str(original)]) == 0
    saved = (prefix / intake.REPORT).read_bytes()
    assert intake.main(['--prefix', str(prefix), '--archive', str(original)]) == 0
    assert original.read_bytes() == data
    original.write_bytes(package({'changed.pth': b'changed'}))
    assert intake.main(['--prefix', str(prefix), '--archive', str(original)]) == 2
    assert (prefix / intake.REPORT).read_bytes() == saved


@pytest.mark.parametrize('name', ['../model.pth', '/model.pth', 'C:/model.pth', 'x\\model.pth', 'bad\nname.pth'])
def test_unsafe_member_names_fail_closed(intake, tmp_path, name):
    archive = tmp_path / intake.ARCHIVE
    archive.write_bytes(package({name: b'not executed'}))
    with pytest.raises(ValueError):
        intake.inspect_package(tmp_path / 'pilot', archive)
    assert not (tmp_path / 'pilot' / intake.REPORT).exists()


def test_symlink_member_and_expansion_limit(intake, tmp_path, monkeypatch):
    path = tmp_path / intake.ARCHIVE
    with zipfile.ZipFile(path, 'w') as archive:
        entry = zipfile.ZipInfo('weights.pth')
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(entry, 'elsewhere')
    with pytest.raises(ValueError):
        intake.inventory(path)
    path.write_bytes(package())
    monkeypatch.setattr(intake, 'MAX_EXPANDED', 10)
    with pytest.raises(ValueError):
        intake.inventory(path)


def test_bad_zip_and_oversized_download_do_not_replace_report(intake, tmp_path, monkeypatch):
    prefix = tmp_path / 'pilot'
    monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: response(intake, package()))
    intake.inspect_package(prefix)
    saved = (prefix / intake.REPORT).read_bytes()
    (prefix / intake.ARCHIVE).unlink()
    monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: response(intake, b'<html>503</html>'))
    assert intake.main(['--prefix', str(prefix)]) == 2
    assert (prefix / intake.REPORT).read_bytes() == saved
    monkeypatch.setattr(intake, 'MAX_ARCHIVE', 10)
    monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: response(intake, b'x' * 11))
    assert intake.main(['--prefix', str(prefix)]) == 2
    assert (prefix / intake.REPORT).read_bytes() == saved
    assert not (prefix / (intake.ARCHIVE + '.download')).exists()


def test_foreign_directory_and_git_checkout_remain_unchanged(intake, tmp_path):
    foreign = tmp_path / 'foreign'
    foreign.mkdir()
    (foreign / 'important.txt').write_text('keep')
    with pytest.raises(ValueError):
        intake.inspect_package(foreign)
    assert sorted(p.name for p in foreign.iterdir()) == ['important.txt']
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    (checkout / '.git').write_text('gitdir: elsewhere')
    with pytest.raises(ValueError):
        intake.inspect_package(checkout / 'pilot')


def test_filesystem_symlink_not_followed(intake, tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip('symlink creation unavailable')
    with pytest.raises(ValueError):
        intake.inspect_package(link / 'pilot')
    assert not list(real.iterdir())


def test_concurrent_start_does_not_remove_active_download(intake, tmp_path, monkeypatch):
    prefix = tmp_path / 'pilot'
    monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: response(intake, package()))
    intake.inspect_package(prefix)
    saved = (prefix / intake.REPORT).read_bytes()
    partial = prefix / (intake.ARCHIVE + '.download')
    with intake.package_lock(prefix):
        partial.write_bytes(b'active download')
        assert intake.main(['--prefix', str(prefix)]) == 2
        assert partial.read_bytes() == b'active download'
        assert (prefix / intake.REPORT).read_bytes() == saved
    assert intake.main(['--prefix', str(prefix)]) == 0
    assert not partial.exists()


PRIVATE_DETAIL = r'C:\private-customer\roof\coordinates-and-proxy-secret'


@pytest.mark.parametrize('error,code', [
    (urllib.error.HTTPError(PRIVATE_DETAIL, 503, PRIVATE_DETAIL, {}, None), 'HTTP_ERROR'),
    (urllib.error.URLError(ssl.SSLCertVerificationError(1, PRIVATE_DETAIL)), 'TLS_CERTIFICATE'),
    (ssl.SSLError(1, PRIVATE_DETAIL), 'TLS_CONNECTION'),
    (urllib.error.URLError(socket.gaierror(-2, PRIVATE_DETAIL)), 'DNS_LOOKUP'),
    (urllib.error.URLError(TimeoutError(PRIVATE_DETAIL)), 'NETWORK_TIMEOUT'),
    (TimeoutError(PRIVATE_DETAIL), 'NETWORK_TIMEOUT'),
    (urllib.error.URLError(PRIVATE_DETAIL), 'NETWORK_CONNECTION'),
    (http.client.IncompleteRead(b'private partial data', 100), 'DOWNLOAD_INTERRUPTED'),
    (ConnectionResetError(PRIVATE_DETAIL), 'DOWNLOAD_INTERRUPTED'),
    (PermissionError(errno.EACCES, PRIVATE_DETAIL, PRIVATE_DETAIL), 'LOCAL_ACCESS'),
    (OSError(errno.ENOSPC, PRIVATE_DETAIL, PRIVATE_DETAIL), 'DISK_FULL'),
    (FileNotFoundError(errno.ENOENT, PRIVATE_DETAIL, PRIVATE_DETAIL), 'LOCAL_FILE_MISSING'),
    (OSError(errno.EIO, PRIVATE_DETAIL, PRIVATE_DETAIL), 'LOCAL_IO'),
    (RuntimeError(PRIVATE_DETAIL), 'UNEXPECTED_ERROR'),
])
def test_main_reports_specific_failure_without_paths_or_raw_exception(
        intake, tmp_path, monkeypatch, capsys, error, code):
    def failed_download(url, **kwargs):
        assert url == intake.URL
        assert kwargs == {'timeout': 30}  # Default verified TLS; no insecure context.
        raise error
    monkeypatch.setattr(intake.urllib.request, 'urlopen', failed_download)
    prefix = tmp_path / 'pilot'
    assert intake.main(['--prefix', str(prefix)]) == 2
    output = capsys.readouterr().out
    record, remainder = json.JSONDecoder().raw_decode(output[output.index('{'):])
    assert record['check'] == intake.FAILURE_CHECK
    assert record['error_code'] == code
    assert record['model_loaded'] is record['training_started'] is record['inference_started'] is False
    if code == 'HTTP_ERROR':
        assert record['http_status'] == 503
    assert PRIVATE_DETAIL not in output
    assert 'private-customer' not in output and 'private partial data' not in output
    assert str(tmp_path) not in output
    assert not (prefix / intake.REPORT).exists()
    assert not (prefix / (intake.ARCHIVE + '.download')).exists()


@pytest.mark.parametrize('data,code', [(b'<html>unavailable</html>', 'INVALID_ZIP'), (b'not JSON', 'LOCAL_METADATA')])
def test_format_failures_have_safe_diagnosis(intake, tmp_path, monkeypatch, capsys, data, code):
    prefix = tmp_path / 'pilot'
    if code == 'INVALID_ZIP':
        monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: response(intake, data))
    else:
        prefix.mkdir()
        (prefix / 'cvut-intake.json').write_bytes(data)
    assert intake.main(['--prefix', str(prefix)]) == 2
    output = capsys.readouterr().out
    record, _ = json.JSONDecoder().raw_decode(output[output.index('{'):])
    assert record['error_code'] == code
    assert str(tmp_path) not in output


def test_rejected_response_reason_is_visible_without_remote_url(intake, tmp_path, monkeypatch, capsys):
    def redirected(url, **kwargs):
        result = response(intake, package())
        result.geturl = lambda: 'https://other.invalid/' + PRIVATE_DETAIL
        return result
    monkeypatch.setattr(intake.urllib.request, 'urlopen', redirected)
    assert intake.main(['--prefix', str(tmp_path / 'pilot')]) == 2
    output = capsys.readouterr().out
    assert 'PACKAGE_CHECK' in output and 'Unerwartete Downloadantwort' in output
    assert PRIVATE_DETAIL not in output and 'other.invalid' not in output
    assert not (tmp_path / 'pilot' / intake.ARCHIVE).exists()


def rebuild_metadata_tensor(*args):
    raise AssertionError('A pickle constructor must never execute during inspection')


class TensorMetadata:
    def __init__(self, shape):
        self.shape = shape

    def __reduce__(self):
        return rebuild_metadata_tensor, ('storage-reference', 0, self.shape, (), False, OrderedDict())


def tensor_pickle():
    class MetadataPickler(pickle.Pickler):
        def persistent_id(self, obj):
            if isinstance(obj, str) and obj == 'storage-reference':
                return ('storage', 'FloatStorage', '0', 'cpu', 1728)
    stream = io.BytesIO()
    MetadataPickler(stream, protocol=2).dump(OrderedDict([
        ('inc.double_conv.0.weight', TensorMetadata((64, 3, 3, 3))),
        ('outc.conv.weight', TensorMetadata((1, 64, 1, 1))),
        ('bn.num_batches_tracked', TensorMetadata(())),
    ]))
    return stream.getvalue()


def rgb_layout_fixture(intake, tmp_path, monkeypatch, *, metadata=None, extra=None, legacy=False):
    model = b'legacy-not-loaded' if legacy else package({
        'weights/data.pkl': metadata if metadata is not None else tensor_pickle(),
        'weights/data/0': b'not-real-tensor-values',
        'weights/version': b'3\n',
        **(extra or {}),
    })
    data = package({
        'UNet_pv_installation_rgb.pth': b'not selected',
        'UNet_pv_module_rgb.pth': model,
        'UNet_pv_module_thermo.pth': b'not selected',
    })
    path = tmp_path / intake.ARCHIVE
    path.write_bytes(data)
    monkeypatch.setattr(intake, 'CVUT_ARCHIVE', dict(
        bytes=len(data), sha256=intake.sha256(data).hexdigest(),
        rgb_name='UNet_pv_module_rgb.pth', rgb_bytes=len(model)))
    monkeypatch.setattr(intake.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('Layout check must be offline'))
    return path, data, model


def test_rgb_layout_reads_only_pinned_model_metadata_and_preserves_package_report(
        intake, tmp_path, monkeypatch, capsys):
    path, source, model = rgb_layout_fixture(intake, tmp_path, monkeypatch)
    prefix = tmp_path / 'pilot'
    intake.inspect_package(prefix, path)
    original_report = (prefix / intake.REPORT).read_bytes()
    monkeypatch.setattr(pickle, 'loads', lambda *a, **k: pytest.fail('No pickle loading'))
    assert intake.main(['--prefix', str(prefix), '--archive', str(path), '--inspect-rgb-layout']) == 0
    record = json.loads((prefix / intake.RGB_REPORT).read_text())
    assert record['check'] == 'solarcheck-cvut-rgb-layout-1'
    assert record['model_sha256'] == intake.sha256(model).hexdigest()
    assert record['selected_model'] == 'UNet_pv_module_rgb.pth'
    assert record['metadata']['pickle_protocol'] == 2
    assert record['metadata']['tensor_shape_hints'] == [
        {'parameter': 'inc.double_conv.0.weight', 'shape': [64, 3, 3, 3]},
        {'parameter': 'outc.conv.weight', 'shape': [1, 64, 1, 1]},
        {'parameter': 'bn.num_batches_tracked', 'shape': []},
    ]
    for field in ('model_loaded', 'training_started', 'inference_started', 'dependencies_installed',
                  'model_license_verified', 'production_approved'):
        assert record[field] is False
    assert path.read_bytes() == source
    assert (prefix / intake.REPORT).read_bytes() == original_report
    saved = (prefix / intake.RGB_REPORT).read_bytes()
    assert intake.main(['--prefix', str(prefix), '--archive', str(path), '--inspect-rgb-layout']) == 0
    assert (prefix / intake.RGB_REPORT).read_bytes() == saved
    assert sorted(p.name for p in prefix.iterdir()) == sorted([
        'cvut-intake.json', 'cvut-package.lock', intake.REPORT, intake.RGB_REPORT])
    assert str(tmp_path) not in capsys.readouterr().out


def write_unwanted_file(path):
    Path(path).write_text('must not happen')


def test_pickle_constructor_is_disassembled_without_execution(intake, tmp_path, monkeypatch):
    marker = tmp_path / 'should-never-exist'
    class Payload:
        def __reduce__(self):
            return write_unwanted_file, (str(marker),)
    path, _, _ = rgb_layout_fixture(intake, tmp_path, monkeypatch, metadata=pickle.dumps(Payload(), protocol=2))
    record = intake.inspect_rgb_layout(tmp_path / 'pilot', path)
    assert not marker.exists()
    assert any('write_unwanted_file' in name for name in record['metadata']['global_references'])
    assert str(marker) not in json.dumps(record)
    assert record['model_loaded'] is False


def test_layout_rejects_changed_archive_and_keeps_last_result(intake, tmp_path, monkeypatch):
    path, _, _ = rgb_layout_fixture(intake, tmp_path, monkeypatch)
    prefix = tmp_path / 'pilot'
    intake.inspect_rgb_layout(prefix, path)
    before = (prefix / intake.RGB_REPORT).read_bytes()
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='beobachtete'):
        intake.inspect_rgb_layout(prefix, path)
    assert (prefix / intake.RGB_REPORT).read_bytes() == before


@pytest.mark.parametrize('case', ['metadata_limit', 'nested_path', 'malformed_pickle'])
def test_layout_metadata_limits_and_rejections(intake, tmp_path, monkeypatch, case):
    kwargs = {}
    if case == 'nested_path':
        kwargs['extra'] = {'../bad': b'do not read'}
    if case == 'malformed_pickle':
        kwargs['metadata'] = b'not pickle opcodes'
    path, _, _ = rgb_layout_fixture(intake, tmp_path, monkeypatch, **kwargs)
    if case == 'metadata_limit':
        monkeypatch.setattr(intake, 'MAX_PICKLE_METADATA', 4)
    assert intake.main(['--prefix', str(tmp_path / 'pilot'), '--archive', str(path), '--inspect-rgb-layout']) == 2
    assert not (tmp_path / 'pilot' / intake.RGB_REPORT).exists()


def test_layout_cancellation_closes_temporary_model_and_retains_result(intake, tmp_path, monkeypatch):
    path, source, _ = rgb_layout_fixture(intake, tmp_path, monkeypatch)
    prefix = tmp_path / 'pilot'
    intake.inspect_rgb_layout(prefix, path)
    before = (prefix / intake.RGB_REPORT).read_bytes()
    original_parser = intake.pickle_layout
    def cancelled(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(intake, 'pickle_layout', cancelled)
    assert intake.main(['--prefix', str(prefix), '--archive', str(path), '--inspect-rgb-layout']) == 130
    assert (prefix / intake.RGB_REPORT).read_bytes() == before
    assert path.read_bytes() == source
    assert sorted(p.name for p in prefix.iterdir()) == sorted([
        'cvut-intake.json', 'cvut-package.lock', intake.RGB_REPORT])
    monkeypatch.setattr(intake, 'pickle_layout', original_parser)
    assert intake.main(['--prefix', str(prefix), '--archive', str(path), '--inspect-rgb-layout']) == 0
    assert (prefix / intake.RGB_REPORT).read_bytes() == before


def test_legacy_container_is_reported_without_loading(intake, tmp_path, monkeypatch):
    path, _, _ = rgb_layout_fixture(intake, tmp_path, monkeypatch, legacy=True)
    record = intake.inspect_rgb_layout(tmp_path / 'pilot', path)
    assert record['metadata']['format'] == 'legacy_or_unknown_not_loaded'
    assert record['model_loaded'] is False


def test_layout_requires_explicit_local_archive(intake, tmp_path):
    with pytest.raises(ValueError, match='--archive'):
        intake.inspect_rgb_layout(tmp_path / 'pilot', None)
    assert not (tmp_path / 'pilot').exists()
