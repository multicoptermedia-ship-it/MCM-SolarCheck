"""Synthetic incomplete preview; never relax the full-result gates."""
import json

import pytest

from mcm_solarcheck.services import opensfm_rgb_pilot as pilot
from mcm_solarcheck.services import opensfm_thermal_partial as partial
from mcm_solarcheck.services.colmap_openmvs_pilot import PilotError, PilotCancelled, PilotTimeout
from test_opensfm_sparse_bridge import sparse_source
from test_opensfm_thermal_pilot import thermal_engine


def prepare(source):
    (source / 'reference_lla.json').write_text('{"latitude":50,"longitude":8,"altitude":100}')
    (source / 'tracks.csv').write_text('synthetic saved tracks')


def test_separate_incomplete_preview_reopens_without_matching_or_raw_decode(sparse_source, monkeypatch):
    source, config = sparse_source
    prepare(source)
    before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    monkeypatch.setattr(pilot, '_require_thermal_copy', lambda *a: pytest.fail('No raw inventory'))
    calls = []
    folder, report = partial.run_partial_preview(source, config, executor=thermal_engine(calls))
    assert calls == list(pilot.STAGES[5:])
    assert all(p.read_bytes() == data for p, data in before.items())
    assert {p for p in source.rglob('*') if p.is_file()} == set(before)
    assert folder.parent == source.parent and folder != source
    assert len(list((folder / 'images').iterdir())) == 8
    assert len(json.loads((folder / 'reconstruction.json').read_text())) == 1
    assert report['included_images'] == 8 and report['excluded_images'] == 2
    assert report['source_images'] == 10 and report['incomplete']
    assert report['status'] == 'finished'
    for key in ('thermal_created', 'orthophoto_created', 'temperature_verified', 'georeferencing_verified'):
        assert report[key] is False
    assert not (folder / 'job.json').exists()
    assert not (folder / 'undistorted/depthmaps/ortho.tif').exists()
    assert (folder / 'undistorted/depthmaps/UNVOLLSTAENDIG_THERMAL_TEILVORSCHAU.tif').is_file()
    assert partial.read_partial_preview(source) == (folder, report)
    import rasterio
    output = folder / 'undistorted/depthmaps/UNVOLLSTAENDIG_THERMAL_TEILVORSCHAU.tif'
    with rasterio.open(output) as raster:
        tags = raster.tags()
        assert tags['SOLARCHECK_LABEL'] == 'unvollständig: 8 von 10 Bildern'
        assert tags['SOLARCHECK_INCOMPLETE'] == 'true'
        assert tags['SOLARCHECK_PAIR_IMPORT_ALLOWED'] == 'false'
        assert tags['SOLARCHECK_TEMPERATURE_VERIFIED'] == 'false'
    excluded = json.loads((folder / 'excluded-images.LOCAL.json').read_text())
    assert [item['working_name'] for item in excluded] == ['000009.JPG', '000010.JPG']
    assert all(item['source_file'] and item['frame_id'] for item in excluded)
    assert not pilot.read_opensfm_metrics(source)['registration_complete']
    assert str(source) not in json.dumps(report) and 'latitude' not in json.dumps(report)
    with pytest.raises(PilotError, match='bereits'):
        partial.run_partial_preview(source, config, executor=lambda *a, **k: pytest.fail('No repeat'))


@pytest.mark.parametrize('failure', ['checksum', 'geometry', 'timeout', 'cancel', 'raster', 'mutation'])
def test_failures_preserve_source_and_never_finish(sparse_source, failure):
    source, config = sparse_source
    prepare(source)
    if failure == 'checksum':
        (source / 'images/000001.JPG').write_bytes(b'changed')
    if failure == 'geometry':
        path = source / 'reconstruction.json'
        models = json.loads(path.read_text())
        models[0]['shots']['000001.JPG']['translation'][0] = float('nan')
        path.write_text(json.dumps(models))
    calls = []
    delegate = thermal_engine(calls)
    def execute(executable, args, folder, log, cancel, **kwargs):
        if failure == 'timeout':
            raise PilotTimeout('synthetic')
        if failure == 'cancel':
            raise PilotCancelled('synthetic')
        delegate(executable, args, folder, log, cancel, **kwargs)
        if failure == 'mutation':
            (source / 'tracks.csv').write_text('changed')
        if failure == 'raster' and 'dense_merging' in args:
            (folder / 'undistorted/depthmaps/ortho.tif').unlink()
    with pytest.raises((PilotError, OSError)):
        partial.run_partial_preview(source, config, executor=execute)
    folder, report = partial.read_partial_preview(source)
    assert report['status'] in ('failed', 'cancelled')
    assert not report['orthophoto_created'] and not report['thermal_created']
    if failure in ('checksum', 'geometry'):
        assert calls == []
    assert not (folder / 'undistorted/depthmaps/UNVOLLSTAENDIG_THERMAL_TEILVORSCHAU.tif').exists()


@pytest.mark.skipif(__import__('os').name != 'nt' and not __import__('os').environ.get('DISPLAY'),
                    reason='Native Tk needs display')
