"""Prepare complete local targets with explicit exclusions, without training."""
import json
import cv2
import numpy as np
import rasterio
from rasterio.windows import Window
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton,
    QFormLayout, QHBoxLayout, QComboBox, QScrollArea, QSplitter,
)

from ..services.thermal_partial_training import (
    read_learning_preparation, save_learning_preparation, revoke_learning_preparation, prepared_split, SPLIT_LABELS,
    learning_selection, validate_ignore_areas, preview_learning_preparation, learning_target, learning_counts,
)
from ..services.thermal_partial_comparison import verify_partial_comparison
from ..services.thermal_partial_pv import load_module_review
from .orthophoto_pv_review import _rgb_pixels
from .orthophoto_comparison import _pixmap_from_rgb


def _overlay(rgb, target):
    pixels = rgb.copy()
    for value, color in ((1, (0, 255, 80)), (255, (255, 0, 255))):
        selected = target == value
        pixels[selected] = (pixels[selected] * .4 + np.asarray(color) * .6).astype(np.uint8)
    return pixels


class LearningMaskDialog(QDialog):
    def __init__(self, comparison, entry, parent=None):
        super().__init__(parent)
        self.setObjectName('pv_learning_mask_preview')
        self.setWindowTitle('Lernmaske prüfen – noch kein Training')
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setSizeGripEnabled(True)
        pair = verify_partial_comparison(comparison)
        counts = learning_counts(entry)
        window = entry['manifest']['samples'][0]['source_window']
        with rasterio.open(pair.rgb_path) as rgb:
            pixels = _rgb_pixels(rgb, pair.rgb_bands, window=Window(*window))
        verify_partial_comparison(comparison)
        layout = QVBoxLayout(self)
        for text in (comparison.label,
                'Grün: zum Lernen ausgewählte Modulflächen. Magenta: vom Lernen ausgenommen, einschließlich Sicherheitsrand. '
                'Übrige Pixel: Hintergrund. Nicht sichtbare Ecken werden nicht ergänzt oder erraten.',
                f"{counts['module_outlines']} ausgewählte Modulflächen · {counts['ignored_outlines']} ausgenommene Vorschläge · "
                f"{counts['ignored_areas']} markierte Bereiche · Datenteil: {SPLIT_LABELS[counts['split']]}",
                'Lernbereich begrenzt: Alles außerhalb ist Magenta und wird ignoriert.' if counts['learning_area_limited'] else
                'Gesamter Ausschnitt: Weitere sichtbare Module müssen beschriftet oder ausgenommen sein. Bei Teilbeschriftung zuerst Lernbereich begrenzen.',
                'Links: ursprünglicher RGB-Ausschnitt. Rechts: 480 × 270 Pixel des bisherigen Kandidatenprofils. '
                'Das originale CVUT-Eingabeprofil bleibt ungeprüft. Die Vorschau startet weder Modell noch Training; '
                'Änderungen anschließend in der Lernvorbereitung speichern.'):
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)
        panes = QSplitter(Qt.Orientation.Horizontal)
        for name, image, target in (
                ('native', pixels, learning_target(entry)),
                ('candidate', cv2.resize(pixels, (480, 270), interpolation=cv2.INTER_CUBIC), learning_target(entry, (480, 270)))):
            label = QLabel()
            label.setObjectName('pv_learning_mask_' + name)
            pixmap = _pixmap_from_rgb(_overlay(image, target))
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            try:
                for index, area in enumerate(entry['manifest']['user_ignore_polygons_px'], 1):
                    x, y = np.mean(area, axis=0)
                    painter.drawText(round(x*image.shape[1]/window[2]), round(y*image.shape[0]/window[3]), f'U{index}')
            finally:
                painter.end()
            label.setPixmap(pixmap)
            scroll = QScrollArea()
            scroll.setWidget(label)
            panes.addWidget(scroll)
        layout.addWidget(panes, 1)
        self.counts = counts
        copy = QPushButton('Lernmasken-Kennzahlen kopieren (ohne Bilder und Pfade)')
        copy.setObjectName('pv_learning_copy_counts')
        copy.clicked.connect(lambda: QApplication.clipboard().setText(json.dumps(self.counts, indent=2, ensure_ascii=False)))
        layout.addWidget(copy)
        close = QPushButton('Schließen')
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        available = self.screen().availableGeometry()
        self.resize(min(1200, available.width()-40), min(750, available.height()-40))


