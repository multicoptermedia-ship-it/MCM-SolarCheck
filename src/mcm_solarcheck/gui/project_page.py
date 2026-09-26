"""Project workspace for the SolarCheck GUI.

The first implementation slice stays deliberately presentation-only: project
creation/opening operations will be supplied by application services rather
than invented in Qt widget state.
"""

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


def make_project_page(
    parent: QWidget | None = None,
    *,
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
        create.clicked.connect(on_create_project)
    else:
        create.setEnabled(False)
        create.setAccessibleDescription(
            "Nicht verfügbar, solange kein Project Application Service angebunden ist."
        )
    layout.addWidget(create)

    projects_heading = QLabel("Vorhandene Projekte", page)
    projects_heading.setObjectName("existing_projects_heading")
    layout.addWidget(projects_heading)

    empty = QLabel(
        "Noch keine Projektdaten geladen. Projekte werden hier nur aus "
        "persistierten Backend-Daten angezeigt.",
        page,
    )
    empty.setObjectName("project_empty_state")
    empty.setWordWrap(True)
    layout.addWidget(empty)

    open_project = QPushButton("Projekt öffnen", page)
    open_project.setObjectName("open_project_button")
    open_project.setToolTip("Projektöffnung verwendet ausschließlich persistierte Projektdaten.")
    if on_open_project is not None:
        open_project.clicked.connect(on_open_project)
    else:
        open_project.setEnabled(False)
        open_project.setAccessibleDescription(
            "Nicht verfügbar, solange kein Project Application Service angebunden ist."
        )
    layout.addWidget(open_project)
    layout.addStretch(1)
    return page
