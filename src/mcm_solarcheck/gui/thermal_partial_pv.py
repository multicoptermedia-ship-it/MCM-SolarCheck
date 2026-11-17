"""Existing ROI/detector review with local draft IDs and labelled module detail."""
import numpy as np
import rasterio
from rasterio.windows import Window
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF
from PySide6.QtWidgets import (
    QLabel, QComboBox, QDialog, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QScrollArea, QHBoxLayout,
)

from .orthophoto_pv_review import OrthophotoPVReviewDialog, _rgb_pixels
from .orthophoto_comparison import OrthophotoComparisonWidget, _pixmap_from_rgb
from ..services.thermal_partial_pv import (
    REVIEWS, load_module_review, save_module_review, detect_partial_pv_window,
    region_key, make_region, parse_region, partial_module_detail, manual_module_outline,
)
from ..services.thermal_partial_comparison import verify_partial_comparison
from ..services.orthophoto_pv_modules import OrthophotoPVWindowResult

REVIEW_LABELS = dict(zip(REVIEWS, ('Offen', 'Umriss passt', 'Verwerfen')))


class ModuleCornerImage(QLabel):
    """Four explicit clicks on native RGB pixel centers, without resampling."""
    changed = Signal()

    def __init__(self, pixels, window, previous=None):
        super().__init__()
        self.setObjectName('partial_pv_corner_image')
        self.base = _pixmap_from_rgb(pixels)
        self.window = window
        self.previous = previous or ()
        self.corners = []
        self.setFixedSize(self.base.size())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.redraw()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and len(self.corners) < 4:
            point = event.position().toPoint()
            if self.rect().contains(point):
                self.corners.append((point.x()+self.window[0], point.y()+self.window[1]))
                self.redraw()
                self.changed.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def undo(self):
        if self.corners:
            self.corners.pop()
            self.redraw()
            self.changed.emit()

    def redraw(self):
        pixmap = self.base.copy()
        painter = QPainter(pixmap)
        def points(values):
            return QPolygonF([QPointF(x-self.window[0], y-self.window[1]) for x, y in values])
        painter.setPen(QPen(QColor(255, 200, 0), 2, Qt.PenStyle.DashLine))
        if self.previous:
            painter.drawPolygon(points(self.previous))
        painter.setPen(QPen(QColor(0, 255, 160), 2))
        if self.corners:
            ring = points(self.corners)
            painter.drawPolyline(ring)
            if len(self.corners) == 4:
                painter.drawLine(ring[-1], ring[0])
            for index, point in enumerate(ring, 1):
                painter.drawEllipse(point, 3, 3)
                painter.drawText(point+QPointF(5, -5), str(index))
        painter.end()
        self.setPixmap(pixmap)


