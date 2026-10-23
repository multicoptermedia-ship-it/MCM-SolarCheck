from dataclasses import replace
from zoneinfo import available_timezones

from mcm_solarcheck.domain.project_profile import ProjectProfile

from PySide6.QtCore import Qt

"""Project workspace for the SolarCheck GUI.

The first implementation slice stays deliberately presentation-only: project
creation/opening operations will be supplied by application services rather
than invented in Qt widget state.
"""

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget



def _timezone_picker(field: QLineEdit, *, allow_empty: bool, object_name: str) -> QComboBox:
    """Use explicit IANA choices while keeping the validated data field intact.

    The hidden QLineEdit is retained for backward-compatible form bindings;
    operators do not have to guess the spelling of a timezone.
    """
    choice = QComboBox(field.parentWidget())
    choice.setObjectName(object_name)
    choice.setAccessibleName("Standort-Zeitzone auswählen")
    choice.setToolTip("Zeitzone der Anlage wählen, z. B. Europe/Berlin.")
    choice.setMaxVisibleItems(18)
    choice.addItem("Zeitzone auswählen …" if not allow_empty else "Keine Zeitzone", "")
    popular = ("Europe/Berlin", "Europe/Vienna", "Europe/Zurich", "Europe/London", "Etc/UTC")
    known = set(available_timezones()) | set(popular)
    for name in (*popular, *sorted(known.difference(popular))):
        choice.addItem(name, name)
    existing = field.text().strip()
    if existing and existing not in known:
        choice.addItem(existing, existing)
    if existing:
        index = choice.findData(existing)
        if index >= 0:
            choice.setCurrentIndex(index)
    choice.currentIndexChanged.connect(
        lambda _index: field.setText(choice.currentData() or "")
    )
    field.hide()
    return choice


