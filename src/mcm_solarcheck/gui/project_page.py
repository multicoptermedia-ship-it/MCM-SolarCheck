"""Project workspace for the SolarCheck GUI.

The first implementation slice stays deliberately presentation-only: project
creation/opening operations will be supplied by application services rather
than invented in Qt widget state.
"""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget


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
        layout.addRow("Projekt-ID", self.project_id)
        layout.addRow("Projektname", self.name)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)
        self.project_id.textChanged.connect(self._update_acceptance)
        self.name.textChanged.connect(self._update_acceptance)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _update_acceptance(self) -> None:
        self._ok_button.setEnabled(
            bool(self.project_id.text().strip()) and bool(self.name.text().strip())
        )

    def values(self) -> tuple[str, str]:
        return self.project_id.text(), self.name.text()


def make_project_page(
    parent: QWidget | None = None,
    *,
    projects=(),
    on_create_project=None,
    on_open_project=None,
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
                project_id, name = dialog.values()
                on_create_project(project_id, name)

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
        item = QListWidgetItem(f"{project.name} · {project.created_at}")
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
    layout.addStretch(1)
    return page
