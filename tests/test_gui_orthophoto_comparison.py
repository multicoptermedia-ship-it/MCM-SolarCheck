"""Desktop comparison slider regression tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QLabel, QSlider

from mcm_solarcheck.gui.orthophoto_comparison import OrthophotoComparisonWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_slider_displays_two_aligned_layers_without_changing_arrays(qapp):
    rgb = np.full((4, 5, 3), 30, dtype=np.uint8)
    thermal = np.full((4, 5), 42, dtype=np.float32)
    thermal[:, 0] = np.nan
    original_rgb = rgb.copy()
    original_thermal = thermal.copy()
    widget = OrthophotoComparisonWidget(rgb, thermal)
    slider = widget.findChild(QSlider, "orthophoto_thermal_opacity_slider")
    label = widget.findChild(QLabel, "orthophoto_comparison_image")
    assert slider.minimum() == 0 and slider.maximum() == 100
    assert not label.pixmap().isNull()
    slider.setValue(100)
    assert not label.pixmap().isNull()
    slider.setValue(0)
    assert np.array_equal(rgb, original_rgb)
    assert np.array_equal(thermal, original_thermal, equal_nan=True)


def test_widget_rejects_unaligned_layers(qapp):
    with pytest.raises(ValueError, match="match"):
        OrthophotoComparisonWidget(
            np.zeros((3, 4, 3), dtype=np.uint8),
            np.zeros((4, 3), dtype=np.float32),
        )
