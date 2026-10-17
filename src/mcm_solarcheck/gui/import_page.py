"""Import workspace presentation for SolarCheck."""

from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget


def make_import_page(parent=None, *, current_project_id=None, on_import_images=None, choose_directory=None, import_summary=None, import_attempt=None, import_verification=None, on_inspect_geotiff=None, choose_geotiff=None, geotiff_result=None, on_register_geotiff=None, choose_register_geotiff=None, geotiff_artifacts=(), on_compare_orthophotos=None, choose_orthophoto_pair=None, orthophoto_comparison=None, orthophoto_comparison_error=None, on_generate_orthophotos=None):
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

    if import_verification is not None:
        verification_heading = QLabel("Importprüfung", page)
        verification_heading.setObjectName("import_verification_heading")
        layout.addWidget(verification_heading)

        verification = QLabel(
            f"Qualität: {import_verification.quality_pass} OK · "
            f"{import_verification.quality_review} prüfen · "
            f"{import_verification.quality_reject} verworfen\n"
            f"Fehlende Metadaten: {import_verification.missing_timestamp} Zeit · "
            f"{import_verification.missing_position} Position · "
            f"{import_verification.missing_camera_identity} Kamera",
            page,
        )
        verification.setObjectName("import_verification")
        verification.setAccessibleDescription(
            "Persistierte Qualitäts- und Metadatenprüfung des aktiven Projekts."
        )
        layout.addWidget(verification)

    if import_attempt is not None:
        if import_attempt.succeeded:
            status_text = "Letzter Import erfolgreich abgeschlossen."
        else:
            status_text = f"Import fehlgeschlagen: {import_attempt.error}"
        status = QLabel(status_text, page)
        status.setObjectName("import_attempt_status")
        status.setProperty("outcome", "success" if import_attempt.succeeded else "error")
        status.setAccessibleDescription(
            "Ergebnis des letzten Importversuchs laut Anwendungsservice."
        )
        layout.addWidget(status)

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
    inspect_button = QPushButton("GeoTIFF / GIS-Metadaten prüfen", page)
    inspect_button.setObjectName("inspect_geotiff_button")
    if current_project_id is not None and on_inspect_geotiff is not None:
        def request_geotiff_inspection():
            chooser = choose_geotiff or (lambda: QFileDialog.getOpenFileName(
                page, "GeoTIFF auswählen", "", "GeoTIFF (*.tif *.tiff)"
            )[0])
            selected = chooser()
            if selected:
                on_inspect_geotiff(selected)
        inspect_button.clicked.connect(request_geotiff_inspection)
    else:
        inspect_button.setEnabled(False)
    layout.addWidget(inspect_button)
    if geotiff_result is not None:
        result = QLabel(geotiff_result, page)
        result.setObjectName("geotiff_inspection_result")
        result.setWordWrap(True)
        layout.addWidget(result)

    register_button = QPushButton("GeoTIFF dauerhaft im Projekt registrieren", page)
    register_button.setObjectName("register_geotiff_button")
    if current_project_id is not None and on_register_geotiff is not None:
        def request_geotiff_registration():
            chooser = choose_register_geotiff or (lambda: QFileDialog.getOpenFileName(
                page, "GeoTIFF zur Registrierung auswählen", "", "GeoTIFF (*.tif *.tiff)"
            )[0])
            selected = chooser()
            if selected:
                on_register_geotiff(selected)
        register_button.clicked.connect(request_geotiff_registration)
    else:
        register_button.setEnabled(False)
    layout.addWidget(register_button)
    artifact_lines = [
        f"{item['source_path']} · {item['source_kind']} · CRS {item['crs']} · SHA-256 {item['content_sha256']}"
        for item in geotiff_artifacts
    ]
    artifacts = QLabel(
        "Registrierte GeoTIFF-Dateien (nur Metadaten, keine fachliche Freigabe):\n"
        + ("\n".join(artifact_lines) if artifact_lines else "Keine GeoTIFF-Dateien registriert."),
        page,
    )
    artifacts.setObjectName("registered_geotiff_artifacts")
    artifacts.setWordWrap(True)
    layout.addWidget(artifacts)
    generate_button = QPushButton('RGB- und Thermal-Orthofotos erzeugen (vermessene Fläche)', page)
    generate_button.setObjectName('generate_orthophotos_button')
    if current_project_id is not None and on_generate_orthophotos is not None:
        generate_button.clicked.connect(on_generate_orthophotos)
    else:
        generate_button.setEnabled(False)
        generate_button.setToolTip('Benötigt geprüfte Vermessung, importierte Originalbilder und einen angebundenen Erzeugungsablauf.')
    layout.addWidget(generate_button)
    compare_button = QPushButton("RGB- und Thermal-Orthofotos vergleichen", page)
    compare_button.setObjectName("compare_orthophotos_button")
    if current_project_id is not None and on_compare_orthophotos is not None:
        def request_comparison():
            if choose_orthophoto_pair is not None:
                paths = choose_orthophoto_pair()
            else:
                rgb = QFileDialog.getOpenFileName(
                    page, "RGB-Orthofoto auswählen", "", "GeoTIFF (*.tif *.tiff)"
                )[0]
                thermal = QFileDialog.getOpenFileName(
                    page, "Thermal-Orthofoto auswählen", "", "GeoTIFF (*.tif *.tiff)"
                )[0] if rgb else ""
                paths = (rgb, thermal)
            if paths and len(paths) == 2 and all(paths):
                on_compare_orthophotos(*paths)
        compare_button.clicked.connect(request_comparison)
    else:
        compare_button.setEnabled(False)
    layout.addWidget(compare_button)
    if orthophoto_comparison_error is not None:
        error_label = QLabel(orthophoto_comparison_error, page)
        error_label.setObjectName("orthophoto_comparison_error")
        error_label.setWordWrap(True)
        layout.addWidget(error_label)
    if orthophoto_comparison is not None:
        from mcm_solarcheck.gui.orthophoto_comparison import OrthophotoComparisonWidget
        rgb_pixels, thermal_pixels = orthophoto_comparison
        layout.addWidget(OrthophotoComparisonWidget(rgb_pixels, thermal_pixels, page))
    layout.addStretch(1)
    return page
