"""Tk starts only the app's separate Qt viewer, never the engine or database."""
import gc
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from test_opensfm_rgb_launcher import launcher
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source


def test_launch_uses_app_python_and_fixed_companion_with_explicit_selected_run(scene):
    source, folder, rgb, thermal = scene
    module = launcher()
    seen = []
    def popen(args, **kwargs):
        seen.append(args)
        assert kwargs == dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 'synthetic child'
    assert module.launch_partial_comparison(source, choose_rgb=True, popen=popen) == 'synthetic child'
    assert seen == [[module.sys.executable,
                     str(Path(module.__file__).with_name('MCM_SolarCheck_THERMAL_RGB_VERGLEICH.py')),
                     '--source', str(source), '--choose-rgb']]


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='Native Tk needs display')
def test_native_load_completed_preview_and_start_or_reselect_rgb(scene, monkeypatch):
    import tkinter as tk
    from tkinter import ttk, filedialog
    source, folder, rgb, thermal = scene
    module = launcher()
    roots, calls, errors, done = [], [], [], []
    real_tk = tk.Tk
    def descendants(root):
        for child in root.winfo_children():
            yield child
            yield from descendants(child)
    def button(root, text):
        return next(w for w in descendants(root) if isinstance(w, ttk.Button) and w['text'] == text)
    def activate(root):
        button(root, 'Lauf laden').invoke()
        assert str(button(root, 'RGB vergleichen')['state']) == 'normal'
        button(root, 'RGB vergleichen').invoke()
        button(root, 'Anderes RGB wählen').invoke()
        assert calls == [(source, False), (source, True)]
        done.append(True)
        button(root, 'Schliessen').invoke()
    def create(*args, **kwargs):
        root = real_tk(*args, **kwargs)
        roots.append(root)
        root.report_callback_exception = lambda *args: errors.append(args)
        root.after(20, lambda: activate(root))
        root.after(8000, root.destroy)
        return root
    def launch(path, *, choose_rgb=False):
        calls.append((path, choose_rgb))
        return SimpleNamespace(poll=lambda: 0)
    monkeypatch.setattr(tk, 'Tk', create)
    monkeypatch.setattr(filedialog, 'askdirectory', lambda **kwargs: str(source))
    monkeypatch.setattr(module, 'launch_partial_comparison', launch)
    monkeypatch.setattr(module, 'execute', lambda *a, **k: pytest.fail('No engine'))
    try:
        module.window(modality='thermal')
        assert done and not errors, [(str(e[0]), str(e[1])) for e in errors]
    finally:
        monkeypatch.undo()
        roots.clear()
        gc.collect()
