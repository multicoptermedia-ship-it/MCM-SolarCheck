"""Read-only RGB/thermal orthophoto comparison widget for the Windows desktop.

Both layers must first be aligned by the GIS service; slider changes display
opacity only and never modifies source rasters or export files.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QScrollArea, QSlider, QHBoxLayout, QVBoxLayout, QWidget


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
        self._zoom = 1.0
        self._label = QLabel(self)
        self._label.setObjectName("orthophoto_comparison_image")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._slider.setObjectName("orthophoto_thermal_opacity_slider")
        self._slider.setRange(0, 100)
        self._slider.setValue(50)
        self._slider.valueChanged.connect(self._update_image)
        layout = QVBoxLayout(self)
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName('orthophoto_comparison_scroll_area')
        self._scroll.setWidgetResizable(False)
        self._scroll.setWidget(self._label)
        layout.addWidget(self._scroll)
        controls = QHBoxLayout()
        for title, factor, name in (('−', 0.8, 'orthophoto_zoom_out'), ('+', 1.25, 'orthophoto_zoom_in')):
            button = QPushButton(title, self)
            button.setObjectName(name)
            button.clicked.connect(lambda checked=False, f=factor: self._set_zoom(self._zoom * f))
            controls.addWidget(button)
        reset = QPushButton('100 %', self)
        reset.setObjectName('orthophoto_zoom_reset')
        reset.clicked.connect(lambda: self._set_zoom(1.0))
        controls.addWidget(reset)
        layout.addLayout(controls)
        layout.addWidget(QLabel("RGB ← Ebenenüberblendung → Thermal", self))
        layout.addWidget(self._slider)
        self._update_image()

    def _set_zoom(self, value: float):
        self._zoom = max(0.25, min(4.0, value))
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
        pixmap = _pixmap_from_rgb(composed)
        from PySide6.QtCore import QSize
        size = QSize(max(1, round(pixmap.width() * self._zoom)), max(1, round(pixmap.height() * self._zoom)))
        self._label.setPixmap(pixmap.scaled(size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self._label.resize(size)
