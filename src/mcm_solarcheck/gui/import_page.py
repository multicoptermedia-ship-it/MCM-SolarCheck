"""Import workspace presentation for SolarCheck."""

from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget


def make_import_page(parent=None, *, current_project_id=None, on_import_images=None, choose_directory=None, import_summary=None):
    page = QWidget(parent)
    page.setObjectName("import_page")
    layout = QVBoxLayout(page)

    heading = QLabel("Bilddaten importieren", page)
    heading.setObjectName("page_heading")
    layout.addWidget(heading)

    project = QLabel(
        f"Aktives Projekt: {current_project_id}"
        if current_project_id
        else "Kein aktives Projekt ausgewählt.",
        page,
    )
    project.setObjectName("import_project_context")
    layout.addWidget(project)

    if import_summary is not None:
        summary_heading = QLabel("Persistierter Importstand", page)
        summary_heading.setObjectName("import_summary_heading")
        layout.addWidget(summary_heading)

        summary = QLabel(
            f"{import_summary.rgb_frames} RGB · "
            f"{import_summary.thermal_frames} Thermal · "
            f"{import_summary.image_pairs} Paare",
            page,
        )
        summary.setObjectName("import_summary")
        summary.setAccessibleDescription(
            "Persistierte Bild- und Paarzahlen des aktiven Projekts."
        )
        layout.addWidget(summary)

    import_images = QPushButton("Bilddaten auswählen", page)
    import_images.setObjectName("import_images_button")
    if current_project_id is not None and on_import_images is not None:
        def request_import():
            chooser = choose_directory or (
                lambda: QFileDialog.getExistingDirectory(
                    page, "Bildverzeichnis auswählen"
                )
            )
            source_directory = chooser()
            if source_directory:
                on_import_images(source_directory)

        import_images.clicked.connect(request_import)
    else:
        import_images.setEnabled(False)
        import_images.setAccessibleDescription(
            "Nicht verfügbar, solange kein aktives Projekt und Import-Service angebunden sind."
        )
    layout.addWidget(import_images)
    layout.addStretch(1)
    return page
