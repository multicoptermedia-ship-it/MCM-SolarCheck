"""Existing overlay widget with a local-only note for an incomplete preview."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QPlainTextEdit,
)

from .orthophoto_comparison import OrthophotoComparisonWidget
from ..services.thermal_partial_comparison import VERDICTS, save_partial_comparison


class PartialThermalComparisonWindow(QWidget):
    def __init__(self, comparison):
        super().__init__()
        self.comparison = comparison
        self.setWindowTitle('SolarCheck – RGB / unvollständige Thermal-Teilvorschau')
        self.resize(1100, 850)
        layout = QVBoxLayout(self)
        description = QLabel('Übersicht nach den gespeicherten GeoTIFF-Koordinaten. '
            'Keine automatische Lagekorrektur. Zoom vergrößert die Vorschau; Details in den Original-TIFFs prüfen.')
        description.setWordWrap(True)
        layout.addWidget(description)
        self.viewer = OrthophotoComparisonWidget(comparison.rgb, comparison.thermal,
                                                 incomplete_label=comparison.label)
        self.viewer.restore_view_state(opacity=comparison.view['opacity'], zoom=comparison.view['zoom'])
        layout.addWidget(self.viewer, 1)
        self.verdict = QComboBox()
        self.verdict.setObjectName('partial_comparison_verdict')
        for text, key in zip(('Noch nicht beurteilt', 'In dieser Ansicht passend', 'Versatz sichtbar'), VERDICTS):
            self.verdict.addItem(text, key)
        self.verdict.setCurrentIndex(VERDICTS.index(comparison.view['verdict']))
        layout.addWidget(self.verdict)
        self.note = QPlainTextEdit(comparison.view['note'])
        self.note.setObjectName('partial_comparison_note')
        self.note.setPlaceholderText('Lokale Notiz: Modulränder, Dachkanten, Aufbauten, Nähte und Randbereiche vergleichen.')
        self.note.setMaximumHeight(80)
        layout.addWidget(self.note)
        self.status = QLabel('Beurteilung bleibt lokal; sie bestätigt keine geometrische Genauigkeit oder Temperaturwerte.')
        self.status.setWordWrap(True)
        self.status.setObjectName('partial_comparison_status')
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self._pv_dialog = None
        self.pv = QPushButton('PV-Modulgrenzen und Entwurfs-IDs prüfen')
        self.pv.setObjectName('partial_comparison_pv_review')
        self.pv.clicked.connect(self._open_pv)
        row.addWidget(self.pv)
        save = QPushButton('Sichtvergleich lokal speichern')
        save.setObjectName('partial_comparison_save')
        save.clicked.connect(self.save)
        row.addWidget(save)
        close = QPushButton('Schließen ohne weiteres Speichern')
        close.clicked.connect(self.close)
        row.addWidget(close)
        layout.addLayout(row)
        self.verdict.currentIndexChanged.connect(self._update_pv)
        self._update_pv()

    def _update_pv(self, *_):
        self.pv.setEnabled(self.verdict.currentData() == 'looks_aligned'
                          and self.comparison.view['verdict'] == 'looks_aligned')

    def _open_pv(self):
        try:
            from .thermal_partial_pv import PartialThermalPVReviewDialog
            if self._pv_dialog:
                if self._pv_dialog.isVisible():
                    self._pv_dialog.raise_()
                    self._pv_dialog.activateWindow()
                    return
                self._pv_dialog.deleteLater()
            self._pv_dialog = PartialThermalPVReviewDialog(self.comparison, self)
            self._pv_dialog.show()
        except (ValueError, TypeError, OSError, RuntimeError, KeyError):
            self.status.setText('Modulprüfung nicht geöffnet: passenden Sichtvergleich lokal speichern und Raster unverändert lassen.')

    def save(self):
        try:
            save_partial_comparison(self.comparison, **self.viewer.view_state(),
                verdict=self.verdict.currentData(), note=self.note.toPlainText())
            self.status.setText('Sichtvergleich lokal gespeichert. Beim nächsten Öffnen wird er wiederhergestellt.')
            self._update_pv()
        except (ValueError, OSError):
            self.status.setText('Speichern fehlgeschlagen: Dateien unverändert lassen; Notiz auf maximal 2000 Zeichen begrenzen.')
