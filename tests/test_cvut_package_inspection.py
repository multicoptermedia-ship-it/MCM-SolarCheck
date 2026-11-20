"""Public model intake: inventory only, no dependency/model execution."""
import importlib.util
import errno
import http.client
import io
import json
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
