"""Read-only RGB/thermal orthophoto comparison widget for the Windows desktop.

Both layers must first be aligned by the GIS service; slider changes display
opacity only and never modifies source rasters or export files.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget


def _pixmap_from_rgb(rgb: np.ndarray) -> QPixmap:
    image = np.ascontiguousarray(rgb, dtype=np.uint8)
    height, width, _ = image.shape
    return QPixmap.fromImage(QImage(
        image.data, width, height, image.strides[0], QImage.Format.Format_RGB888
    ).copy())


class OrthophotoComparisonWidget(QWidget):
    """Overlay geographically aligned arrays using an interactive opacity slider."""

    def __init__(self, rgb: np.ndarray, thermal: np.ndarray, parent=None):
        super().__init__(parent)
        if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError("RGB layer must be uint8 HxWx3")
        if thermal.ndim != 2 or thermal.shape != rgb.shape[:2]:
            raise ValueError("Thermal layer must match aligned RGB grid")
        self._rgb = rgb.copy()
        self._thermal = thermal.astype(np.float32, copy=True)
        self._label = QLabel(self)
        self._label.setObjectName("orthophoto_comparison_image")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._slider.setObjectName("orthophoto_thermal_opacity_slider")
        self._slider.setRange(0, 100)
        self._slider.setValue(50)
        self._slider.valueChanged.connect(self._update_image)
        layout = QVBoxLayout(self)
        layout.addWidget(self._label)
        layout.addWidget(QLabel("RGB ← Ebenenüberblendung → Thermal", self))
        layout.addWidget(self._slider)
        self._update_image()

    def _update_image(self, *_args):
        valid = np.isfinite(self._thermal)
        thermal_rgb = np.zeros_like(self._rgb)
        if valid.any():
            values = self._thermal[valid]
            low, high = np.percentile(values, (2, 98))
            if high > low:
                normalized = np.clip((values - low) * 255 / (high - low), 0, 255)
            else:
                normalized = np.full(values.shape, 128)
            thermal_rgb[valid, 0] = normalized.astype(np.uint8)
            thermal_rgb[valid, 1] = (255 - normalized).astype(np.uint8)
        alpha = self._slider.value() / 100.0
        weights = np.where(valid, alpha, 0.0)[..., None]
        composed = np.clip(
            self._rgb.astype(np.float32) * (1 - weights)
            + thermal_rgb.astype(np.float32) * weights,
            0, 255,
        ).astype(np.uint8)
        self._label.setPixmap(_pixmap_from_rgb(composed))
