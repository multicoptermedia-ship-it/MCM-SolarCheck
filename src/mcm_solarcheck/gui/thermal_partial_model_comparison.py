"""Read-only side-by-side evidence in the existing native ROI result renderer."""
import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF
from PySide6.QtWidgets import QLabel, QScrollArea
from .orthophoto_pv_review import OrthophotoPVReviewDialog
from .thermal_partial_pv import _resizable_dialog
from ..services.thermal_partial_model_comparison import read_model_comparison


class ModelComparisonDialog(OrthophotoPVReviewDialog):
    def __init__(self, comparison, parent=None):
        self.comparison = comparison
        record, result, self.references = read_model_comparison(comparison)
        super().__init__(comparison.rgb_path, comparison.thermal_path, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        _resizable_dialog(self)
        self.setWindowTitle('KI-Modellvergleich – keine automatische Übernahme')
        self.setObjectName('partial_pv_model_result')
        self._selection_image.hide()
        self.findChild(QScrollArea, 'orthophoto_pv_selection_scroll').hide()
        self._run.hide()
        notice = QLabel(comparison.label + ' · Gelb: gespeicherte passende Umrisse; Grün: KI-Kandidaten. '
            'Keine automatische Übernahme, physische IDs, Geometrie- oder Celsiusfreigabe.')
        notice.setWordWrap(True)
        self.layout().insertWidget(0, notice)
        counts = record['counts']
        self.findChild(QLabel, 'orthophoto_pv_help').setText(
            f"Gespeicherte passende Umrisse: {counts['reviewed_outlines']} · "
            f"davon wiedergefunden: {counts['matched_reviewed_outlines']} · "
            f"nicht wiedergefunden: {counts['unmatched_reviewed_outlines']} · "
            f"zusätzliche ungeprüfte Kandidaten: {counts['additional_unreviewed_candidates']}. "
            'Die Referenz ist nicht vollständig: keine allgemeine Trefferquote oder Fehlerfreiheit ableiten.')
        self._window = result.rgb_window
        scroll = self.findChild(QScrollArea, 'orthophoto_pv_result_scroll')
        scroll.setMaximumHeight(16777215)
        self._render_result(result)
        self._status.setText('Vergleich separat lokal gespeichert. Bestehende Entwürfe/Beurteilungen bleiben erhalten. '
            f"Modell: {record['model']['model']['provider']} / {record['model']['model']['model_version']}")
        available = self.screen().availableGeometry()
        self.resize(min(1200, available.width()-40), min(850, available.height()-40))

    def _inspect_pair(self, rgb_path, thermal_path):
        return self.comparison._pair

    def _after_result(self, result):
        pixmap = self._output.pixmap().copy()
        painter = QPainter(pixmap)
        try:
            col, row, width, height = result.rgb_window
            factor = min(1., 1024/max(width, height))
            painter.setPen(QColor(0, 220, 160))
            for i, p in enumerate(result.proposals, 1):
                x, y = np.mean(p.rgb_polygon_px, axis=0)
                painter.drawText(QPointF((x-col)*factor, (y-row)*factor), f'K-{i:04d}')
            painter.setPen(QPen(QColor(255, 200, 0), 2))
            for ref in self.references:
                polygon = ref['proposal']['rgb_polygon_px']
                painter.drawPolygon(QPolygonF([QPointF((x-col)*factor, (y-row)*factor) for x,y in polygon]))
                x, y = np.mean(polygon, axis=0)
                painter.drawText(QPointF((x-col)*factor, (y-row)*factor-12), ref['module_id'].split(':')[-1])
        finally:
            painter.end()
        self._output.setPixmap(pixmap)
