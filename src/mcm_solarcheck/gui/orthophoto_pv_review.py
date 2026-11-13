"""Local, bounded PV proposals on existing orthophotos; no image reconstruction."""
from __future__ import annotations

from math import ceil, floor

import numpy as np
import rasterio
from rasterio.enums import ColorInterp, Resampling
from rasterio.windows import Window
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QDialog, QLabel, QPushButton, QRubberBand, QScrollArea, QVBoxLayout,
)

from mcm_solarcheck.gui.orthophoto_comparison import _pixmap_from_rgb
from mcm_solarcheck.services.orthophoto_layer_alignment import inspect_orthophoto_layer_pair
from mcm_solarcheck.services.orthophoto_pv_modules import detect_orthophoto_pv_window


class OrthophotoROIImage(QLabel):
    """Map a visible rectangle to original RGB pixels, without resizing analysis."""

    selection_changed = Signal(object)

    def __init__(self, rgb, native_size, parent=None):
        super().__init__(parent)
        self.setObjectName("orthophoto_pv_roi_image")
        self.setPixmap(_pixmap_from_rgb(rgb))
        self.setFixedSize(rgb.shape[1], rgb.shape[0])
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._native_width, self._native_height = native_size
        self._origin = None
        self._rubber = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.selected_window = None

    def _inside(self, position):
        return QPoint(max(0, min(self.width()-1, position.x())),
                      max(0, min(self.height()-1, position.y())))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = self._inside(event.position().toPoint())
            self._rubber.setGeometry(QRect(self._origin, self._origin))
            self._rubber.show()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _rectangle(self, end):
        left, right = sorted((self._origin.x(), end.x()))
        top, bottom = sorted((self._origin.y(), end.y()))
        return QRect(left, top, right-left+1, bottom-top+1)

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._rubber.setGeometry(self._rectangle(self._inside(event.position().toPoint())))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            super().mouseReleaseEvent(event)
            return
        rect = self._rectangle(self._inside(event.position().toPoint()))
        self._rubber.setGeometry(rect)
        sx, sy = self._native_width/self.width(), self._native_height/self.height()
        left, top = floor(rect.left()*sx), floor(rect.top()*sy)
        right = min(self._native_width, ceil((rect.right()+1)*sx))
        bottom = min(self._native_height, ceil((rect.bottom()+1)*sy))
        self.selected_window = (left, top, right-left, bottom-top)
        self._origin = None
        self.selection_changed.emit(self.selected_window)
        event.accept()


def _rgb_pixels(dataset, bands, *, out_shape=None, window=None):
    options = {"window": window} if window is not None else {}
    if out_shape is not None:
        options.update(out_shape=(3, *out_shape), resampling=Resampling.bilinear)
    pixels = dataset.read(bands, **options)
    mask_options = {"window": window} if window is not None else {}
    if out_shape is not None:
        mask_options.update(out_shape=(3, *out_shape), resampling=Resampling.nearest)
    valid = np.all(dataset.read_masks(bands, **mask_options) > 0, axis=0)
    for plane, band in zip(pixels, bands):
        nodata = dataset.nodatavals[band-1]
        if nodata is not None:
            valid &= plane != nodata
    for index, color in enumerate(dataset.colorinterp, 1):
        if color == ColorInterp.alpha:
            alpha_options = {"window": window} if window is not None else {}
            if out_shape is not None:
                alpha_options.update(out_shape=out_shape, resampling=Resampling.nearest)
            valid &= dataset.read(index, **alpha_options) > 0
    image = np.moveaxis(pixels, 0, -1).copy()
    image[~valid] = 0
    return image