@pytest.mark.parametrize('abort', [False, True])
def test_native_partial_button_reopens_and_preserves_incomplete_source(sparse_source, monkeypatch, abort):
    import gc
    import threading
    import time
    import tkinter as tk
    from tkinter import filedialog, ttk
    from test_opensfm_rgb_launcher import launcher
    source, config = sparse_source
    prepare(source)
    module = launcher()
    roots, errors, done = [], [], []
    working = threading.Event()
    interrupted_once, continued = [], []
    real_tk = tk.Tk
    delegate = thermal_engine([])
    def engine(*args, **kwargs):
        if abort and not interrupted_once:
            interrupted_once.append(True)
            working.set()
            deadline = time.monotonic() + 5
            while not args[5]() and time.monotonic() < deadline:
                time.sleep(.02)
            assert args[5]()
            raise PilotCancelled('synthetic')
        return delegate(*args, **kwargs)
    monkeypatch.setattr(module, 'saved_config', lambda *a: config)
    monkeypatch.setattr(module, 'run_partial_preview', lambda *a, **k:
        partial.run_partial_preview(*a, **k, executor=engine))
    monkeypatch.setattr(module, 'continue_partial_preview', lambda *a, **k:
        partial.continue_partial_preview(*a, **k, executor=engine))
    monkeypatch.setattr(module, 'execute_bridge', lambda *a, **k: pytest.fail('No matching'))
    monkeypatch.setattr(module, 'execute', lambda *a, **k: pytest.fail('No new import'))
    monkeypatch.setattr(filedialog, 'askdirectory', lambda **k: str(source))
    def descendants(root):
        for child in root.winfo_children():
            yield child
            yield from descendants(child)
    def button(root, text):
        return next(w for w in descendants(root) if isinstance(w, ttk.Button) and w['text'] == text)
    def activate(root):
        button(root, 'Lauf laden').invoke()
        assert not button(root, 'Zusatzabgleich starten').winfo_manager()
        button(root, 'Unvollstaendige Thermal-Teilvorschau').invoke()
        root.after(50, lambda: finish(root))
    def finish(root):
        if abort and working.is_set() and not continued:
            button(root, 'Abbrechen').invoke()
        if str(button(root, 'Kennzahlen kopieren')['state']) != 'normal':
            root.after(50, lambda: finish(root))
            return
        folder, report = partial.read_partial_preview(source)
        if abort and not continued:
            assert report['status'] == 'cancelled'
            button(root, 'Lauf laden').invoke()
            continued.append(True)
            button(root, 'Teilvorschau fortsetzen').invoke()
            root.after(50, lambda: finish(root))
            return
        assert report['status'] == 'finished'
        button(root, 'Lauf laden').invoke()
        labels = [str(w.cget('text')) for w in descendants(root) if isinstance(w, ttk.Label)]
        assert any('UNVOLLSTAENDIGE' in text and 'unvollständig: 8 von 10 Bildern' in text for text in labels)
        button(root, 'Kennzahlen kopieren').invoke()
        original = json.loads(root.clipboard_get())
        assert not original['registration_complete'] and not original['thermal_created']
        done.append(True)
        button(root, 'Schliessen').invoke()
    def create(*a, **k):
        root = real_tk(*a, **k)
        roots.append(root)
        root.report_callback_exception = lambda *args: errors.append(args)
        root.after(20, lambda: activate(root))
        root.after(8000, root.destroy)
        return root
    monkeypatch.setattr(tk, 'Tk', create)
    try:
        module.window(modality='thermal')
        assert done and not errors, [(str(e[0]), str(e[1])) for e in errors]
    finally:
        monkeypatch.undo()
        roots.clear()
        gc.collect()


@pytest.mark.parametrize('stop', ['cancel', 'timeout'])
def test_continue_partial_only_unfinished_native_stages_and_reopen(sparse_source, stop):
    source, config = sparse_source
    prepare(source)
    before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    calls = []
    delegate = thermal_engine(calls)
    def interrupted(executable, args, folder, log, cancel, **kwargs):
        if 'compute_depthmaps' in args:
            raise (PilotCancelled if stop == 'cancel' else PilotTimeout)('synthetic')
        delegate(executable, args, folder, log, cancel, **kwargs)
    with pytest.raises(PilotError):
        partial.run_partial_preview(source, config, executor=interrupted)
    folder, old = partial.read_partial_preview(source)
    assert old['status'] == ('cancelled' if stop == 'cancel' else 'failed')
    assert calls == ['undistort', 'dense_clustering']
    calls.clear()
    continued, report = partial.continue_partial_preview(source, config, executor=thermal_engine(calls))
    assert continued == folder
    assert calls == ['compute_depthmaps', 'fuse_depthmaps', 'dense_merging']
    assert partial.read_partial_preview(source) == (continued, report)
    assert report['incomplete'] and not report['thermal_created'] and not report['georeferencing_verified']
    assert all(p.read_bytes() == data for p, data in before.items())
    assert {p for p in source.rglob('*') if p.is_file()} == set(before)
    with pytest.raises(PilotError, match='gestoppte'):
        partial.continue_partial_preview(source, config, executor=lambda *a, **k: pytest.fail('Finished'))


@pytest.mark.parametrize('mutate', ['source_pose', 'preview_pose', 'preview_image'])
def test_resume_refuses_changed_saved_geometry_and_working_copies(sparse_source, mutate):
    source, config = sparse_source
    prepare(source)
    with pytest.raises(PilotTimeout):
        partial.run_partial_preview(source, config, executor=lambda *a, **k: (_ for _ in ()).throw(PilotTimeout('synthetic')))
    folder, _ = partial.read_partial_preview(source)
    path = (source / 'reconstruction.json' if mutate == 'source_pose' else
            folder / ('reconstruction.json' if mutate == 'preview_pose' else 'images/000001.JPG'))
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(PilotError, match='veraendert'):
        partial.continue_partial_preview(source, config, executor=lambda *a, **k: pytest.fail('No engine'))
