"""Prepare saved local corrections, without invoking any training runtime."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton, QFormLayout

from ..services.thermal_partial_training import (
    read_learning_preparation, save_learning_preparation, revoke_learning_preparation, prepared_split, SPLIT_LABELS,
)


class LearningPreparationDialog(QDialog):
    def __init__(self, comparison, key, parent=None):
        super().__init__(parent)
        self.setObjectName('pv_learning_preparation')
        self.setWindowTitle('PV-Lernmuster lokal vorbereiten')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setSizeGripEnabled(True)
        self.comparison, self.key = comparison, key
        state = read_learning_preparation(comparison, key)
        self.review_sha256 = state['review_sha256']
        self.problem = state['problem']
        layout = QVBoxLayout(self)
        for text in (comparison.label,
                f"{state['module_count']} passend beurteilte Modulflächen aus dem gespeicherten Ausschnitt. "
                'Aktuelle Korrekturen und Ergänzungen werden verwendet. Gelöschte/verworfene Umrisse sind keine Hintergrundlabels.',
                'Nur wenige kleine Ausschnitte vollständig beschriften. Alle sichtbaren Module müssen als ganze Flächen markiert sein; '
                'bei angeschnittenen oder unklaren Modulen die Vorbereitung noch nicht bestätigen. '
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
        self.complete = QCheckBox('Vollständige Beschriftung dieses Ausschnitts bestätigen')
        self.complete.setObjectName('pv_learning_complete')
        layout.addWidget(self.complete)
        self.status = QLabel()
        self.status.setObjectName('pv_learning_status')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        if state['current']:
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
        self._controls()
        self.resize(850, 520)

    def _controls(self):
        self.save.setEnabled(not self.problem and self.complete.isChecked()
            and bool(self.group.text().strip()) and bool(self.reviewer.text().strip()))

    def _saved(self, entry):
        self.status.setText(f"Vorbereitung lokal gespeichert · {len(entry['manifest']['labels'])} Modulflächen · "
            f"Datenteil: {SPLIT_LABELS[prepared_split(entry)]}. Noch kein vollständiger Trainingsdatensatz oder trainiertes Modell.")

    def _save(self):
        try:
            entry = save_learning_preparation(self.comparison, self.key, reviewer=self.reviewer.text(),
                group_id=self.group.text(), complete_annotation=self.complete.isChecked(),
                expected_review_sha256=self.review_sha256)
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