class OrthophotoPVReviewDialog(QDialog):
    """Select an RGB region and inspect existing detector/thermal-map proposals."""

    def __init__(self, rgb_path, thermal_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PV-Modulvorschläge aus Orthofotos")
        self.setObjectName("orthophoto_pv_review_dialog")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._pair = inspect_orthophoto_layer_pair(rgb_path, thermal_path)
        self.proposal_result = None
        self._window = None
        with rasterio.open(self._pair.rgb_path) as dataset:
            factor = min(1., 1024/max(dataset.width, dataset.height))
            width, height = max(1, round(dataset.width*factor)), max(1, round(dataset.height*factor))
            overview = _rgb_pixels(dataset, self._pair.rgb_bands, out_shape=(height, width))
            native_size = (dataset.width, dataset.height)
        layout = QVBoxLayout(self)
        help_text = QLabel(
            "Einen Bereich im RGB-Orthofoto mit der Maus markieren. "
            "Die Vorschläge werden in Originalauflösung geprüft und dem "
            "Thermal-Orthofoto zugeordnet. Große Bereiche bitte kleiner wählen.", self)
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self._selection_image = OrthophotoROIImage(overview, native_size, self)
        self._selection_image.selection_changed.connect(self._select_window)
        scroll = QScrollArea(self)
        scroll.setObjectName("orthophoto_pv_selection_scroll")
        scroll.setWidgetResizable(False)
        scroll.setWidget(self._selection_image)
        layout.addWidget(scroll)
        self._status = QLabel("Noch kein Bereich ausgewählt.", self)
        self._status.setObjectName("orthophoto_pv_status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self._run = QPushButton("PV-Modulvorschläge suchen", self)
        self._run.setObjectName("orthophoto_pv_detect_button")
        self._run.setEnabled(False)
        self._run.clicked.connect(self._run_detection)
        layout.addWidget(self._run)
        self._output = QLabel(self)
        self._output.setObjectName("orthophoto_pv_result_image")
        self._output.setAlignment(Qt.AlignmentFlag.AlignCenter)
        output_scroll = QScrollArea(self)
        output_scroll.setObjectName("orthophoto_pv_result_scroll")
        output_scroll.setWidgetResizable(False)
        output_scroll.setWidget(self._output)
        output_scroll.setMinimumHeight(120)
        output_scroll.setMaximumHeight(380)
        layout.addWidget(output_scroll)
        note = QLabel("Vorschläge zur Fachprüfung; keine Modul-, Registrierungs- oder Temperaturfreigabe.", self)
        note.setWordWrap(True)
        layout.addWidget(note)
        close = QPushButton("Schließen", self)
        close.clicked.connect(self.close)
        layout.addWidget(close)
        self.resize(min(1080, width+40), min(850, height+300))

    def _select_window(self, window):
        self.proposal_result = None
        self._output.clear()
        self._window = window
        accepted = 1 <= window[2] <= 2048 and 1 <= window[3] <= 2048
        self._run.setEnabled(accepted)
        self._status.setText(
            "Bereich ausgewählt. Modulvorschläge können geprüft werden." if accepted else
            "Der Bereich ist zu groß. Bitte einen kleineren Ausschnitt markieren "
            "(höchstens 2048 × 2048 Originalpixel).")

    def _run_detection(self):
        if self._window is None or not self._run.isEnabled():
            return
        self._run.setEnabled(False)
        try:
            result = detect_orthophoto_pv_window(
                self._pair.rgb_path, self._pair.thermal_path, window=self._window,
            )
            col, row, width, height = self._window
            with rasterio.open(self._pair.rgb_path) as dataset:
                image = _rgb_pixels(dataset, self._pair.rgb_bands,
                                    window=Window(col, row, width, height))
            factor = min(1., 1024/max(width, height))
            pixmap = _pixmap_from_rgb(image)
            if factor < 1:
                pixmap = pixmap.scaled(max(1, round(width*factor)), max(1, round(height*factor)),
                                       Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(0, 220, 160), 2))
            for proposal in result.proposals:
                painter.drawPolygon(QPolygonF([
                    QPointF((x-col)*factor, (y-row)*factor)
                    for x, y in proposal.rgb_polygon_px
                ]))
            painter.end()
            self._output.setPixmap(pixmap)
            self._output.resize(pixmap.size())
            self.proposal_result = result
            summary = result.summary()
            self._status.setText(
                f"{summary['module_proposal_count']} Modulvorschläge; "
                f"{summary['proposals_with_thermal_coverage']} mit Thermalabdeckung. "
                "Zuordnung anhand der GeoTIFF-Georeferenzierung; keine Temperaturauswertung.")
        except (ValueError, TypeError, OSError, RuntimeError) as error:
            self.proposal_result = None
            self._status.setText(f"Modulprüfung nicht möglich: {error}")
        finally:
            self._run.setEnabled(True)


def show_orthophoto_pv_review(rgb_path, thermal_path, parent=None):
    """Open a nonmodal review window; the caller retains the returned dialog."""
    dialog = OrthophotoPVReviewDialog(rgb_path, thermal_path, parent)
    dialog.show()
    return dialog
