"""Read-only side-by-side evidence in the existing native ROI result renderer."""
import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea
from .orthophoto_pv_review import OrthophotoPVReviewDialog
from .thermal_partial_pv import _resizable_dialog
from ..services.thermal_partial_model_comparison import read_model_comparison, shareable_counts


class ModelComparisonDialog(OrthophotoPVReviewDialog):
    def __init__(self, comparison, parent=None):
        self.comparison = comparison
        record, result, self.references = read_model_comparison(comparison)
        self._record = record
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
        diagnostic = record.get('diagnostics')
        if diagnostic:
            masks, filtering = diagnostic['inference']['masks'], diagnostic['filtering']
            text = (f"Modell liefert: {masks['returned_instances']} Instanzen · "
                f"nach Maskenprüfung: {masks['accepted_outlines']} · "
                f"nach Geometrie/Dubletten: {filtering['after_geometry_and_duplicates']} · "
                f"nach RGB-Datenprüfung: {filtering['final_outlines']}. "
                'Diese Zähler erklären den Ablauf, keine vollständige Modulanzahl.')
        else:
            text = ('Dieser gespeicherte Bericht enthält noch keine Filterkennzahlen. '
                'Ein neuer begrenzter KI-Vergleich im selben Ausschnitt erfasst sie; keine Neuinstallation nötig.')
        label = QLabel(text)
        label.setObjectName('partial_pv_diagnostics')
        label.setWordWrap(True)
        self.layout().insertWidget(1, label)
        self.copy_counts = QPushButton('KI-Kennzahlen kopieren (ohne Bilder und Pfade)')
        self.copy_counts.setObjectName('partial_pv_copy_counts')
        self.copy_counts.clicked.connect(self._copy_counts)
        self.layout().insertWidget(2, self.copy_counts)
        counts = record['counts']
        self.findChild(QLabel, 'orthophoto_pv_help').setText(
            f"KI-Kandidaten: {counts['candidate_outlines']} · "
            f"Gespeicherte passende Umrisse: {counts['reviewed_outlines']} · "
            f"davon wiedergefunden: {counts['matched_reviewed_outlines']} · "
            f"nicht wiedergefunden: {counts['unmatched_reviewed_outlines']} · "
            f"zusätzliche ungeprüfte Kandidaten: {counts['additional_unreviewed_candidates']}. "
            'Die Referenz ist nicht vollständig: keine allgemeine Trefferquote oder Fehlerfreiheit ableiten.')
        self._window = result.rgb_window
        scroll = self.findChild(QScrollArea, 'orthophoto_pv_result_scroll')
        scroll.setMaximumHeight(16777215)
        self._render_result(result)
        # ONNX reports embed ModelManifest; existing PV-Hawk reports store
        # provider/version directly. Reopen either without rewriting evidence.
        metadata = record['model'].get('model', record['model'])
        configuration = record['model'].get('preprocessing_config')
        configuration_text = (f" · RGB-Eingabe: {configuration['image_min_dim']}/{configuration['image_max_dim']} Pixel"
            if configuration else '')
        empty = ('Keine KI-Umrisse im Ergebnis. Der Vergleich ist abgeschlossen; '
            'gelbe Umrisse zeigen die gespeicherte Teilreferenz. ' if not result.proposals else '')
        self._status.setText(empty + 'Vergleich separat lokal gespeichert. Bestehende Entwürfe/Beurteilungen bleiben erhalten. '
            f"Modell: {metadata['provider']} / {metadata['model_version']}" + configuration_text)
        available = self.screen().availableGeometry()
        self.resize(min(1200, available.width()-40), min(850, available.height()-40))

    def _inspect_pair(self, rgb_path, thermal_path):
        return self.comparison._pair

    def _copy_counts(self):
        import json
        QApplication.clipboard().setText(json.dumps(shareable_counts(self._record),ensure_ascii=False,indent=2))

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
