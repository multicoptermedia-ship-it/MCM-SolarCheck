"""The requested Downloads starter delegates to the existing project-safe start."""
from hashlib import sha256
import importlib.util
from pathlib import Path
import stat
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo

import pytest


@pytest.fixture
def starter(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'scripts/MCM_SolarCheck_Schritt115_START_MicMac.py'
    spec = importlib.util.spec_from_file_location('download_starter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'REQUIRED_HASHES', {
        'scripts/start_windows10_offline.ps1': sha256(b'# synthetic starter').hexdigest(),
        'src/main.py': sha256(b'# synthetic app').hexdigest(),
    })
    return module


def package(starter, path, extra=None, comment=None):
    root = 'MCM-SolarCheck-' + starter.PROGRAM_COMMIT + '/'
    with ZipFile(path, 'w') as archive:
        archive.comment = starter.PROGRAM_COMMIT.encode() if comment is None else comment
        archive.writestr(root + 'scripts/start_windows10_offline.ps1', b'# synthetic starter')
        archive.writestr(root + 'src/main.py', b'# synthetic app')
        if extra is not None:
            name, data = extra
            if isinstance(name, ZipInfo):
                archive.writestr(name, data)
            else:
                archive.writestr(root + name, data)


def test_extracts_source_once_and_never_overwrites_existing_folder(starter, tmp_path):
    archive = tmp_path / 'source.zip'
    package(starter, archive)
    updates = tmp_path / 'old program' / 'test-updates'
    sentinel = tmp_path / 'old program' / 'keep.sqlite3'
    sentinel.parent.mkdir()
    sentinel.write_bytes(b'original')
    program = starter.prepare_program(archive, updates)
    assert starter.check_program(program)
    archive.unlink()
    assert starter.prepare_program(archive, updates) == program
    assert sentinel.read_bytes() == b'original'
    (program / 'src/main.py').write_bytes(b'changed')
    with pytest.raises(RuntimeError, match='nicht ueberschrieben'):
        starter.prepare_program(archive, updates)
    assert (program / 'src/main.py').read_bytes() == b'changed'


@pytest.mark.parametrize('kind', ['wrong_commit', 'traversal', 'symlink', 'customer_file', 'duplicate', 'bad_digest'])
def test_invalid_archives_never_publish_program(starter, tmp_path, kind):
    extra = None
    comment = None
    if kind == 'wrong_commit':
        comment = b'wrong'
    elif kind == 'traversal':
        extra = ('../escape.py', b'x')
    elif kind == 'symlink':
        link = ZipInfo('MCM-SolarCheck-' + starter.PROGRAM_COMMIT + '/link.py')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        extra = (link, b'elsewhere')
    elif kind == 'customer_file':
        extra = ('customer.jpg', b'x')
    elif kind == 'duplicate':
        extra = ('SRC/Main.py', b'x')
    elif kind == 'bad_digest':
        starter.REQUIRED_HASHES['src/main.py'] = '0' * 64
    archive = tmp_path / 'source.zip'
    package(starter, archive, extra, comment)
    updates = tmp_path / 'updates'
    with pytest.raises(RuntimeError):
        starter.prepare_program(archive, updates)
    assert not updates.exists()
    assert not (tmp_path / 'escape.py').exists()


def test_requested_python_delegates_to_existing_powershell_and_reuses_cache(starter, tmp_path, monkeypatch):
    python = tmp_path / 'old app [F] &' / '.venv/Scripts/python.exe'
    python.parent.mkdir(parents=True)
    python.write_bytes(b'existing python')
    downloads = tmp_path / 'profile/Downloads'
    downloads.mkdir(parents=True)
    archive = downloads / ('MCM-SolarCheck-' + starter.PROGRAM_COMMIT + ' (1).zip')
    package(starter, archive)
    monkeypatch.setattr(starter.sys, 'platform', 'win32')
    monkeypatch.setattr(starter.sys, 'executable', str(python))
    monkeypatch.setenv('USERPROFILE', str(downloads.parent))
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=17)
    monkeypatch.setattr(starter.subprocess, 'run', run)
    assert starter.main() == 17
    args, options = calls[0]
    assert args[-3:] == ['-PythonExe', str(python), '-UseExistingProject']
    assert args[1:7] == ['-NoProfile', '-STA', '-ExecutionPolicy', 'Bypass', '-File', str(options['cwd'] / 'scripts/start_windows10_offline.ps1')]
    assert options['cwd'].parent == python.parents[2] / 'test-updates'
    assert options['check'] is False
    archive.unlink()
    assert starter.main() == 17
    assert python.read_bytes() == b'existing python'


def test_missing_program_zip_gives_download_link_without_starting(starter, tmp_path, monkeypatch):
    monkeypatch.setattr(starter.sys, 'platform', 'win32')
    monkeypatch.setattr(starter.sys, 'executable', str(tmp_path / 'old/.venv/Scripts/python.exe'))
    monkeypatch.setenv('USERPROFILE', str(tmp_path / 'profile'))
    monkeypatch.setattr(starter.subprocess, 'run', lambda *a, **k: pytest.fail('must not start'))
    with pytest.raises(RuntimeError, match='Bitte zuerst die Programm-ZIP') as error:
        starter.main()
    assert starter.PROGRAM_ZIP_URL in str(error.value)
    assert not (tmp_path / 'old').exists()
