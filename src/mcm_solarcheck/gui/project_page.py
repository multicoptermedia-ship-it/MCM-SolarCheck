"""Project workspace for the SolarCheck GUI.

The first implementation slice stays deliberately presentation-only: project
creation/opening operations will be supplied by application services rather
than invented in Qt widget state.
"""

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


def make_project_page(parent: QWidget | None = None) -> QWidget:
    page = QWidget(parent)
    page.setObjectName("project_page")
    layout = QVBoxLayout(page)

    heading = QLabel("SolarCheck / PV-Inspektion", page)
    heading.setObjectName("page_heading")
    layout.addWidget(heading)

    create = QPushButton("Neues Projekt erstellen", page)
    create.setObjectName("create_project_button")
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
    layout.addStretch(1)
    return page
