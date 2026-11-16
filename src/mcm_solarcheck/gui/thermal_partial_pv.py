"""Existing ROI/detector review with local draft IDs and labelled module detail."""
import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (
    QLabel, QComboBox, QDialog, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QScrollArea,
)

from .orthophoto_pv_review import OrthophotoPVReviewDialog
from .orthophoto_comparison import OrthophotoComparisonWidget
from ..services.thermal_partial_pv import (
    REVIEWS, load_module_review, save_module_review, detect_partial_pv_window,
    region_key, make_region, parse_region, partial_module_detail,
)


class PartialThermalPVReviewDialog(OrthophotoPVReviewDialog):
    def __init__(self, comparison, parent=None):
        self.comparison = comparison
        self.regions, last = load_module_review(comparison)
        self.current_region = None
        self._detail_dialog = None
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
        save = QPushButton('Modul-Entwürfe und Prüfung lokal speichern')
        save.setObjectName('partial_pv_save')
        save.clicked.connect(self._save)
        layout.insertWidget(layout.count()-1, save)
        self.resize(1200, 940)
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
                    item.setToolTip('Lokaler Entwurf in diesem RGB-Ausschnitt; keine bestätigte physische Modul-ID.')
                self.table.setItem(index, column, item)
            review = QComboBox()
            for text, status in zip(('Offen', 'Umriss passt', 'Verwerfen'), REVIEWS):
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
