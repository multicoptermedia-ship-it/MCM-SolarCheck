"""Existing ROI/detector review with local draft IDs and labelled module detail."""
import numpy as np
import sys
from pathlib import Path
from uuid import uuid4
import rasterio
from rasterio.windows import Window
from PySide6.QtCore import QPointF, QRectF, QTimer, QProcess, Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF
from PySide6.QtWidgets import (
    QLabel, QComboBox, QDialog, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QScrollArea, QHBoxLayout, QSplitter, QWidget, QFileDialog,
)

from .orthophoto_pv_review import OrthophotoPVReviewDialog, _rgb_pixels
from .orthophoto_comparison import OrthophotoComparisonWidget, _pixmap_from_rgb
from ..services.thermal_partial_pv import (
    REVIEWS, load_module_review, save_module_review, detect_partial_pv_window,
    region_key, make_region, parse_region, partial_module_detail, manual_module_outline,
    active_entries, set_module_deleted,
)
from ..services.thermal_partial_comparison import verify_partial_comparison
from ..services.orthophoto_pv_modules import OrthophotoPVWindowResult

REVIEW_LABELS = dict(zip(REVIEWS, ('Offen', 'Umriss passt', 'Verwerfen')))


def _resizable_dialog(dialog):
    # QDialog omits the maximize button by default on Windows.
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
    dialog.setSizeGripEnabled(True)


