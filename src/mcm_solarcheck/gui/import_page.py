"""Import workspace presentation for SolarCheck."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget


def make_import_page(parent=None, *, current_project_id=None, on_import_images=None, choose_directory=None, import_summary=None, import_attempt=None, import_verification=None, on_inspect_geotiff=None, choose_geotiff=None, geotiff_result=None, on_register_geotiff=None, choose_register_geotiff=None, geotiff_artifacts=(), on_compare_orthophotos=None, choose_orthophoto_pair=None, orthophoto_comparison=None, orthophoto_comparison_error=None, on_generate_orthophotos=None, on_preview_rgb_files=None, choose_rgb_files=None, rgb_preview_status=None, rgb_preview_path=None, on_preview_rgb_folder=None, choose_rgb_folder=None, on_run_rgb_links=None, choose_rgb_link_folder=None, on_export_rgb_segments=None, choose_rgb_registration=None, choose_rgb_segment_folder=None, on_inspect_rgb_integrity=None, choose_rgb_integrity_folder=None, choose_rgb_integrity_output=None, rgb_integrity_status=None, on_cancel_rgb_integrity=None, on_start_flight_preflight=None, choose_preflight_folder=None, on_cancel_flight_preflight=None, flight_preflight_status=None):
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

    preflight_start = QPushButton(
        "Großen DJI-Flugordner vorab prüfen (nur Dateinamen/Größen)", page,
    )
    preflight_start.setObjectName("start_large_flight_preflight_button")
    if current_project_id is not None and on_start_flight_preflight is not None:
        def request_preflight():
            select = choose_preflight_folder or (
                lambda: QFileDialog.getExistingDirectory(
                    page, "DJI-Mavic-3T-Quellordner für Vorprüfung auswählen",
                )
            )
            folder = select()
            if folder:
                on_start_flight_preflight(folder)
        preflight_start.clicked.connect(request_preflight)
    else:
        preflight_start.setEnabled(False)
    layout.addWidget(preflight_start)

    preflight_cancel = QPushButton("Laufende DJI-Vorprüfung abbrechen", page)
    preflight_cancel.setObjectName("cancel_large_flight_preflight_button")
    preflight_cancel.setEnabled(on_cancel_flight_preflight is not None)
    if on_cancel_flight_preflight is not None:
        preflight_cancel.clicked.connect(on_cancel_flight_preflight)
    layout.addWidget(preflight_cancel)
    if flight_preflight_status is not None:
        preflight_label = QLabel(flight_preflight_status, page)
        preflight_label.setObjectName("large_flight_preflight_status")
        preflight_label.setTextFormat(Qt.TextFormat.PlainText)
        preflight_label.setWordWrap(True)
        layout.addWidget(preflight_label)

    folder_preview = QPushButton("DJI-Bildordner automatisch auswerten (derzeit 3–4 RGB)", page)
    folder_preview.setObjectName("preview_rgb_folder_button")
    if current_project_id is not None and on_preview_rgb_folder is not None:
        def request_folder_preview():
            chooser = choose_rgb_folder or (lambda: QFileDialog.getExistingDirectory(
                page, "DJI-Bildordner auswählen"
            ))
            folder = chooser()
            if folder:
                on_preview_rgb_folder(folder)
        folder_preview.clicked.connect(request_folder_preview)
    else:
        folder_preview.setEnabled(False)
    layout.addWidget(folder_preview)
    link_button = QPushButton("DJI-Flugordner: alle RGB-Bildverbindungen prüfen", page)
    link_button.setObjectName("run_rgb_links_button")
    if current_project_id is not None and on_run_rgb_links is not None:
        def request_link_run():
            chooser = choose_rgb_link_folder or (lambda: QFileDialog.getExistingDirectory(
                page, "DJI-Flugordner für vollständige RGB-Prüfung auswählen"
            ))
            folder = chooser()
            if folder:
                on_run_rgb_links(folder)
        link_button.clicked.connect(request_link_run)
    else:
        link_button.setEnabled(False)
    layout.addWidget(link_button)
    segments_button = QPushButton("DJI-Flug: alle RGB-Segmentvorschauen exportieren (nichtmetrisch)", page)
    segments_button.setObjectName("export_rgb_segments_button")
    if current_project_id is not None and on_export_rgb_segments is not None:
        def request_segments_export():
            choose_folder = choose_rgb_segment_folder or (
                lambda: QFileDialog.getExistingDirectory(page, "DJI-Flugordner auswählen")
            )
            folder = choose_folder()
            if not folder:
                return
            choose_registration = choose_rgb_registration or (
                lambda: QFileDialog.getOpenFileName(
                    page, "RGB-Registrierung auswählen", "", "JSON-Datei (*.json)"
                )[0]
            )
            registration = choose_registration()
            if registration:
                on_export_rgb_segments(folder, registration)
        segments_button.clicked.connect(request_segments_export)
    else:
        segments_button.setEnabled(False)
    layout.addWidget(segments_button)
    integrity_button = QPushButton("RGB-Arbeitsdateien auf Integrität prüfen (nur lesen)", page)
    integrity_button.setObjectName("inspect_rgb_integrity_button")
    if current_project_id is not None and on_inspect_rgb_integrity is not None:
        def request_integrity():
            choose_source = choose_rgb_integrity_folder or (
                lambda: QFileDialog.getExistingDirectory(page, "DJI-JPEG-Quellordner auswählen")
            )
            source_folder = choose_source()
            if not source_folder:
                return
            choose_output = choose_rgb_integrity_output or (
                lambda: QFileDialog.getExistingDirectory(page, "RGB-NPY-Arbeitsordner auswählen")
            )
            output_folder = choose_output()
            if output_folder:
                on_inspect_rgb_integrity(source_folder, output_folder)
        integrity_button.clicked.connect(request_integrity)
    else:
        integrity_button.setEnabled(False)
    layout.addWidget(integrity_button)
    cancel_integrity = QPushButton("RGB-Integritätsprüfung abbrechen", page)
    cancel_integrity.setObjectName("cancel_rgb_integrity_button")
    cancel_integrity.setEnabled(on_cancel_rgb_integrity is not None)
    if on_cancel_rgb_integrity is not None:
        cancel_integrity.clicked.connect(on_cancel_rgb_integrity)
    layout.addWidget(cancel_integrity)
    if rgb_integrity_status is not None:
        integrity_label = QLabel(rgb_integrity_status, page)
        integrity_label.setObjectName("rgb_integrity_status")
        integrity_label.setWordWrap(True)
        integrity_label.setAccessibleDescription(
            "Nur lesende Integritätsdiagnose; keine automatische Wiederaufnahme oder Freigabe."
        )
        layout.addWidget(integrity_label)
    preview_button = QPushButton("RGB-Einzelbilder als Vorschau zusammensetzen (3–4)", page)
    preview_button.setObjectName("preview_rgb_files_button")
    if current_project_id is not None and on_preview_rgb_files is not None:
        def request_rgb_preview():
            chooser = choose_rgb_files or (lambda: QFileDialog.getOpenFileNames(
                page, "3–4 RGB-Bilder in Aufnahmereihenfolge auswählen", "",
                "RGB-Bilder (*.jpg *.jpeg *.png)"
            )[0])
            selected = chooser()
            if selected:
                on_preview_rgb_files(tuple(selected))
        preview_button.clicked.connect(request_rgb_preview)
    else:
        preview_button.setEnabled(False)
    layout.addWidget(preview_button)
    if rgb_preview_status is not None:
        preview_status = QLabel(rgb_preview_status, page)
        preview_status.setObjectName("rgb_preview_status")
        preview_status.setWordWrap(True)
        layout.addWidget(preview_status)
    if rgb_preview_path is not None:
        preview_image = QLabel(page)
        preview_image.setObjectName("rgb_preview_image")
        preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_image.setAccessibleDescription(
            "Nicht metrisch verifizierte RGB-Bildvorschau; kein Orthofoto."
        )
        pixmap = QPixmap(str(rgb_preview_path))
        if not pixmap.isNull():
            preview_image.setPixmap(pixmap.scaled(
                720, 420, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            layout.addWidget(preview_image)
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
        def request_native_generation():
            job_path = QFileDialog.getOpenFileName(
                page, "Vermessungsauftrag auswählen", "", "JSON (*.json)"
            )[0]
            if job_path:
                on_generate_orthophotos(job_path)
        generate_button.clicked.connect(request_native_generation)
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
