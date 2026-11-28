"""Existing Qt overlay used for a labelled local note and reopening, synthetic only."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QLabel, QSlider, QPushButton

from mcm_solarcheck.gui.thermal_partial_comparison import PartialThermalComparisonWindow
from mcm_solarcheck.services import thermal_partial_comparison as comparison
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source


@pytest.fixture(scope='module')
def qapp():
    return QApplication.instance() or QApplication([])


def test_overlay_slider_zoom_note_save_close_reopen_and_cancel_preserve_sources(scene, qapp):
    source, folder, rgb, thermal = scene
    before = {p: p.read_bytes() for p in (rgb, thermal)}
    value = comparison.open_partial_comparison(source, rgb)
    window = PartialThermalComparisonWindow(value)
    assert 'unvollständig: 8 von 10 Bildern' in window.findChild(
        QLabel, 'orthophoto_comparison_incomplete_notice').text()
    slider = window.findChild(QSlider, 'orthophoto_thermal_opacity_slider')
    image = window.findChild(QLabel, 'orthophoto_comparison_image')
    slider.setValue(0)
    assert image.pixmap().toImage().pixelColor(3, 2).getRgb() == (30, 30, 30, 255)
    slider.setValue(100)
    assert image.pixmap().toImage().pixelColor(3, 2).getRgb() == (80, 80, 80, 255)
    slider.setValue(70)
    window.findChild(QPushButton, 'orthophoto_zoom_in').click()
    window.verdict.setCurrentIndex(2)
    window.note.setPlainText('Synthetic visible offset at edge')
    window.findChild(QPushButton, 'partial_comparison_save').click()
    assert 'gespeichert' in window.status.text()
    window.close()
    reopened = PartialThermalComparisonWindow(comparison.open_partial_comparison(source))
    assert reopened.viewer.view_state() == dict(opacity=70, zoom=1.25)
    assert reopened.verdict.currentData() == 'visible_offset'
    assert reopened.note.toPlainText() == 'Synthetic visible offset at edge'
    saved_bytes = (folder / comparison.STATE).read_bytes()
    reopened.note.setPlainText('Do not save this change')
    reopened.close()
    assert (folder / comparison.STATE).read_bytes() == saved_bytes
    assert all(p.read_bytes() == data for p, data in before.items())


def test_comparison_script_file_selection_cancel_and_actual_window_reopen(scene, qapp, monkeypatch):
    import importlib.util
    from pathlib import Path
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QFileDialog
    source, folder, rgb, thermal = scene
    spec = importlib.util.spec_from_file_location('thermal_rgb_compare_script',
        Path(__file__).resolve().parents[1] / 'scripts/MCM_SolarCheck_THERMAL_RGB_VERGLEICH.py')
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: ('', ''))
    assert script.main(['--source', str(source)]) == 0
    assert not (folder / comparison.STATE).exists()
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(rgb), 'GeoTIFF'))
    errors, done = [], []
    def inspect_window():
        try:
            window = next(w for w in qapp.topLevelWidgets()
                          if isinstance(w, PartialThermalComparisonWindow) and w.isVisible())
            assert window.comparison.label == 'unvollständig: 8 von 10 Bildern'
            window.note.setPlainText('Saved through actual standalone entry point')
            window.save()
            assert 'gespeichert' in window.status.text()
            window.close()
            done.append(True)
        except BaseException as error:
            errors.append(error)
        finally:
            qapp.quit()
    QTimer.singleShot(50, inspect_window)
    assert script.main(['--source', str(source)]) == 0
    assert done and not errors
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: pytest.fail('Restore saved RGB without dialog'))
    done.clear()
    QTimer.singleShot(50, inspect_window)
    assert script.main(['--source', str(source)]) == 0
    assert done and not errors