class NewProjectDialog(QDialog):
    """Collect only the minimal project identity required by the service."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Neues Projekt")
        layout = QFormLayout(self)
        self.project_id = QLineEdit(self)
        self.project_id.setObjectName("new_project_id")
        self.name = QLineEdit(self)
        self.name.setObjectName("new_project_name")
        # Legacy fields remain as internal compatibility slots, not inputs.
        self.project_id.hide()
        self.name.hide()
        info = QLabel(
            "Die Projektnummer wird beim Speichern automatisch vergeben. "
            "Als Projektname verwenden wir die Bezeichnung der Anlage.",
            self,
        )
        info.setObjectName("auto_project_number_hint")
        info.setWordWrap(True)
        layout.addRow(info)
        self.customer_name = QLineEdit(self); self.customer_name.setObjectName("new_project_customer_name")
        self.site_name = QLineEdit(self); self.site_name.setObjectName("new_project_site_name")
        self.site_name.setMaxLength(80)
        self.site_name.setPlaceholderText("3–80 Zeichen, z. B. PV-Anlage Norddach")
        self.site_name.setAccessibleDescription(
            "Anlagenbezeichnung: mindestens 3, höchstens 80 Zeichen."
        )

        self.site_street = QLineEdit(self); self.site_street.setObjectName("new_project_site_street")
        self.site_postal_code = QLineEdit(self); self.site_postal_code.setObjectName("new_project_site_postal_code")
        self.site_city = QLineEdit(self); self.site_city.setObjectName("new_project_site_city")
        self.site_timezone = QLineEdit(self); self.site_timezone.setObjectName("new_project_site_timezone")
        self.site_timezone.setPlaceholderText("z. B. Europe/Berlin")
        self.inspector = QLineEdit(self); self.inspector.setObjectName("new_project_inspector")
        for label, field in (("Kunde",self.customer_name),("Anlage",self.site_name),("Standort Straße",self.site_street),("Standort PLZ",self.site_postal_code),("Standort Ort",self.site_city)):
            layout.addRow(label, field)
        self.site_timezone_choice = _timezone_picker(
            self.site_timezone, allow_empty=False,
            object_name="new_project_site_timezone_choice",
        )
        layout.addRow("Standort-Zeitzone (IANA)", self.site_timezone_choice)
        layout.addRow("Prüfer", self.inspector)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)
        self.project_id.textChanged.connect(self._update_acceptance)
        self.name.textChanged.connect(self._update_acceptance)
        for field in (self.customer_name,self.site_name,self.site_street,self.site_postal_code,self.site_city,self.site_timezone,self.inspector):
            field.textChanged.connect(self._update_acceptance)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _update_acceptance(self) -> None:
        required=(self.customer_name,self.site_name,self.site_street,self.site_postal_code,self.site_city,self.site_timezone,self.inspector)
        if not all(field.text().strip() for field in required):
            self._ok_button.setEnabled(False); return
        if not 3 <= len(self.site_name.text().strip()) <= 80:
            self._ok_button.setEnabled(False); return
        try:
            self.profile()
        except ValueError:
            self._ok_button.setEnabled(False); return
        self._ok_button.setEnabled(True)

    def profile(self) -> ProjectProfile:
        return ProjectProfile(customer_name=self.customer_name.text(),site_name=self.site_name.text(),site_street=self.site_street.text(),site_postal_code=self.site_postal_code.text(),site_city=self.site_city.text(),inspector=self.inspector.text(),site_timezone=self.site_timezone.text())

    def values(self) -> tuple[str, str, ProjectProfile]:
        return "", self.site_name.text().strip(), self.profile()


class EditProjectProfileDialog(QDialog):
    """Edit only visible fields, preserving all original optional metadata."""

    FIELDS = (
        ("customer_name", "Kunde"),
        ("site_name", "Anlage"),
        ("site_street", "Standort Straße"),
        ("site_postal_code", "Standort PLZ"),
        ("site_city", "Standort Ort"),
        ("site_timezone", "Standort-Zeitzone (IANA, optional)"),
        ("inspector", "Prüfer"),
    )

    def __init__(self, original: ProjectProfile | None, parent=None) -> None:
        super().__init__(parent)
        self._original = original
        self.setWindowTitle("Projektstammdaten bearbeiten")
        layout = QFormLayout(self)
        self.fields = {}
        for key, label in self.FIELDS:
            field = QLineEdit(self)
            field.setObjectName("edit_profile_" + key)
            field.setText(getattr(original, key, None) or "")
            if key == "site_timezone":
                field.setPlaceholderText("z. B. Europe/Berlin")
                self.site_timezone_choice = _timezone_picker(
                    field, allow_empty=True,
                    object_name="edit_profile_site_timezone_choice",
                )
                layout.addRow(label, self.site_timezone_choice)
            else:
                layout.addRow(label, field)
            self.fields[key] = field

        info = QLabel(
            "Änderungen gelten nur für das aktive Offline-Projekt. "
            "Ein vorbereiteter Berichtsentwurf wird nach dem Speichern ungültig.",
            self,
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.TextFormat.PlainText)
        layout.addRow(info)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        for field in self.fields.values():
            field.textChanged.connect(self._update_acceptance)
        self._update_acceptance()

    def profile(self) -> ProjectProfile:
        values = {key: field.text().strip() for key, field in self.fields.items()}
        values["site_timezone"] = values["site_timezone"] or None
        if self._original is None:
            return ProjectProfile(**values)
        return replace(self._original, **values)

    def _update_acceptance(self) -> None:
        try:
            result = self.profile()
        except ValueError:
            self._ok_button.setEnabled(False)
        else:
            self._ok_button.setEnabled(
                self._original is None or result != self._original
            )


def make_project_page(
    parent: QWidget | None = None,
    *,
    projects=(),
    on_create_project=None,
    on_open_project=None,
    current_project_id=None,
    profile=None,
    on_edit_profile=None,
    last_profile_status=None,
) -> QWidget:
    page = QWidget(parent)
    page.setObjectName("project_page")
    layout = QVBoxLayout(page)

    heading = QLabel("SolarCheck / PV-Inspektion", page)
    heading.setObjectName("page_heading")
    layout.addWidget(heading)

    create = QPushButton("Neues Projekt erstellen", page)
    create.setObjectName("create_project_button")
    create.setToolTip("Projektanlage wird über den Application Service ausgeführt.")
    if on_create_project is not None:
        def request_project_creation() -> None:
            dialog = NewProjectDialog(page)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                project_id, name, profile = dialog.values()
                on_create_project(project_id, name, profile)

        create.clicked.connect(request_project_creation)
    else:
        create.setEnabled(False)
        create.setAccessibleDescription(
            "Nicht verfügbar, solange kein Project Application Service angebunden ist."
        )
    layout.addWidget(create)

    projects_heading = QLabel("Vorhandene Projekte", page)
    projects_heading.setObjectName("existing_projects_heading")
    layout.addWidget(projects_heading)

    project_list = QListWidget(page)
    project_list.setObjectName("project_list")
    for project in projects:
        number = getattr(project, "display_number", None)
        item = QListWidgetItem(
            f"{project.name} · {number} · {project.created_at}"
            if number else f"{project.name} · {project.created_at}"
        )
        item.setData(256, project.project_id)
        project_list.addItem(item)
    project_list.setVisible(project_list.count() > 0)
    layout.addWidget(project_list)

    empty = QLabel(
        "Keine gespeicherten Projekte vorhanden.",
        page,
    )
    empty.setObjectName("project_empty_state")
    empty.setWordWrap(True)
    empty.setVisible(project_list.count() == 0)
    layout.addWidget(empty)

    open_project = QPushButton("Projekt öffnen", page)
    open_project.setObjectName("open_project_button")
    open_project.setToolTip("Projektöffnung verwendet ausschließlich persistierte Projektdaten.")
    if on_open_project is not None:
        open_project.clicked.connect(
            lambda: on_open_project(
                project_list.currentItem().data(256)
                if project_list.currentItem() is not None
                else None
            )
        )
        open_project.setEnabled(project_list.currentItem() is not None)
        project_list.currentItemChanged.connect(
            lambda current, previous: open_project.setEnabled(current is not None)
        )
    else:
        open_project.setEnabled(False)
        open_project.setAccessibleDescription(
            "Nicht verfügbar, solange kein Project Application Service angebunden ist."
        )
    layout.addWidget(open_project)

    active_number = next(
        (getattr(p, "display_number", None) for p in projects
         if p.project_id == current_project_id), None,
    )
    current = QLabel(
        f"Aktives Projekt: {active_number or current_project_id}"
        if current_project_id is not None else "Kein aktives Projekt geöffnet.",
        page,
    )
    current.setObjectName("project_profile_context")
    current.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(current)
    edit = QPushButton("Stammdaten des aktiven Projekts bearbeiten …", page)
    edit.setObjectName("edit_project_profile_button")
    edit.setEnabled(current_project_id is not None and on_edit_profile is not None)
    if current_project_id is not None and on_edit_profile is not None:
        def request_profile_edit():
            dialog = EditProjectProfileDialog(profile, page)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                on_edit_profile(profile, dialog.profile())

        edit.clicked.connect(request_profile_edit)
    layout.addWidget(edit)
    if last_profile_status:
        status = QLabel(last_profile_status, page)
        status.setObjectName("project_profile_edit_status")
        status.setTextFormat(Qt.TextFormat.PlainText)
        status.setWordWrap(True)
        layout.addWidget(status)
    layout.addStretch(1)
    return page