class LearningPreparationDialog(QDialog):
    def __init__(self, comparison, key, parent=None):
        super().__init__(parent)
        # Also valid if source/legacy validation aborts construction. Qt can
        # still close the parent-owned, partially constructed dialog later.
        self._area_editor = self._mask_dialog = None
        self.setObjectName('pv_learning_preparation')
        self.setWindowTitle('PV-Lernmuster lokal vorbereiten')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setSizeGripEnabled(True)
        self.comparison, self.key = comparison, key
        state = read_learning_preparation(comparison, key)
        self.ignore_areas = list(state['ignore_areas'])
        self.learning_area = state['learning_area']
        self.review_sha256 = state['review_sha256']
        self.problem = state['problem']
        layout = QVBoxLayout(self)
        for text in (comparison.label,
                'Gespeicherte Korrekturen und Ergänzungen werden verwendet. Gelöschte/verworfene Umrisse sind keine Hintergrundlabels.',
                'Nur wenige kleine Ausschnitte vorbereiten. Jedes sichtbare Modul entweder korrekt als ganze Fläche beschriften '
                'oder ausdrücklich vom Lernen ausnehmen. Keine nicht sichtbaren Ecken erraten. '
                'Die Vollständigkeit wird von dir geprüft, nicht automatisch festgestellt.',
                'Gleiche Anlage und zusammengehörige Befliegungen immer mit derselben Anlagengruppe bezeichnen, auch in anderen Orthofotos. '
                'Die Gruppe erhält fest einen Datenteil; überlappende Ausschnitte werden nicht auf Training und Prüfung verteilt. '
                'Ein Orthofoto allein liefert kein unabhängiges Prüfset.'):
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)
        form = QFormLayout()
        self.group = QLineEdit(state['group_id'])
        self.group.setObjectName('pv_learning_group')
        self.group.setMaxLength(100)
        self.group.setReadOnly(bool(state['group_id']))
        form.addRow('Anlagengruppe (lokale Bezeichnung):', self.group)
        self.reviewer = QLineEdit(state['entry']['reviewer'] if state['entry'] else '')
        self.reviewer.setObjectName('pv_learning_reviewer')
        self.reviewer.setMaxLength(100)
        form.addRow('Geprüft von:', self.reviewer)
        layout.addLayout(form)
        scope_buttons = QHBoxLayout()
        limit = QPushButton('Lernbereich begrenzen')
        limit.setObjectName('pv_learning_area_set')
        limit.clicked.connect(lambda: self._add_area(True))
        scope_buttons.addWidget(limit)
        self.unlimit = QPushButton('Begrenzung entfernen')
        self.unlimit.setObjectName('pv_learning_area_clear')
        self.unlimit.clicked.connect(self._clear_limit)
        scope_buttons.addWidget(self.unlimit)
        layout.addLayout(scope_buttons)
        area_buttons = QHBoxLayout()
        add = QPushButton('Unklaren Bereich markieren')
        add.setObjectName('pv_learning_ignore_add')
        add.clicked.connect(self._add_area)
        area_buttons.addWidget(add)
        self.areas = QComboBox()
        self.areas.setObjectName('pv_learning_ignore_areas')
        area_buttons.addWidget(self.areas, 1)
        self.remove = QPushButton('Ausnahme entfernen')
        self.remove.setObjectName('pv_learning_ignore_remove')
        self.remove.clicked.connect(self._remove_area)
        area_buttons.addWidget(self.remove)
        layout.addLayout(area_buttons)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.complete = QCheckBox('Alle sichtbaren Module korrekt umrandet oder ausdrücklich vom Lernen ausgenommen')
        self.complete.setObjectName('pv_learning_complete')
        layout.addWidget(self.complete)
        self.status = QLabel()
        self.status.setObjectName('pv_learning_status')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        if state['needs_mask_review']:
            self.status.setText('Bisherige Vorbereitung geladen. Bei nicht sichtbaren Ecken unklare Bereiche markieren; Lernmaske prüfen und erneut bestätigen.')
        elif state['current']:
            self.complete.setChecked(True)
            self._saved(state['entry'])
        elif state['entry']:
            self.status.setText('Vorbereitung veraltet: Modulprüfung wurde geändert. Vollständigkeit erneut prüfen und bestätigen.')
        elif self.problem:
            self.status.setText(self.problem)
        else:
            self.status.setText('Noch keine Vollständigkeitsbestätigung gespeichert.')
        notice = QLabel('Es werden nur lokale Beschriftungsdaten vorbereitet. Kein Bildexport, kein Training und keine Modelländerung. '
            'Datennutzungsrechte und ein geeigneter Trainer bleiben vor einer tatsächlichen Trainingsnutzung zu prüfen. '
            'Keine Bestätigung von Modul-IDs, Abdeckung, Geometrie oder Celsius.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.save = QPushButton('Lernmuster-Vorbereitung lokal speichern')
        self.save.setObjectName('pv_learning_save')
        self.save.clicked.connect(self._save)
        layout.addWidget(self.save)
        self.preview = QPushButton('Lernmaske prüfen')
        self.preview.setObjectName('pv_learning_preview')
        self.preview.clicked.connect(self._preview)
        layout.addWidget(self.preview)
        self.revoke = QPushButton('Vollständigkeitsbestätigung zurücknehmen')
        self.revoke.setObjectName('pv_learning_revoke')
        self.revoke.setEnabled(state['entry'] is not None)
        self.revoke.clicked.connect(self._revoke)
        layout.addWidget(self.revoke)
        close = QPushButton('Schließen')
        close.setObjectName('pv_learning_close')
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        self.complete.toggled.connect(self._controls)
        self.group.textChanged.connect(self._controls)
        self.reviewer.textChanged.connect(self._controls)
        self.finished.connect(self._close_children)
        self._refresh_areas()
        self._controls()
        self.resize(1000, 640)

    def _controls(self):
        self.save.setEnabled(not self.problem and self.complete.isChecked()
            and bool(self.group.text().strip()) and bool(self.reviewer.text().strip()))
        self.preview.setEnabled(not self.problem and bool(self.group.text().strip()) and bool(self.reviewer.text().strip()))
        reason = self.problem
        if not reason and (not self.group.text().strip() or not self.reviewer.text().strip()):
            reason = 'Anlagengruppe und Geprüft von ausfüllen, dann Lernmaske prüfen.'
        self.preview.setToolTip(reason or 'Lernmaske vor der Vollständigkeitsbestätigung prüfen.')
        if reason:
            self.status.setText(reason)

    def _saved(self, entry):
        self.status.setText(f"Vorbereitung lokal gespeichert · {len(entry['manifest']['labels'])} Modulflächen · "
            f"Datenteil: {SPLIT_LABELS[prepared_split(entry)]}. Noch kein vollständiger Trainingsdatensatz oder trainiertes Modell.")

    def _save(self):
        try:
            entry = save_learning_preparation(self.comparison, self.key, reviewer=self.reviewer.text(),
                group_id=self.group.text(), complete_annotation=self.complete.isChecked(),
                expected_review_sha256=self.review_sha256, ignore_areas=self.ignore_areas, learning_area=self.learning_area)
            self.group.setText(entry['manifest']['group_id'])
            self.group.setReadOnly(True)
            self._saved(entry)
            self.revoke.setEnabled(True)
        except ValueError as error:
            self.status.setText(str(error))
        except (TypeError, KeyError, OSError, RuntimeError):
            self.status.setText('Vorbereitung nicht gespeichert. Gespeicherte Modulprüfung, ganze gültige Umrisse und Quellen prüfen; '
                'bei Änderungen dieses Fenster erneut öffnen. Bisherige Vorbereitung bleibt erhalten.')

    def _revoke(self):
        try:
            revoke_learning_preparation(self.comparison, self.key, expected_review_sha256=self.review_sha256)
            self.complete.setChecked(False)
            self.revoke.setEnabled(False)
            self.status.setText('Vollständigkeitsbestätigung zurückgenommen. Modul-Entwürfe bleiben erhalten; kein Training gestartet.')
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            self.status.setText('Bestätigung nicht geändert; Lernvorbereitung erneut öffnen und Quellen prüfen.')

    def _refresh_areas(self):
        self.areas.clear()
        for index in range(len(self.ignore_areas)):
            self.areas.addItem(f'Unklarer Bereich {index+1}')
        self.remove.setEnabled(bool(self.ignore_areas))
        self.unlimit.setEnabled(self.learning_area is not None)
        state = learning_selection(self.comparison, self.key, self.ignore_areas, self.learning_area)
        self.problem = state['problem']
        self.summary.setText(f"{state['module_count']} ausgewählte Modulflächen · {state['ignored_count']} Vorschläge vom Lernen ausgenommen. " +
            ('Lernbereich begrenzt: Außerhalb wird alles ignoriert. Innerhalb alle sichtbaren Module prüfen.' if self.learning_area is not None else
            'Gesamter Ausschnitt: Bei Teilbeschriftung Lernbereich begrenzen; unbeschriftete Module sind sonst Hintergrund.'))

    def _add_area(self, limit=False):
        try:
            from .thermal_partial_pv import ManualModuleOutlineDialog
            regions, _ = load_module_review(self.comparison)
            if self._area_editor:
                self._area_editor.raise_()
                return
            self._area_editor = ManualModuleOutlineDialog(self.comparison, regions[self.key], parent=self,
                learning_ignore=not limit, learning_scope=limit)
            self._area_editor.area_selected.connect(self._apply_limit if limit else self._apply_area)
            self._area_editor.finished.connect(self._area_closed)
            self._area_editor.show()
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            self.status.setText('Bereich nicht geöffnet; gespeicherte Modulprüfung und Quellen prüfen.')

    def _area_closed(self):
        self._area_editor = None

    def _apply_limit(self, polygon):
        try:
            regions, _ = load_module_review(self.comparison)
            window = regions[self.key]['window']
            col, row = window[:2]
            self.learning_area = validate_ignore_areas(window, [tuple((x-col, y-row) for x, y in polygon)])[0]
            self._areas_changed()
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            self.status.setText(str(error))

    def _clear_limit(self):
        self.learning_area = None
        self._areas_changed()

    def _apply_area(self, polygon):
        try:
            regions, _ = load_module_review(self.comparison)
            window = regions[self.key]['window']
            col, row = window[:2]
            self.ignore_areas = list(validate_ignore_areas(window,
                [*self.ignore_areas, tuple((x-col, y-row) for x, y in polygon)]))
            self._areas_changed()
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            self.status.setText(str(error))

    def _remove_area(self):
        index = self.areas.currentIndex()
        if 0 <= index < len(self.ignore_areas):
            del self.ignore_areas[index]
            self._areas_changed()

    def _areas_changed(self):
        self.complete.setChecked(False)
        self._refresh_areas()
        self.status.setText(self.problem or 'Ausnahmen geändert, noch nicht gespeichert. Lernmaske prüfen und Vollständigkeit erneut bestätigen.')
        self._controls()

    def _preview(self):
        try:
            entry = preview_learning_preparation(self.comparison, self.key, reviewer=self.reviewer.text(),
                group_id=self.group.text(), ignore_areas=self.ignore_areas, learning_area=self.learning_area,
                expected_review_sha256=self.review_sha256)
            if self._mask_dialog:
                self._mask_dialog.close()
                self._mask_dialog.deleteLater()
            self._mask_dialog = LearningMaskDialog(self.comparison, entry, self)
            self._mask_dialog.show()
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            self.status.setText(str(error))

    def closeEvent(self, event):
        self._close_children()
        super().closeEvent(event)

    def _close_children(self, *args):
        for child in (self._area_editor, self._mask_dialog):
            if child:
                child.close()
