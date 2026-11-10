"""Read-only project bridge and actual Tk flow; synthetic local records only."""
import gc
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
    spec = importlib.util.spec_from_file_location('opensfm_rgb_launcher',
        ROOT / 'scripts' / 'MCM_SolarCheck_OPENSFM_RGB_PILOT.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def database(path):
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE projects(project_id TEXT,name TEXT);'
            'CREATE TABLE image_frames(project_id TEXT,frame_id TEXT,source_file TEXT,latitude REAL,longitude REAL,altitude_m REAL);'
            'CREATE TABLE training_samples(project_id TEXT,source_frame_id TEXT,modality TEXT,content_sha256 TEXT);'
            "INSERT INTO projects VALUES('P','Synthetic project');"
            "INSERT INTO image_frames VALUES('P','F','photo.JPG',50,8,100);")


def test_opening_launcher_never_starts_engine_or_installs(monkeypatch):
    module = launcher()
    calls = []
    monkeypatch.setattr(module, 'window', lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(module, 'execute', lambda *args: pytest.fail('Explicit start required'))
    assert module.main([]) == 0
    assert calls == [{'conda': module.CONDA, 'environment': module.ENVIRONMENT}]


def test_existing_readonly_database_bridge_binds_all_inputs_and_detects_change(tmp_path, monkeypatch):
    module = launcher()
    db = tmp_path / 'existing.sqlite3'
    database(db)
    before = db.read_bytes()
    prefix = tmp_path / 'existing-env'
    (prefix if os.name == 'nt' else prefix / 'bin').mkdir(parents=True)
    (prefix / ('python.exe' if os.name == 'nt' else 'bin/python')).write_bytes(b'synthetic')
    def job(frames, config, **kwargs):
        assert len(frames) == 1 and frames[0].source_file == str(tmp_path / 'photo.JPG')
        assert config.engine_command == ('conda.exe', 'run', '--no-capture-output', '--prefix', str(prefix), 'python')
        assert kwargs['inputs_unchanged']()
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE image_frames SET altitude_m=101 WHERE frame_id='F'")
        assert not kwargs['inputs_unchanged']()
        return 'synthetic_result'
    monkeypatch.setattr(module, 'run_opensfm_rgb_pilot', job)
    assert module.execute(db, 'P', 'conda.exe', prefix, tmp_path,
                          lambda: False, lambda text: None, lambda path: None) == 'synthetic_result'
    # Only this test deliberately wrote the change; the read-only path did not.
    assert before != db.read_bytes()


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='Native Tk needs display')
@pytest.mark.parametrize('cancel_run', [False, True])
def test_native_tk_explicit_project_start_workspace_and_result_or_cancel(tmp_path, monkeypatch, cancel_run):
    import tkinter as tk
    from tkinter import filedialog, ttk
    module = launcher()
    db = tmp_path / 'existing.sqlite3'
    database(db)
    before = db.read_bytes()
    output = tmp_path / 'private'
    output.mkdir()
    seen, errors, roots = [], [], []
    real_tk = tk.Tk
    started = threading.Event()
    outcome = {'finished': False}
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    def create_root(*args, **kwargs):
        root = real_tk(*args, **kwargs)
        roots.append(root)
        root.report_callback_exception = lambda *args: errors.append(args)
        root.after(20, lambda: activate(root))
        root.after(8000, root.destroy)
        return root
    def execute(*args):
        seen.append(args[:5])
        cancel, progress, workspace = args[5:]
        workspace(output)
        progress('synthetic stage')
        started.set()
        if cancel_run:
            deadline = time.monotonic() + 5
            while not cancel() and time.monotonic() < deadline:
                time.sleep(.02)
            assert cancel()
            raise module.PilotCancelled('synthetic')
        return SimpleNamespace(rgb_geotiff=output / 'ortho.tif')
    monkeypatch.setattr(tk, 'Tk', create_root)
    monkeypatch.setattr(filedialog, 'askopenfilename', lambda **kwargs: str(db))
    monkeypatch.setattr(filedialog, 'askdirectory', lambda **kwargs: str(output))
    monkeypatch.setattr(module, 'execute', execute)
    def button(root, text):
        return next(widget for widget in descendants(root)
                    if isinstance(widget, ttk.Button) and widget['text'] == text)
    def activate(root):
        picks = [widget for widget in descendants(root)
                 if isinstance(widget, ttk.Button) and widget['text'] == 'Auswaehlen']
        picks[0].invoke()
        picks[3].invoke()
        combo = next(widget for widget in descendants(root) if isinstance(widget, ttk.Combobox))
        assert combo.current() == -1
        combo.current(0)
        button(root, 'RGB-Pilot starten').invoke()
        root.after(50, lambda: finish(root))
    def finish(root):
        if not started.is_set():
            root.after(50, lambda: finish(root))
            return
        if cancel_run and 'cancelled' not in outcome:
            outcome['cancelled'] = True
            button(root, 'Abbrechen').invoke()
        if str(button(root, 'RGB-Pilot starten')['state']) != 'normal':
            root.after(50, lambda: finish(root))
            return
        assert str(button(root, 'Ausgabeordner oeffnen')['state']) == 'normal'
        outcome['finished'] = True
        button(root, 'Schliessen').invoke()
    try:
        module.window()
        assert not errors and outcome['finished']
        assert seen[0][:2] == (str(db), 'P')
        assert db.read_bytes() == before
    finally:
        monkeypatch.undo()
        roots.clear()
        gc.collect()