class ModuleCornerImage(QLabel):
    """Zoom display only; four clicks always address native RGB pixel centers."""
    changed = Signal()
    zoom_requested = Signal(float)
    pan_requested = Signal(float, float)

    def __init__(self, pixels, window, previous=None, module_label=''):
        super().__init__()
        self.setObjectName('partial_pv_corner_image')
        self.base = _pixmap_from_rgb(pixels)
        self.native_window = window
        self.previous = previous or ()
        self.module_label = module_label
        self.corners = []
        self.zoom = 1.
        self._pan_origin = None
        self.setFixedSize(self.base.size())
        self.setCursor(Qt.CursorShape.CrossCursor)

    def display_point(self, native):
        # Pixel centers under Qt's image scaling, with separate rounded axes.
        x, y = native
        return QPointF((x-self.native_window[0]+.5)*self.width()/self.base.width()-.5,
            (y-self.native_window[1]+.5)*self.height()/self.base.height()-.5)

    def native_point(self, point):
        return (max(0, min(self.base.width()-1, round((point.x()+.5)*self.base.width()/self.width()-.5)))
                + self.native_window[0],
            max(0, min(self.base.height()-1, round((point.y()+.5)*self.base.height()/self.height()-.5)))
                + self.native_window[1])

    def set_zoom(self, zoom):
        self.zoom = max(.25, min(8., float(zoom)))
        self.setFixedSize(max(1, round(self.base.width()*self.zoom)),
            max(1, round(self.base.height()*self.zoom)))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = event.globalPosition()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and len(self.corners) < 4:
            if self.rect().contains(event.position().toPoint()):
                self.corners.append(self.native_point(event.position()))
                self.update()
                self.changed.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_origin is not None:
            delta = event.globalPosition()-self._pan_origin
            self._pan_origin = event.globalPosition()
            self.pan_requested.emit(delta.x(), delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = None
            self.setCursor(Qt.CursorShape.CrossCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.angleDelta().y():
            self.zoom_requested.emit(1.25 if event.angleDelta().y() > 0 else .8)
            event.accept()
        else:
            super().wheelEvent(event)

    def undo(self):
        if self.corners:
            self.corners.pop()
            self.update()
            self.changed.emit()

    def paintEvent(self, event):
        # Paint only the exposed viewport. Never allocate a zoom-sized raster
        # (a 2048² ROI at 800% would otherwise require hundreds of megabytes).
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.zoom < 1)
            painter.drawPixmap(QRectF(self.rect()), self.base, QRectF(self.base.rect()))
            def points(values):
                return QPolygonF([self.display_point(point) for point in values])
            painter.setPen(QPen(QColor(255, 200, 0), 3, Qt.PenStyle.DashLine))
            if self.previous:
                painter.drawPolygon(points(self.previous))
                label = self.display_point(tuple(np.mean(self.previous, axis=0)))
                painter.drawText(label+QPointF(6, -6), self.module_label)
            painter.setPen(QPen(QColor(0, 255, 160), 2))
            if self.corners:
                ring = points(self.corners)
                painter.drawPolyline(ring)
                if len(self.corners) == 4:
                    painter.drawLine(ring[-1], ring[0])
                for index, point in enumerate(ring, 1):
                    painter.drawEllipse(point, 3, 3)
                    painter.drawText(point+QPointF(5, -5), str(index))
        finally:
            painter.end()


class ManualModuleOutlineDialog(QDialog):
    outline_changed = Signal(object, object)

    def __init__(self, comparison, region, module_id=None, parent=None):
        super().__init__(parent)
        self.setObjectName('partial_pv_outline_dialog')
        _resizable_dialog(self)
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
            'Zoom: +/− oder Strg+Mausrad; Verschieben: mittlere Maustaste oder Scrollleisten. '
            'Gelb: bisheriger Umriss. Grün: neuer Entwurf. Keine Geometrie- oder Celsiusfreigabe.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        if old:
            previous = QLabel(f"{module_id.split(':')[-1]} · Bisher: {REVIEW_LABELS[old['status']]} · {old['note']}\n"
                'Bisheriger Umriss und Beurteilung bleiben lokal in der Historie erhalten.')
            previous.setWordWrap(True)
            layout.addWidget(previous)
        self.image = ModuleCornerImage(pixels, result.rgb_window,
            old['proposal']['rgb_polygon_px'] if old else None, module_id.split(':')[-1] if module_id else '')
        toolbar = QHBoxLayout()
        for title, name, action in (
                ('−', 'zoom_out', lambda: self._zoom_relative(.8)),
                ('+', 'zoom_in', lambda: self._zoom_relative(1.25)),
                ('100 %', 'zoom_native', lambda: self._set_zoom(1.)),
                ('Ausschnitt einpassen', 'zoom_fit', self._fit_region),
                ('Ausgewähltes Modul zeigen', 'zoom_selected', self._show_selected)):
            button = QPushButton(title)
            button.setObjectName('partial_pv_' + name)
            button.clicked.connect(action)
            button.setEnabled(name != 'zoom_selected' or bool(old))
            toolbar.addWidget(button)
        self.zoom_label = QLabel('100 %')
        self.zoom_label.setObjectName('partial_pv_zoom_value')
        toolbar.addWidget(self.zoom_label)
        layout.addLayout(toolbar)
        self.scroll = QScrollArea()
        self.scroll.setObjectName('partial_pv_editor_scroll')
        self.scroll.setWidget(self.image)
        layout.addWidget(self.scroll, 1)
        self.image.zoom_requested.connect(self._zoom_relative)
        self.image.pan_requested.connect(self._pan)
        self._initial_focus_done = False
        self._initial_focus = QTimer(self)
        self._initial_focus.setSingleShot(True)
        self._initial_focus.timeout.connect(self._show_selected if old else self._fit_region)
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

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initial_focus_done:
            self._initial_focus_done = True
            self._initial_focus.start(0)

    def _pan(self, dx, dy):
        self.scroll.horizontalScrollBar().setValue(self.scroll.horizontalScrollBar().value()-round(dx))
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().value()-round(dy))

    def _zoom_relative(self, factor):
        self._set_zoom(self.image.zoom*factor)

    def _set_zoom(self, zoom, center=None):
        if center is None:
            center = self.image.native_point(QPointF(
                self.scroll.horizontalScrollBar().value()+self.scroll.viewport().width()/2,
                self.scroll.verticalScrollBar().value()+self.scroll.viewport().height()/2))
        self.image.set_zoom(zoom)
        self.zoom_label.setText(f'{100*self.image.zoom:.0f} %')
        # Update the scroll ranges before re-centering the enlarged widget.
        self.scroll.horizontalScrollBar().setRange(0, max(0, self.image.width()-self.scroll.viewport().width()))
        self.scroll.verticalScrollBar().setRange(0, max(0, self.image.height()-self.scroll.viewport().height()))
        position = self.image.display_point(center)
        self.scroll.horizontalScrollBar().setValue(round(position.x()-self.scroll.viewport().width()/2))
        self.scroll.verticalScrollBar().setValue(round(position.y()-self.scroll.viewport().height()/2))

    def _fit_region(self):
        col, row, width, height = self.image.native_window
        self._set_zoom(min(self.scroll.viewport().width()/width, self.scroll.viewport().height()/height),
            (col+(width-1)/2, row+(height-1)/2))

    def _show_selected(self):
        if not self.image.previous:
            return
        xy = np.asarray(self.image.previous)
        left, top = xy.min(axis=0)
        right, bottom = xy.max(axis=0)
        # Include neighboring module edges even when the old draft is partial.
        margin = max(32., max(right-left, bottom-top)*.75)
        zoom = min(self.scroll.viewport().width()/(right-left+2*margin),
            self.scroll.viewport().height()/(bottom-top+2*margin))
        self._set_zoom(zoom, ((left+right)/2, (top+bottom)/2))

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
        self._model_process = None
        self._model_dialog = None
        self._model_pending = None
        self._model_cancelled = False
        super().__init__(comparison.rgb_path, comparison.thermal_path, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle('PV-Modul-Entwürfe – unvollständige Thermal-Teilvorschau')
        self.setObjectName('partial_pv_review_dialog')
        _resizable_dialog(self)
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
        self.table = QTableWidget(0, 4)
        self.table.setObjectName('partial_pv_modules')
        self.table.setHorizontalHeaderLabels(('Entwurfs-ID', 'Gültige Thermalpixel %', 'Umrissprüfung', 'Lokale Notiz'))
        self.table.horizontalHeaderItem(1).setToolTip('Anteil nur innerhalb dieses Modulpolygons; keine Anlagenabdeckung.')
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
        removal = QHBoxLayout()
        self.delete = QPushButton('Ausgewählten Umriss löschen')
        self.delete.setObjectName('partial_pv_delete_outline')
        self.delete.clicked.connect(self._delete_outline)
        removal.addWidget(self.delete)
        self.deleted = QComboBox()
        self.deleted.setObjectName('partial_pv_deleted_outlines')
        self.deleted.addItem('Gelöschte Umrisse (0)', None)
        removal.addWidget(self.deleted, 1)
        self.restore = QPushButton('Wiederherstellen')
        self.restore.setObjectName('partial_pv_restore_outline')
        self.restore.setEnabled(False)
        self.restore.clicked.connect(self._restore_outline)
        self.deleted.currentIndexChanged.connect(self._edit_buttons)
        removal.addWidget(self.restore)
        layout.insertLayout(layout.count()-1, removal)
        model_buttons = QHBoxLayout()
        self.model_start = QPushButton('KI-Modellvergleich starten (lokal)')
        self.model_start.setObjectName('partial_pv_model_start')
        self.model_start.clicked.connect(self._start_model_comparison)
        model_buttons.addWidget(self.model_start)
        self.model_open = QPushButton('Gespeicherten KI-Vergleich öffnen')
        self.model_open.setObjectName('partial_pv_model_open')
        self.model_open.clicked.connect(self._open_model_comparison)
        model_buttons.addWidget(self.model_open)
        layout.insertLayout(layout.count()-1, model_buttons)
        self._model_timer = QTimer(self)
        self._model_timer.setSingleShot(True)
        self._model_timer.timeout.connect(self._cancel_model_comparison)
        self.table.itemSelectionChanged.connect(self._edit_buttons)
        self.table.itemSelectionChanged.connect(self._highlight_selected)
        self._labelled_result = None
        # The images grow with the window; dividers allocate working space.
        self.panes = QSplitter(Qt.Orientation.Vertical)
        self.panes.setObjectName('partial_pv_panes')
        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        for name in ('orthophoto_pv_selection_scroll', 'orthophoto_pv_result_scroll'):
            scroll = self.findChild(QScrollArea, name)
            scroll.setMaximumHeight(16777215)
            scroll.setMinimumHeight(80)
            layout.removeWidget(scroll)
            if name == 'orthophoto_pv_selection_scroll':
                overview_layout.addWidget(scroll, 1)
            else:
                result_scroll = scroll
        layout.removeWidget(self._run)
        overview_layout.addWidget(self._run)
        layout.removeWidget(self.table)
        self.panes.addWidget(overview)
        self.panes.addWidget(result_scroll)
        self.panes.addWidget(self.table)
        self.panes.setSizes([160, 340, 140])
        self.panes.setStretchFactor(1, 3)
        layout.insertWidget(4, self.panes, 1)
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
            for index, entry in enumerate(active_entries(self.regions[self.current_region])):
                entry['status'] = self.table.cellWidget(index, 2).currentData()
                entry['note'] = self.table.item(index, 3).text()

    def _clear_table(self):
        # Qt defers destruction of cell widgets; hide removed review controls
        # immediately so a deleted row cannot leave a visible dropdown behind.
        for index in range(self.table.rowCount()):
            review = self.table.cellWidget(index, 2)
            if review:
                review.hide()
        self.table.setRowCount(0)

    def _select_window(self, window):
        self._collect()
        super()._select_window(window)
        self.current_region = None
        self._clear_table()
        self._refresh_deleted()
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
        self.delete.setEnabled(self.correct.isEnabled())
        self.restore.setEnabled(self.current_region is not None and self.deleted.currentData() is not None)
        self.add.setEnabled(self._window is not None and all(1 <= v <= 2048 for v in self._window[2:]))
        running = self._model_process is not None and self._model_process.state() != QProcess.ProcessState.NotRunning
        self.model_start.setEnabled(running or self.current_region is not None)

    def _start_model_comparison(self):
        if self._model_process and self._model_process.state() != QProcess.ProcessState.NotRunning:
            self._cancel_model_comparison()
            return
        try:
            self._collect()
            saved, _ = load_module_review(self.comparison)
            _, current = parse_region(self.comparison, self.regions[self.current_region])
            if not self.comparison.source_path or saved.get(self.current_region) != current:
                raise ValueError('Zuerst aktuelle Modul-Entwürfe lokal speichern.')
            if not any(e['status'] == 'outline_ok' for e in active_entries(current)):
                raise ValueError('Mindestens einen Umriss passend beurteilen und lokal speichern.')
            manifest, _ = QFileDialog.getOpenFileName(self, 'Geprüfte lokale KI-Modellbeschreibung wählen',
                '', 'Lokale KI-Modellbeschreibung (*.json)')
            if not manifest:
                return
            import json
            from ..vision.pv_hawk_module_detector import PROFILE, evaluation_python
            from ..vision.cvut_module_detector import PROFILE as CVUT_PROFILE, evaluation_python as cvut_python
            from ..services.thermal_partial_comparison import _local
            path = _local(manifest)
            if path.stat().st_size > 32768:
                raise ValueError('Modellbeschreibung zu groß.')
            description = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(description, dict):
                raise ValueError('Modellbeschreibung muss ein JSON-Objekt sein.')
            profile = description.get('profile')
            executable = (evaluation_python(manifest) if profile == PROFILE else
                          cvut_python(manifest) if profile == CVUT_PROFILE else sys.executable)
            token = uuid4().hex
            self._model_pending = self.comparison.folder / f'pv-model-comparison-{token}.LOCAL.json'
            process = QProcess(self)
            process.setStandardOutputFile(QProcess.nullDevice())
            process.setStandardErrorFile(QProcess.nullDevice())
            process.finished.connect(self._model_finished)
            process.errorOccurred.connect(self._model_error)
            self._model_process = process
            self._model_cancelled = False
            script = Path(__file__).resolve().parents[3] / 'scripts/MCM_SolarCheck_PV_MODELLVERGLEICH.py'
            process.start(executable, [str(script), '--source', str(self.comparison.source_path),
                '--manifest', manifest, '--region', self.current_region, '--run-token', token])
            self._model_timer.start(5*60*1000)
            self.model_start.setText('KI-Vergleich abbrechen')
            self._status.setText('Lokaler Modellvergleich läuft, maximal fünf Minuten. Gespeicherte Entwürfe bleiben erhalten.')
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            self._status.setText(str(error))

    def _cancel_model_comparison(self):
        self._model_cancelled = True
        if self._model_process:
            self._model_process.kill()

    def _model_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._model_finished(2, QProcess.ExitStatus.CrashExit)

    def _model_finished(self, code, status):
        from ..services.thermal_partial_model_comparison import read_model_comparison, state_for_model
        self._model_timer.stop()
        self.model_start.setText('KI-Modellvergleich starten (lokal)')
        pending = self._model_pending
        self._model_pending = None
        try:
            if self._model_cancelled:
                raise ValueError('Vergleich abgebrochen; kein Ergebnis übernommen.')
            if code != 0 or status != QProcess.ExitStatus.NormalExit or pending is None:
                raise ValueError('Kein Vergleich erstellt. Modellbeschreibung, Gewichte und optionale ONNX-Prüfbibliothek prüfen.')
            record, _, _ = read_model_comparison(self.comparison, pending)
            target = self.comparison.folder / state_for_model(record['model'])
            if target.is_symlink():
                raise ValueError('Vergleichsziel darf keine Verknüpfung sein.')
            pending.replace(target)
            self._status.setText('KI-Vergleich separat lokal gespeichert; vorhandene Entwürfe bleiben erhalten.')
            self._open_model_comparison(report_path=target)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            self._status.setText(str(error))
        finally:
            if pending:
                pending.unlink(missing_ok=True)
                pending.with_suffix('.next.json').unlink(missing_ok=True)
            self._edit_buttons()

    def _open_model_comparison(self, *, report_path=None):
        try:
            from ..services.thermal_partial_model_comparison import STATE, CVUT_STATE
            from PySide6.QtWidgets import QInputDialog
            paths = [('Bisheriger KI-Vergleich', self.comparison.folder / STATE),
                     ('CVUT-Kandidat', self.comparison.folder / CVUT_STATE)]
            paths = [(label, path) for label, path in paths if path.exists()]
            if report_path is None and not paths:
                self._status.setText('Noch kein gespeicherter KI-Vergleich. Die Einrichtung allein erstellt keine Anlagen-Ergebnisse. '
                    'Im gespeicherten PV-Ausschnitt „KI-Modellvergleich starten (lokal)“ wählen.')
                return
            if report_path is None:
                if len(paths) == 1:
                    report_path = paths[0][1]
                else:
                    choice, accepted = QInputDialog.getItem(self, 'Gespeicherten KI-Vergleich öffnen',
                        'Vergleich wählen', [name for name, _ in paths], 1, False)
                    if not accepted:
                        return
                    report_path = dict(paths)[choice]
            from .thermal_partial_model_comparison import ModelComparisonDialog
            if self._model_dialog:
                self._model_dialog.deleteLater()
            self._model_dialog = ModelComparisonDialog(self.comparison, self, report_path=report_path)
            self._model_dialog.show()
            self._model_dialog.raise_()
            self._model_dialog.activateWindow()
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            self._status.setText('Kein passender gespeicherter KI-Vergleich; Quellen und gespeicherte Modulprüfung unverändert lassen.')

    def closeEvent(self, event):
        self._cancel_model_comparison()
        if self._model_process and self._model_process.state() != QProcess.ProcessState.NotRunning:
            self._model_process.waitForFinished(1000)
        super().closeEvent(event)

    def _refresh_deleted(self):
        region = self.regions.get(self.current_region)
        deleted = [e for e in region['entries'] if e.get('deleted', False)] if region else []
        self.deleted.blockSignals(True)
        self.deleted.clear()
        self.deleted.addItem(f'Gelöschte Umrisse ({len(deleted)})', None)
        for entry in deleted:
            self.deleted.addItem(entry['module_id'].split(':')[-1], entry['module_id'])
        self.deleted.blockSignals(False)

    def _delete_outline(self):
        index = self.table.currentRow()
        if not self.current_region or index < 0:
            return
        module_id = active_entries(self.regions[self.current_region])[index]['module_id']
        self._change_deleted(module_id, True)

    def _restore_outline(self):
        module_id = self.deleted.currentData()
        if self.current_region and module_id:
            self._change_deleted(module_id, False)

    def _change_deleted(self, module_id, deleted):
        try:
            self._collect()
            region = set_module_deleted(self.comparison, self.regions[self.current_region], module_id, deleted=deleted)
            self.regions[self.current_region] = region
            if self._detail_dialog:
                self._detail_dialog.close()
            self._restore_region(self.current_region)
            entries = active_entries(region)
            if not deleted:
                self.table.selectRow(next(i for i, e in enumerate(entries) if e['module_id'] == module_id))
            action = 'aus der Ansicht gelöscht' if deleted else 'wiederhergestellt'
            self._status.setText(f"{module_id.split(':')[-1]} {action}. Bitte Modul-Entwürfe lokal speichern.")
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            self._status.setText('Umriss nicht geändert; Quellen und lokale Notizen prüfen.')

    def _open_outline(self, *, correct):
        try:
            self._collect()
            if correct:
                index = self.table.currentRow()
                if not self.current_region or index < 0:
                    return
                region = self.regions[self.current_region]
                module_id = active_entries(region)[index]['module_id']
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
        entries = active_entries(region)
        index = (next(i for i, e in enumerate(entries) if e['module_id'] == module_id)
            if module_id else len(entries)-1)
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
            self.saved_regions.addItem(f'Ausschnitt {index} · {len(active_entries(region))} Entwürfe', key)
        self.saved_regions.setCurrentIndex(max(0, self.saved_regions.findData(selected)))
        self.saved_regions.blockSignals(False)

    def _after_result(self, result):
        self._labelled_result = None
        key = region_key(result.rgb_window)
        if key not in self.regions:
            self.regions[key] = make_region(self.comparison, result)
        self.current_region = key
        entries = active_entries(self.regions[key])
        self._clear_table()
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
        self._labelled_result = pixmap
        self._output.setPixmap(pixmap)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        if entries:
            self.table.selectRow(0)
        self._highlight_selected()
        self._refresh_regions(key)
        self._refresh_deleted()
        self._edit_buttons()
        self._status.setText(f'{len(entries)} lokale Modul-Entwürfe. IDs gelten nur in diesem RGB-Ausschnitt. '
            'Gültige Thermalpixel sind kein Nachweis vollständiger Anlagenabdeckung. '
            'Der vorhandene Detektor liefert konservative Vorschläge nur für abgrenzbare Modulflächen.')

    def _highlight_selected(self):
        index = self.table.currentRow()
        if (self._labelled_result is None or self.proposal_result is None
                or not 0 <= index < len(self.proposal_result.proposals)):
            return
        result = self.proposal_result
        polygon = result.proposals[index].rgb_polygon_px
        col, row, width, height = result.rgb_window
        factor = min(1., 1024/max(width, height))
        pixmap = self._labelled_result.copy()
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(255, 80, 0), 4))
        painter.drawPolygon(QPolygonF([QPointF((x-col)*factor, (y-row)*factor) for x, y in polygon]))
        painter.end()
        self._output.setPixmap(pixmap)
        center = np.mean(polygon, axis=0)
        scroll = self.findChild(QScrollArea, 'orthophoto_pv_result_scroll')
        scroll.ensureVisible(round((center[0]-col)*factor), round((center[1]-row)*factor), 60, 60)

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
            _resizable_dialog(dialog)
            layout = QVBoxLayout(dialog)
            module_id = active_entries(self.regions[self.current_region])[index]['module_id']
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
