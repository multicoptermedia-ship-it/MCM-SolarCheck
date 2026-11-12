"""Read-only project bridge and actual Tk flow; synthetic local records only."""
import gc
import importlib.util
import json
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
        (output / 'job.json').write_text(json.dumps({
            'expected_engine_source': '8b6b77efddebf4429044d3206c7dc21c4e767e08',
            'project_label': 'Synthetic project', 'started_at': '2026-11-10T20:43:00+01:00'}))
        (output / 'laufzeiten.json').write_text(json.dumps({
            'status': 'cancelled' if cancel_run else 'finished', 'rgb_images': 3, 'steps': []}))
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
        button(root, 'Kennzahlen kopieren').invoke()
        assert json.loads(root.clipboard_get())['pipeline'] == 'opensfm_rgb'
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


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='Native Tk needs display')
@pytest.mark.parametrize('wrong_engine', [False, True])
def test_native_tk_loads_old_run_and_copies_only_opensfm_metrics_without_recalculation(tmp_path, monkeypatch, wrong_engine):
    import tkinter as tk
    from tkinter import filedialog, ttk
    from mcm_solarcheck.services.opensfm_rgb_pilot import ENGINE_SOURCE, STAGES
    module = launcher()
    folder = tmp_path / ('rgb-pilot-old' if wrong_engine else 'opensfm-rgb-old')
    folder.mkdir()
    (folder / 'job.json').write_text(json.dumps({} if wrong_engine else {'expected_engine_source': ENGINE_SOURCE}))
    (folder / 'laufzeiten.json').write_text(json.dumps({'status': 'failed', 'rgb_images': 3,
        'elapsed_seconds': 60, 'steps': [{'stage': 'COLMAP-Bildabgleich' if wrong_engine else STAGES[0],
                                        'status': 'failed', 'seconds': 60}]}))
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    errors, outcome, roots = [], {'checked': False}, []
    real_tk = tk.Tk
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    def activate(root):
        widgets = list(descendants(root))
        button = lambda text: next(widget for widget in widgets
                                  if isinstance(widget, ttk.Button) and widget['text'] == text)
        button('Lauf laden').invoke()
        if wrong_engine:
            assert str(button('Kennzahlen kopieren')['state']) == 'disabled'
        else:
            assert str(button('Kennzahlen kopieren')['state']) == 'normal'
            button('Kennzahlen kopieren').invoke()
            result = json.loads(root.clipboard_get())
            assert result['pipeline'] == 'opensfm_rgb' and result['status'] == 'failed'
            assert 'stored_depthmaps' in result
        outcome['checked'] = True
        button('Schliessen').invoke()
    def create(*args, **kwargs):
        root = real_tk(*args, **kwargs)
        roots.append(root)
        root.report_callback_exception = lambda *args: errors.append(args)
        root.after(20, lambda: activate(root))
        root.after(8000, root.destroy)
        return root
    monkeypatch.setattr(tk, 'Tk', create)
    monkeypatch.setattr(filedialog, 'askdirectory', lambda **kwargs: str(folder))
    monkeypatch.setattr(module, 'execute', lambda *args: pytest.fail('Loading metrics must not start an engine'))
    try:
        module.window()
        assert not errors and outcome['checked']
        assert {path.name: path.read_bytes() for path in folder.iterdir()} == before
    finally:
        monkeypatch.undo()
        roots.clear()
        gc.collect()


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='Native Tk needs display')
@pytest.mark.parametrize('continue_cancel', [False, True])
def test_native_tk_checks_saved_depthmaps_continues_and_reopens_report_without_new_job(tmp_path, monkeypatch, continue_cancel):
    import tkinter as tk
    from tkinter import filedialog, ttk
    from mcm_solarcheck.services import opensfm_rgb_pilot as pilot
    from mcm_solarcheck.services import opensfm_dense_continuation as resume
    module = launcher()
    folder = tmp_path / 'opensfm-rgb-synthetic'
    folder.mkdir()
    report = {'status': 'failed', 'registration_complete': True, 'rgb_images': 3,
              'steps': [{'stage': s, 'status': 'finished' if i < 7 else 'failed'}
                        for i, s in enumerate(pilot.STAGES[:8])]}
    (folder / 'job.json').write_text(json.dumps({'expected_engine_source': pilot.ENGINE_SOURCE}))
    (folder / 'laufzeiten.json').write_text(json.dumps(report))
    before = {p: p.read_bytes() for p in folder.iterdir()}
    calls, roots, errors = [], [], []
    done = {'value': False}
    continuing = threading.Event()
    real_tk = tk.Tk
    def descendants(w):
        for c in w.winfo_children():
            yield c
            yield from descendants(c)
    def button(root, text):
        return next(w for w in descendants(root) if isinstance(w, ttk.Button) and w['text'] == text)
    def inspect(workspace, conda, environment, cancel):
        assert Path(workspace) == folder and not cancel()
        calls.append(workspace)
        detail = dict.fromkeys(pilot.CACHE_COUNTS, 0)
        detail.update(check='solarcheck-opensfm-cache-1', status='completed', working_images=3,
                      raw_readable=2, clusters=2, clusters_fully_cached=1, clusters_without_cache=1, clustered_images=3,
                      changed_during_check=False, geometric_quality_verified=False, resume_implemented=False)
        result = {**report, 'depthmap_cache_check': detail}
        inspection = folder / 'cache-check-abc12345'
        inspection.mkdir()
        (inspection / 'Kennzahlen.json').write_text(json.dumps(result))
        return result
    def continue_saved(workspace, conda, environment, cancel, progress):
        assert Path(workspace) == folder
        continuing.set()
        progress('synthetic dense continuation')
        if continue_cancel:
            deadline = time.monotonic() + 5
            while not cancel() and time.monotonic() < deadline:
                time.sleep(.02)
            assert cancel()
        attempt = folder / 'dense-resume-20261112_203000-abc12345'
        attempt.mkdir()
        record = dict(check=resume.CHECK, run_id=None, continuation_id=attempt.name,
            started_at='2026-11-12T20:30:00+01:00', status='cancelled' if continue_cancel else 'finished',
            elapsed_seconds=1,
            steps=[dict(stage=s, status='finished') for s in pilot.STAGES[7:]] if not continue_cancel else [],
            stored_depthmaps={'raw': 0, 'clean': 3}, reused_initial_stages=7,
            orthophoto_created=not continue_cancel, georeferencing_verified=False, temperature_verified=False,
            thermal_created=False, protected_digests={'PRIVATE PATH': 'not shareable'})
        (attempt / 'continuation.json').write_text(json.dumps(record))
        if continue_cancel:
            raise module.PilotCancelled('synthetic cancellation')
        return SimpleNamespace(rgb_geotiff=folder / 'synthetic-ortho.tif')
    def activate(root):
        button(root, 'Lauf laden').invoke()
        assert str(button(root, 'Tiefenkarten pruefen')['state']) == 'normal'
        button(root, 'Tiefenkarten pruefen').invoke()
        root.after(100, lambda: finish(root))
    def finish(root):
        if str(button(root, 'Kennzahlen kopieren')['state']) != 'normal':
            root.after(100, lambda: finish(root))
            return
        button(root, 'Lauf laden').invoke()
        button(root, 'Kennzahlen kopieren').invoke()
        result = json.loads(root.clipboard_get())
        assert result['depthmap_cache_check']['raw_readable'] == 2
        assert result['status'] == 'failed' and not result['depthmap_cache_check']['resume_implemented']
        assert str(button(root, 'Tiefenkarten fortsetzen')['state']) == 'normal'
        button(root, 'Tiefenkarten fortsetzen').invoke()
        root.after(50, lambda: finish_continuation(root))
    def finish_continuation(root):
        if not continuing.is_set():
            root.after(50, lambda: finish_continuation(root))
            return
        if continue_cancel and not done.get('cancelled'):
            done['cancelled'] = True
            button(root, 'Abbrechen').invoke()
        if str(button(root, 'Kennzahlen kopieren')['state']) != 'normal':
            root.after(50, lambda: finish_continuation(root))
            return
        button(root, 'Lauf laden').invoke()
        button(root, 'Kennzahlen kopieren').invoke()
        result = json.loads(root.clipboard_get())
        assert result['dense_continuation']['status'] == ('cancelled' if continue_cancel else 'finished')
        assert result['dense_continuation']['orthophoto_created'] is (not continue_cancel)
        assert 'PRIVATE PATH' not in json.dumps(result)
        done['value'] = True
        button(root, 'Schliessen').invoke()
    def create(*args, **kwargs):
        root = real_tk(*args, **kwargs)
        roots.append(root)
        root.report_callback_exception = lambda *args: errors.append(args)
        root.after(20, lambda: activate(root))
        root.after(8000, root.destroy)
        return root
    monkeypatch.setattr(tk, 'Tk', create)
    monkeypatch.setattr(filedialog, 'askdirectory', lambda **kw: str(folder))
    monkeypatch.setattr(module, 'execute_cache', inspect)
    monkeypatch.setattr(module, 'execute_continue', continue_saved)
    monkeypatch.setattr(module, 'execute', lambda *a: pytest.fail('No new photo job'))
    try:
        module.window()
        assert done['value'] and not errors and len(calls) == 1
        assert all(p.read_bytes() == v for p, v in before.items())
    finally:
        monkeypatch.undo()
        roots.clear()
        gc.collect()
