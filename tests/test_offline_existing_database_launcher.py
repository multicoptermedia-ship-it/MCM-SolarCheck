"""ZIP update reuses a selected project, with a local snapshot before GUI startup."""
from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from mcm_solarcheck.offline import __main__ as launcher
from mcm_solarcheck.offline.composition import build_offline_services


def test_existing_database_is_backed_up_including_wal_before_gui_initialization(tmp_path, monkeypatch):
    path = tmp_path / "project [old] & ' .sqlite3"
    service = build_offline_services(path).projects
    service.create_project('P1', 'Original')
    with closing(sqlite3.connect(path)) as live:
        live.execute('PRAGMA journal_mode=WAL')
        live.execute("UPDATE projects SET name='Committed WAL' WHERE project_id='P1'")
        live.commit()
        assert path.with_name(path.name + '-wal').is_file()
        calls = []
        def start(argv, database_path):
            calls.append((argv, database_path))
            backups = tuple(tmp_path.glob('*.before-update-*.sqlite3'))
            assert len(backups) == 1
            with closing(sqlite3.connect(backups[0])) as backup:
                assert backup.execute("SELECT name FROM projects WHERE project_id='P1'").fetchone() == ('Committed WAL',)
            # Represents a later GUI/migration write, after the snapshot.
            live.execute("UPDATE projects SET name='After startup' WHERE project_id='P1'")
            live.commit()
            return 17
        monkeypatch.setattr(launcher, 'main', start)
        assert launcher.launch(['--existing-database', str(path), '-platform', 'offscreen']) == 17
        assert calls[0][1] == path.resolve()
        assert calls[0][0][-2:] == ['-platform', 'offscreen']
        with closing(sqlite3.connect(next(tmp_path.glob('*.before-update-*.sqlite3')))) as backup:
            assert backup.execute("SELECT name FROM projects WHERE project_id='P1'").fetchone() == ('Committed WAL',)


@pytest.mark.parametrize('kind', ('missing', 'different_database', 'different_projects_schema'))
def test_wrong_or_missing_project_never_creates_database_or_opens_gui(tmp_path, monkeypatch, kind):
    path = tmp_path / 'selected.sqlite3'
    if kind == 'different_database':
        with closing(sqlite3.connect(path)) as other:
            other.execute('CREATE TABLE unrelated(value TEXT)')
            other.commit()
    elif kind == 'different_projects_schema':
        with closing(sqlite3.connect(path)) as other:
            other.execute('CREATE TABLE projects(unrelated TEXT)')
            other.commit()
    before = path.read_bytes() if path.exists() else None
    monkeypatch.setattr(launcher, 'main', lambda **kwargs: pytest.fail('must not initialize an invalid selection'))
    with pytest.raises(SystemExit) as error:
        launcher.launch(['--existing-database', str(path)])
    assert error.value.code == 2
    assert (path.read_bytes() if path.exists() else None) == before
    assert not tuple(tmp_path.glob('*.before-update-*'))


def test_failed_local_backup_prevents_gui_initialization(tmp_path, monkeypatch):
    path = tmp_path / 'existing.sqlite3'
    service = build_offline_services(path).projects
    service.create_project('P1', 'Keep')
    def fail(path):
        raise PermissionError('local backup unavailable')
    monkeypatch.setattr(launcher, 'backup_database', fail)
    monkeypatch.setattr(launcher, 'main', lambda **kwargs: pytest.fail('backup must complete first'))
    with pytest.raises(PermissionError):
        launcher.launch(['--existing-database', str(path)])
    assert service.projects()[0].name == 'Keep'