class ManualModuleOutlineDialog(QDialog):
    outline_changed = Signal(object, object)

    def __init__(self, comparison, region, module_id=None, parent=None):
        super().__init__(parent)
        self.setObjectName('partial_pv_outline_dialog')
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle('Modulumriss korrigieren' if module_id else 'Modul manuell ergänzen')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.comparison, self.region, self.module_id = comparison, region, module_id
        pair = verify_partial_comparison(comparison)
        result, _ = parse_region(comparison, region)
        with rasterio.open(pair.rgb_path) as raster:
            pixels = _rgb_pixels(raster, pair.rgb_bands, window=Window(*result.rgb_window))
        verify_partial_comparison(comparison)
        old = next((e for e in region['entries'] if e['module_id'] == module_id), None)
        layout = QVBoxLayout(self)
        notice = QLabel(comparison.label + ' · Vier Modulecken der Reihe nach am Rand anklicken. '
            'RGB in Originalauflösung; Scrollleisten verschieben den Ausschnitt. '
            'Gelb: bisheriger Umriss. Grün: neuer Entwurf. Keine Geometrie- oder Celsiusfreigabe.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        if old:
            previous = QLabel(f"{module_id.split(':')[-1]} · Bisher: {REVIEW_LABELS[old['status']]} · {old['note']}\n"
                'Bisheriger Umriss und Beurteilung bleiben lokal in der Historie erhalten.')
            previous.setWordWrap(True)
            layout.addWidget(previous)
        self.image = ModuleCornerImage(pixels, result.rgb_window,
            old['proposal']['rgb_polygon_px'] if old else None)
        scroll = QScrollArea()
        scroll.setWidget(self.image)
        layout.addWidget(scroll, 1)
        self.status = QLabel('0 von 4 Modulecken markiert.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        undo = QPushButton('Letzte Ecke zurück')
        undo.setObjectName('partial_pv_corner_undo')
        undo.clicked.connect(self.image.undo)
        buttons.addWidget(undo)
        self.apply = QPushButton('Umriss als offenen Entwurf übernehmen')
        self.apply.setObjectName('partial_pv_outline_apply')
        self.apply.setEnabled(False)
        self.apply.clicked.connect(self._apply)
        buttons.addWidget(self.apply)
        cancel = QPushButton('Abbrechen')
        cancel.setObjectName('partial_pv_outline_cancel')
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.image.changed.connect(self._changed)
        available = self.screen().availableGeometry()
        self.resize(min(1100, available.width()-40), min(750, available.height()-40))

    def _changed(self):
        self.apply.setEnabled(len(self.image.corners) == 4)
        self.status.setText(f'{len(self.image.corners)} von 4 Modulecken markiert.')

    def _apply(self):
        try:
            region = manual_module_outline(self.comparison, self.region, self.image.corners, module_id=self.module_id)
            self.outline_changed.emit(region, self.module_id)
            self.accept()
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            self.status.setText(f'Nicht übernommen: {error}')


class PartialThermalPVReviewDialog(OrthophotoPVReviewDialog):
    def __init__(self, comparison, parent=None):
        self.comparison = comparison
        self.regions, last = load_module_review(comparison)
        self.current_region = None
        self._detail_dialog = None
        self._editor_dialog = None
        super().__init__(comparison.rgb_path, comparison.thermal_path, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle('PV-Modul-Entwürfe – unvollständige Thermal-Teilvorschau')
        self.setObjectName('partial_pv_review_dialog')
        self.findChild(QLabel, 'orthophoto_pv_help').setText(
            'Einen begrenzten RGB-Bereich mit der Maus markieren und die vorhandenen Modulvorschläge suchen. '
            'Die Umrisse werden in Originalauflösung geprüft und zur unvollständigen Thermal-Teilvorschau zugeordnet.')
        layout = self.layout()
        warning = QLabel(comparison.label + ' · Entwurfs-IDs nur je RGB-Ausschnitt; '
            'keine bestätigten physischen Modul-IDs, Geometrie- oder Celsiusfreigabe.')
        warning.setObjectName('partial_pv_incomplete_notice')
        warning.setWordWrap(True)
        layout.insertWidget(0, warning)
        self.saved_regions = QComboBox()
        self.saved_regions.setObjectName('partial_pv_regions')
        self.saved_regions.currentIndexChanged.connect(self._choose_region)
        layout.insertWidget(1, self.saved_regions)
        self.findChild(QScrollArea, 'orthophoto_pv_selection_scroll').setMaximumHeight(240)
        self.findChild(QScrollArea, 'orthophoto_pv_result_scroll').setMaximumHeight(200)
        self.table = QTableWidget(0, 4)
        self.table.setObjectName('partial_pv_modules')
        self.table.setHorizontalHeaderLabels(('Entwurfs-ID', 'Gültige Thermalpixel %', 'Umrissprüfung', 'Lokale Notiz'))
        self.table.horizontalHeaderItem(1).setToolTip('Anteil nur innerhalb dieses Modulpolygons; keine Anlagenabdeckung.')
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMaximumHeight(180)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.insertWidget(layout.count()-1, self.table)
        detail = QPushButton('Ausgewähltes Modul in RGB / Thermal vergleichen')
        detail.setObjectName('partial_pv_module_detail')
        detail.clicked.connect(self._open_detail)
        layout.insertWidget(layout.count()-1, detail)
        edits = QHBoxLayout()
        self.correct = QPushButton('Ausgewählten Umriss korrigieren')
        self.correct.setObjectName('partial_pv_correct_outline')
        self.correct.clicked.connect(lambda: self._open_outline(correct=True))
        self.add = QPushButton('Modul manuell ergänzen')
        self.add.setObjectName('partial_pv_add_outline')
        self.add.clicked.connect(lambda: self._open_outline(correct=False))
        edits.addWidget(self.correct)
        edits.addWidget(self.add)
        layout.insertLayout(layout.count()-1, edits)
        self.table.itemSelectionChanged.connect(self._edit_buttons)
        self._edit_buttons()
        save = QPushButton('Modul-Entwürfe und Prüfung lokal speichern')
        save.setObjectName('partial_pv_save')
        save.clicked.connect(self._save)
        layout.insertWidget(layout.count()-1, save)
        available = self.screen().availableGeometry()
        self.resize(min(1200, available.width()-40), min(900, available.height()-40))
        self._refresh_regions(last)
        if last:
            self._restore_region(last)

    def _inspect_pair(self, rgb_path, thermal_path):
        return self.comparison._pair

    def _detect(self, window):
        return detect_partial_pv_window(self.comparison, window=window)

    def _run_detection(self):
        super()._run_detection()
        if self.proposal_result is not None:
            self._run.setEnabled(False)  # Keep reviewed IDs attached to this detection set.

    def _collect(self):
        if self.current_region and self.proposal_result is not None:
            for index, entry in enumerate(self.regions[self.current_region]['entries']):
                entry['status'] = self.table.cellWidget(index, 2).currentData()
                entry['note'] = self.table.item(index, 3).text()

    def _select_window(self, window):
        self._collect()
        super()._select_window(window)
        self.current_region = None
        self.table.setRowCount(0)
        self._refresh_regions(None)
        if self._detail_dialog:
            self._detail_dialog.close()
        if self._run.isEnabled():
            key = region_key(window)
            if key in self.regions:
                self._restore_region(key)
        self._edit_buttons()

    def _edit_buttons(self):
        self.correct.setEnabled(self.proposal_result is not None and self.table.currentRow() >= 0)
        self.add.setEnabled(self._window is not None and all(1 <= v <= 2048 for v in self._window[2:]))

    def _open_outline(self, *, correct):
        try:
            self._collect()
            if correct:
                index = self.table.currentRow()
                if not self.current_region or index < 0:
                    return
                region = self.regions[self.current_region]
                module_id = region['entries'][index]['module_id']
            else:
                if not self.add.isEnabled():
                    return
                region = self.regions.get(self.current_region)
                if region is None:
                    region = make_region(self.comparison, OrthophotoPVWindowResult((), self._window, 'manual'))
                module_id = None
            if self._detail_dialog:
                self._detail_dialog.close()
            if self._editor_dialog:
                self._editor_dialog.raise_()
                return
            self._editor_dialog = ManualModuleOutlineDialog(self.comparison, region, module_id, self)
            self._editor_dialog.outline_changed.connect(self._apply_outline)
            self._editor_dialog.finished.connect(self._outline_closed)
            self._editor_dialog.show()
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            self._status.setText('Umrisseditor nicht geöffnet; gültigen RGB-Ausschnitt und gespeicherten Vergleich prüfen.')

    def _outline_closed(self):
        self._editor_dialog = None

    def _apply_outline(self, region, module_id):
        result, region = parse_region(self.comparison, region)
        key = region_key(result.rgb_window)
        self.regions[key] = region
        self._restore_region(key)
        index = (next(i for i, e in enumerate(region['entries']) if e['module_id'] == module_id)
            if module_id else len(region['entries'])-1)
        self.table.selectRow(index)
        self._status.setText('Umriss als offener Entwurf übernommen. Bitte prüfen und Modul-Entwürfe lokal speichern.')

    def _restore_region(self, key):
        result, region = parse_region(self.comparison, self.regions[key])
        self.regions[key] = region
        self._window = result.rgb_window
        self._selection_image.show_native_window(self._window)
        self._render_result(result)
        self._run.setEnabled(False)

    def _choose_region(self, *_):
        key = self.saved_regions.currentData()
        if key and key in self.regions:
            self._collect()
            self._restore_region(key)

    def _refresh_regions(self, selected=None):
        self.saved_regions.blockSignals(True)
        self.saved_regions.clear()
        self.saved_regions.addItem('Gespeicherten Ausschnitt wählen oder neuen Bereich markieren', None)
        for index, (key, region) in enumerate(self.regions.items(), 1):
            self.saved_regions.addItem(f'Ausschnitt {index} · {len(region["entries"])} Entwürfe', key)
        self.saved_regions.setCurrentIndex(max(0, self.saved_regions.findData(selected)))
        self.saved_regions.blockSignals(False)

    def _after_result(self, result):
        key = region_key(result.rgb_window)
        if key not in self.regions:
            self.regions[key] = make_region(self.comparison, result)
        self.current_region = key
        entries = self.regions[key]['entries']
        self.table.setRowCount(len(entries))
        pixmap = self._output.pixmap().copy()
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 200, 0))
        factor = min(1., 1024/max(result.rgb_window[2:]))
        col, row = result.rgb_window[:2]
        for index, (entry, proposal) in enumerate(zip(entries, result.proposals)):
            label_id = 'A' + str(list(self.regions).index(key) + 1) + ':' + entry['module_id'].split(':')[-1]
            for column, text in ((0, label_id),
                    (1, f'{100 * proposal.thermal_valid_coverage:.1f}')):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, entry['module_id'])
                    history = entry.get('history', [])
                    origin = 'Manuell ergänzt' if entry.get('origin') == 'manual' else 'Erkennung'
                    item.setToolTip('Lokaler Entwurf; keine bestätigte physische Modul-ID. '
                        f"Ursprung: {origin}; {len(history)} Korrekturen.\n" +
                        '\n'.join(f"Vorher: {REVIEW_LABELS[h['status']]} · {h['note']}" for h in history))
                self.table.setItem(index, column, item)
            review = QComboBox()
            for status, text in REVIEW_LABELS.items():
                review.addItem(text, status)
            review.setCurrentIndex(REVIEWS.index(entry['status']))
            self.table.setCellWidget(index, 2, review)
            self.table.setItem(index, 3, QTableWidgetItem(entry['note']))
            x, y = np.mean(proposal.rgb_polygon_px, axis=0)
            painter.drawText(QPointF((x-col)*factor, (y-row)*factor), entry['module_id'].split(':')[-1])
        painter.end()
        self._output.setPixmap(pixmap)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        if entries:
            self.table.selectRow(0)
        self._refresh_regions(key)
        self._edit_buttons()
        self._status.setText(f'{len(entries)} lokale Modul-Entwürfe. IDs gelten nur in diesem RGB-Ausschnitt. '
            'Gültige Thermalpixel sind kein Nachweis vollständiger Anlagenabdeckung. '
            'Der vorhandene Detektor liefert konservative Vorschläge nur für abgrenzbare Modulflächen.')

    def _save(self):
        try:
            self._collect()
            save_module_review(self.comparison, self.regions, self.current_region)
            self._status.setText('Modul-Entwürfe und Umrissprüfung lokal gespeichert; keine Fach-/Geometrie-/Temperaturfreigabe.')
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            self._status.setText('Nicht gespeichert: Quellen unverändert lassen; maximal 20 Ausschnitte / 2000 Entwürfe und 1000 Zeichen je Notiz.')

    def _open_detail(self):
        index = self.table.currentRow()
        if self.proposal_result is None or not 0 <= index < len(self.proposal_result.proposals):
            return
        try:
            proposal = self.proposal_result.proposals[index]
            rgb, heat = partial_module_detail(self.comparison, proposal)
            if self._detail_dialog:
                self._detail_dialog.deleteLater()
            dialog = QDialog(self)
            dialog.setWindowTitle('Modul-Entwurf: RGB / Thermal-Sichtvergleich')
            dialog.setObjectName('partial_pv_detail_dialog')
            layout = QVBoxLayout(dialog)
            module_id = self.regions[self.current_region]['entries'][index]['module_id']
            text = QLabel(module_id + f' · gültige Thermalpixel: {proposal.thermal_valid_pixel_count}/'
                          f'{proposal.thermal_polygon_sample_count}; keine Temperaturwerte.')
            text.setWordWrap(True)
            layout.addWidget(text)
            layout.addWidget(OrthophotoComparisonWidget(rgb, heat, incomplete_label=self.comparison.label))
            close = QPushButton('Schließen')
            close.clicked.connect(dialog.close)
            layout.addWidget(close)
            dialog.resize(800, 650)
            self._detail_dialog = dialog
            dialog.show()
        except (ValueError, OSError, RuntimeError):
            self._status.setText('Modulausschnitt nicht geöffnet; Raster unverändert lassen und Vergleich erneut laden.')
