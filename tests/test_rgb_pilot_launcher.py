"""Launcher contracts; native Tk flow on Windows/display-enabled Linux only."""
import importlib.util
import os
from pathlib import Path
import sqlite3
import threading
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def launcher():
    spec = importlib.util.spec_from_file_location('rgb_pilot_launcher', ROOT/'scripts'/'MCM_SolarCheck_RGB_PILOT.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_cpu_selection_uses_shared_backend_without_gui_or_installs(monkeypatch, tmp_path):
    module = launcher()
    seen = []
    monkeypatch.setattr(module, 'window', lambda **kwargs: pytest.fail('CLI must not open GUI'))
    monkeypatch.setattr(module, 'execute', lambda db, project, config, cancel, progress:
                        seen.append((db, project, config)) or SimpleNamespace(rgb_geotiff=tmp_path/'rgb.tif'))
    assert module.main(['--database', 'existing.db', '--project', 'P', '--colmap', 'tool.exe',
                        '--openmvs', 'tools', '--output', str(tmp_path), '--cpu', '--target-crs', 'EPSG:32632']) == 0
    assert seen[0][0:2] == ('existing.db', 'P')
    assert seen[0][2].use_gpu is False
    assert seen[0][2].target_crs == 'EPSG:32632'


def test_launcher_without_arguments_opens_only_configuration(monkeypatch):
    module = launcher()
    seen = []
    monkeypatch.setattr(module, 'window', lambda **kwargs: seen.append(kwargs))
    monkeypatch.setattr(module, 'execute', lambda *args: pytest.fail('must wait for explicit start'))
    assert module.main([]) == 0 and seen == [{'use_gpu': True, 'target_crs': None}]
    assert module.main(['--cpu']) == 0 and seen[-1]['use_gpu'] is False


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='native Tk needs a display')
@pytest.mark.parametrize('cancel_run', [False, True])
def test_native_tk_project_selection_start_result_or_cancel(monkeypatch, tmp_path, cancel_run):
    import tkinter as tk
    from tkinter import filedialog, ttk
    module = launcher()
    database = tmp_path/'existing.sqlite3'
    with sqlite3.connect(database) as db:
        db.executescript("CREATE TABLE projects(project_id TEXT,name TEXT); INSERT INTO projects VALUES('P','Existing');")
    before = database.read_bytes()
    root = tk.Tk()
    root.withdraw()
    monkeypatch.setattr(tk, 'Tk', lambda: root)
    files = iter([str(database), str(tmp_path/'colmap.exe')])
    dirs = iter([str(tmp_path/'tools'), str(tmp_path)])
    monkeypatch.setattr(filedialog, 'askopenfilename', lambda **kwargs: next(files))
    monkeypatch.setattr(filedialog, 'askdirectory', lambda **kwargs: next(dirs))
    started, received, errors = threading.Event(), [], []
    outcomes = {'success': False, 'cancel_seen': False, 'cancel_requested': False}
    monkeypatch.setattr(root, 'report_callback_exception', lambda *args: errors.append(args))

    def fake_execute(db, project, config, cancel, progress):
        received.append((db, project, config))
        started.set()
        progress('Synthetic step')
        if cancel_run:
            deadline = time.monotonic() + 5
            while not cancel() and time.monotonic() < deadline:
                time.sleep(.01)
            assert cancel()
            outcomes['cancel_seen'] = True
            raise module.PilotCancelled('cancelled')
        return SimpleNamespace(workspace=tmp_path, rgb_geotiff=tmp_path/'rgb.tif')
    monkeypatch.setattr(module, 'execute', fake_execute)

    def descendants(parent):
        for child in parent.winfo_children():
            yield child
            yield from descendants(child)

    def activate():
        widgets = list(descendants(root))
        picks = [w for w in widgets if isinstance(w, ttk.Button) and w['text']=='Auswaehlen']
        assert not started.is_set()
        for pick in picks:
            pick.invoke()
        combo = next(w for w in widgets if isinstance(w, ttk.Combobox))
        assert combo.current() == -1  # selecting a DB must not select a wrong project silently
        combo.current(0)
        next(w for w in widgets if isinstance(w, ttk.Checkbutton)).invoke()
        next(w for w in widgets if isinstance(w, ttk.Button) and w['text']=='Pilot starten').invoke()
        root.after(50, finish)

    def finish():
        widgets = list(descendants(root))
        if not started.is_set():
            root.after(50, finish)
            return
        if cancel_run:
            outcomes['cancel_requested'] = True
            next(w for w in widgets if isinstance(w, ttk.Button) and w['text']=='Abbrechen').invoke()
            return
        result_button = next(w for w in widgets if isinstance(w, ttk.Button) and w['text']=='Ausgabeordner oeffnen')
        if str(result_button['state']) != 'normal':
            root.after(50, finish)
            return
        outcomes['success'] = True
        next(w for w in widgets if isinstance(w, ttk.Button) and w['text']=='Schliessen').invoke()

    root.after(20, activate)
    root.after(8000, root.destroy)  # fail boundedly if event delivery is broken
    module.window()
    assert not errors
    assert received and received[0][0:2] == (str(database), 'P')
    assert received[0][2].use_gpu is False
    assert database.read_bytes() == before
    assert (outcomes['cancel_seen'] and outcomes['cancel_requested']) if cancel_run else outcomes['success']
