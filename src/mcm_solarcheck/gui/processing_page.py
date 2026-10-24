"""Read-only Windows processing workspace from authoritative project evidence."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)


def make_processing_page(
    parent=None, *, current_project_id=None, overview=None, on_refresh=None,
    on_check_registration=None, registration_check_status=None, choose_control_file=None,
    project_label=None, processing_run=None,
    on_check_imported_files=None, on_cancel_imported_files=None,
    image_check_status=None, image_check_running=False,
    on_check_thermal_raw=None, on_cancel_thermal_raw=None,
    thermal_check_status=None, thermal_check_running=False,
    on_analyze_thermal_stats=None, on_cancel_thermal_stats=None,
    thermal_stats_status=None, thermal_stats_running=False,
    on_sample_rgb_modules=None, on_cancel_rgb_modules=None,
    rgb_sample_status=None, rgb_sample_running=False,
    on_check_module_readiness=None, module_readiness_status=None,
    on_preview_rgb_overlay=None, on_cancel_rgb_overlay=None,
    rgb_overlay_status=None, rgb_overlay_running=False,
):
    """Show persisted image/analysis facts without implying processing was run."""
    page = QWidget(parent)
    page.setObjectName("processing_page")
    root = QVBoxLayout(page)
    root.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(page)
    scroll.setObjectName("processing_workspace_scroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    content = QWidget(scroll)
    layout = QVBoxLayout(content)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    layout.setContentsMargins(14, 14, 14, 22)
    layout.setSpacing(12)
    scroll.setWidget(content)
    root.addWidget(scroll)

    heading = QLabel("Verarbeitung", page)
    heading.setObjectName("page_heading")
    layout.addWidget(heading)

    project = QLabel(
        f"Aktives Projekt: {project_label or current_project_id}"
        if current_project_id is not None else "Kein aktives Projekt ausgewählt.",
        page,
    )
    project.setObjectName("processing_project_context")
    project.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(project)

    if overview is None:
        empty = QLabel(
            "Kein gespeicherter Verarbeitungsstand verfügbar. "
            "Bitte zuerst ein Projekt auswählen.",
            page,
        )
        empty.setObjectName("processing_empty_state")
        empty.setWordWrap(True)
        layout.addWidget(empty)
    else:
        counts = overview.summary
        # Three readable headline counters; only SQLite values, no inferred
        # processing completion or fabricated module detections.
        metrics = QHBoxLayout()
        for value, title in (
            (counts.thermal_frames, "Thermalbilder"),
            (counts.rgb_frames, "RGB-Bilder"),
            (counts.image_pairs, "Bildpaare"),
        ):
            card = QFrame(content)
            card.setObjectName("processing_metric_card")
            card.setStyleSheet(
                "QFrame#processing_metric_card { background: #e2e8e3;"
                " border: 1px solid #b9c8bc; border-radius: 6px; }"
            )
            card_layout = QVBoxLayout(card)
            number = QLabel(str(value), card)
            number.setObjectName("processing_metric_value")
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            number.setStyleSheet("font-size: 27px; font-weight: 600;")
            label = QLabel(title, card)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            card_layout.addWidget(number)
            card_layout.addWidget(label)
            metrics.addWidget(card, 1)
        layout.addLayout(metrics)

        progress_heading = QLabel("Nächste Schritte", page)
        progress_heading.setObjectName("processing_next_steps_heading")
        layout.addWidget(progress_heading)
        progress = QLabel(
            ("✓ Bilder importiert" if counts.thermal_frames or counts.rgb_frames
             else "○ Bilder importieren")
            + "\n○ Vollständige Bildverarbeitung: Abschluss nicht nachgewiesen"
            + "\n○ Fachprüfung erst nach abgeschlossener Verarbeitung",
            page,
        )
        progress.setObjectName("processing_next_steps")
        progress.setWordWrap(True)
        progress.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(progress)

        if processing_run is None:
            run_text = "Noch kein vollständiger Verarbeitungslauf dokumentiert."
        elif processing_run.stale_inputs:
            run_text = (
                "Der Datenbestand wurde seit dem letzten Verarbeitungslauf geändert. "
                "Eine erneute vollständige Verarbeitung ist erforderlich."
            )
        elif processing_run.status == "running":
            run_text = (
                "Verarbeitungslauf begonnen; ein vollständiges Ergebnis "
                "ist noch nicht nachgewiesen."
            )
        elif processing_run.status == "cancelled":
            run_text = "Letzte Verarbeitung abgebrochen; kein vollständiges Ergebnis."
        elif processing_run.status == "failed":
            run_text = "Letzte Verarbeitung fehlgeschlagen; kein vollständiges Ergebnis."
        else:
            # A completed marker without worker-backed verification is not
            # sufficient evidence to enable the expert review.
            run_text = "Ein Abschlussmarker allein belegt keine geprüfte Verarbeitung."
        run_label = QLabel(run_text, page)
        run_label.setObjectName("processing_run_status")
        run_label.setWordWrap(True)
        run_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(run_label)

        check_images = QPushButton(
            "Importierte Originalbilder prüfen (nur lesend)", page,
        )
        check_images.setObjectName("processing_check_imported_files")
        check_images.setEnabled(
            callable(on_check_imported_files) and not image_check_running
            and not thermal_check_running and not thermal_stats_running
            and not rgb_sample_running and not rgb_overlay_running and counts.thermal_frames > 0
        )
        if check_images.isEnabled():
            check_images.clicked.connect(on_check_imported_files)
        layout.addWidget(check_images)

        if image_check_running:
            cancel_images = QPushButton("Dateiprüfung abbrechen", page)
            cancel_images.setObjectName("processing_cancel_imported_files")
            cancel_images.setEnabled(callable(on_cancel_imported_files))
            if cancel_images.isEnabled():
                cancel_images.clicked.connect(on_cancel_imported_files)
            layout.addWidget(cancel_images)
        check_status = QLabel(
            image_check_status or (
                "Prüft lokal Dateilesbarkeit und bekannte Import-Prüfsummen. "
                "Keine Bildanalyse, Temperaturkalibrierung oder Fachfreigabe."
            ), page,
        )
        check_status.setObjectName("processing_image_check_status")
        check_status.setTextFormat(Qt.TextFormat.PlainText)
        check_status.setWordWrap(True)
        layout.addWidget(check_status)

        # A separate technical check decodes the actual 16-bit APP3 raster,
        # unlike JPEG/MPO structural inspection. It never writes findings or
        # marks the full offline processing run as completed.
        check_raw = QPushButton(
            "Thermal-Rohdaten prüfen (nur lesend)", page,
        )
        check_raw.setObjectName("processing_check_thermal_raw")
        check_raw.setEnabled(
            callable(on_check_thermal_raw) and not thermal_check_running
            and not image_check_running and not thermal_stats_running
            and not rgb_sample_running and not rgb_overlay_running and counts.thermal_frames > 0
        )
        if check_raw.isEnabled():
            check_raw.clicked.connect(on_check_thermal_raw)
        layout.addWidget(check_raw)

        if thermal_check_running:
            cancel_raw = QPushButton("Thermal-Rohdatenprüfung abbrechen", page)
            cancel_raw.setObjectName("processing_cancel_thermal_raw")
            cancel_raw.setEnabled(callable(on_cancel_thermal_raw))
            if cancel_raw.isEnabled():
                cancel_raw.clicked.connect(on_cancel_thermal_raw)
            layout.addWidget(cancel_raw)
        raw_status = QLabel(
            thermal_check_status or (
                "Prüft die gespeicherten 16-Bit-Thermalrohwerte und "
                "Import-Prüfsummen. Keine Temperaturkalibrierung, "
                "Defektdiagnose oder Freigabe."
            ), page,
        )
        raw_status.setObjectName("processing_thermal_raw_status")
        raw_status.setTextFormat(Qt.TextFormat.PlainText)
        raw_status.setWordWrap(True)
        layout.addWidget(raw_status)

        # First quantitative per-image raw-sensor stage. No Celsius,
        # anomaly classification, persistence or workflow permission changes.
        analyze = QPushButton(
            "Thermal-Sensorrohwerte statistisch auswerten (nur lesend)", page,
        )
        analyze.setObjectName("processing_analyze_thermal_stats")
        analyze.setEnabled(
            callable(on_analyze_thermal_stats)
            and not thermal_stats_running and not image_check_running
            and not thermal_check_running and not rgb_sample_running
            and counts.thermal_frames > 0
        )
        if analyze.isEnabled():
            analyze.clicked.connect(on_analyze_thermal_stats)
        layout.addWidget(analyze)
        if thermal_stats_running:
            cancel_stats = QPushButton(
                "Thermalstatistik abbrechen", page,
            )
            cancel_stats.setObjectName("processing_cancel_thermal_stats")
            cancel_stats.setEnabled(callable(on_cancel_thermal_stats))
            if cancel_stats.isEnabled():
                cancel_stats.clicked.connect(on_cancel_thermal_stats)
            layout.addWidget(cancel_stats)
        stats_label = QLabel(
            thermal_stats_status or (
                "Berechnet Rohwertstatistiken pro Thermalbild nur aus "
                "verifizierten 16-Bit-Sensordaten. Keine °C-Werte, "
                "PV-Modulerkennung, Defektdiagnose oder Freigabe."
            ), page,
        )
        stats_label.setObjectName("processing_thermal_statistics_status")
        stats_label.setTextFormat(Qt.TextFormat.PlainText)
        stats_label.setWordWrap(True)
        layout.addWidget(stats_label)

        # Metadata prerequisite check is distinct from any detector output
        # and never verifies referenced image bytes itself.
        module_ready = QPushButton(
            "RGB-Eingaben für Modulerkennung prüfen (nur lesend)", page,
        )
        module_ready.setObjectName("processing_check_module_readiness")
        module_ready.setEnabled(
            callable(on_check_module_readiness) and counts.rgb_frames > 0
            and not image_check_running and not thermal_check_running
            and not thermal_stats_running and not rgb_sample_running
        )
        if module_ready.isEnabled():
            module_ready.clicked.connect(on_check_module_readiness)
        layout.addWidget(module_ready)
        module_info = QLabel(
            module_readiness_status or (
                "Prüft nur gespeicherte RGB-Bildmaße und eingetragene "
                "Import-Prüfsummen. Keine erneute Dateiprüfung, "
                "kein produktionsvalidierter Moduldetektor oder Fachfreigabe."
            ), page,
        )
        module_info.setObjectName("processing_module_readiness_status")
        module_info.setTextFormat(Qt.TextFormat.PlainText)
        module_info.setWordWrap(True)
        layout.addWidget(module_info)

        sample = QPushButton(
            "PV-Modulvorschläge prüfen (3 RGB-Bilder, nur lesend)", page,
        )
        sample.setObjectName("processing_sample_rgb_modules")
        sample.setEnabled(
            callable(on_sample_rgb_modules) and not rgb_sample_running
            and not image_check_running and not thermal_check_running
            and not thermal_stats_running and not rgb_overlay_running
            and counts.rgb_frames > 0
        )
        if sample.isEnabled():
            sample.clicked.connect(on_sample_rgb_modules)
        layout.addWidget(sample)
        if rgb_sample_running:
            cancel_sample = QPushButton("RGB-Erkennungstest abbrechen", page)
            cancel_sample.setObjectName("processing_cancel_rgb_modules")
            cancel_sample.setEnabled(callable(on_cancel_rgb_modules))
            if cancel_sample.isEnabled():
                cancel_sample.clicked.connect(on_cancel_rgb_modules)
            layout.addWidget(cancel_sample)
        sample_info = QLabel(
            rgb_sample_status or (
                "Unverbindliche Stichprobe: maximal 3 RGB-Bilder mit "
                "Strukturerkennung, Bildinhaltserkennung und der bereits "
                "entwickelten Cadence-Rasterprüfung. Nur Modulvorschläge, "
                "keine bestätigten PV-Module. Keine Speicherung oder Fachfreigabe."
            ), page,
        )
        sample_info.setObjectName("processing_rgb_module_sample_status")
        sample_info.setTextFormat(Qt.TextFormat.PlainText)
        sample_info.setWordWrap(True)
        layout.addWidget(sample_info)

        # Explicit local preview of only the first three SHA-verified RGB frames.
        # The selector is just a 0-based sample index, never a user file path.
        overlay_selector = QComboBox(page)
        overlay_selector.setObjectName("processing_rgb_overlay_selector")
        for idx in range(min(3, counts.rgb_frames)):
            overlay_selector.addItem(f"RGB-Testbild {idx + 1}", idx)
        overlay_selector.setEnabled(not rgb_overlay_running)
        layout.addWidget(overlay_selector)

        overlay_button = QPushButton(
            "RGB-Modulvorschläge farbig anzeigen (nur lesend)", page,
        )
        overlay_button.setObjectName("processing_preview_rgb_overlay")
        overlay_button.setEnabled(
            callable(on_preview_rgb_overlay)
            and counts.rgb_frames > 0
            and not rgb_overlay_running and not rgb_sample_running
            and not image_check_running and not thermal_check_running
            and not thermal_stats_running
        )
        if overlay_button.isEnabled():
            overlay_button.clicked.connect(
                lambda checked=False: on_preview_rgb_overlay(
                    overlay_selector.currentIndex(),
                )
            )
        layout.addWidget(overlay_button)
        if rgb_overlay_running:
            cancel_overlay = QPushButton("RGB-Bildvorschau abbrechen", page)
            cancel_overlay.setObjectName("processing_cancel_rgb_overlay")
            cancel_overlay.setEnabled(callable(on_cancel_rgb_overlay))
            if cancel_overlay.isEnabled():
                cancel_overlay.clicked.connect(on_cancel_rgb_overlay)
            layout.addWidget(cancel_overlay)
        overlay_info = QLabel(
            rgb_overlay_status or (
                "Farbliche Überlagerung auf einem der ersten drei importierten "
                "RGB-Bilder. Zeigt nur unverbindliche Detektorvorschläge in "
                "einem lokalen Fenster, ohne Originale oder Datenbank zu ändern."
            ), page,
        )
        overlay_info.setObjectName("processing_rgb_overlay_status")
        overlay_info.setTextFormat(Qt.TextFormat.PlainText)
        overlay_info.setWordWrap(True)
        layout.addWidget(overlay_info)

        details_toggle = QPushButton("Technische Details anzeigen", page)
        details_toggle.setObjectName("processing_details_toggle")
        details_toggle.setCheckable(True)
        layout.addWidget(details_toggle)
        details = QWidget(content)
        details.setObjectName("processing_details_panel")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(10)
        evidence = QLabel(
            "Gespeicherte Daten (nur lesend):\n"
            f"RGB-Bilder: {counts.rgb_frames} · Thermalbilder: {counts.thermal_frames}\n"
            f"RGB/Thermal-Paare: {counts.image_pairs} · PV-Module: {counts.pv_modules}\n"
            f"Befundkandidaten: {counts.findings} · Ungeprüft: {counts.unreviewed_findings}\n"
            f"Fachlich bestätigt: {counts.confirmed_findings} · "
            f"Validierte Celsiusbefunde: {counts.calibrated_findings}",
            page,
        )
        evidence.setObjectName("processing_persisted_evidence")
        evidence.setTextFormat(Qt.TextFormat.PlainText)
        evidence.setWordWrap(True)
        evidence.setAccessibleDescription(
            "Zahlen aus SQLite; keine Aussage über fertig verarbeitete Bilder."
        )
        details_layout.addWidget(evidence)

        pair_audit = getattr(overview, "pair_audit", None)
        if pair_audit is not None:
            evidence_label = QLabel(
                "Technische Bildpaar-Prüfung (nur Aufnahmemetadaten):\n"
                f"Gespeicherte Bildpaare: {pair_audit.pairs_recorded} · "
                f"Mit aktueller Zuordnungsregel nachvollziehbar: "
                f"{pair_audit.supported_by_current_rules}\n"
                f"Erneut zu prüfen: {pair_audit.require_review} · "
                f"RGB ohne Paar: {pair_audit.unmatched_rgb} · "
                f"Thermal ohne Paar: {pair_audit.unmatched_thermal}\n"
                f"Übereinstimmende Bildnummer: {pair_audit.with_matching_sequence} · "
                f"Zeitnähe: {pair_audit.with_close_time} · "
                f"GPS-Nähe: {pair_audit.with_close_position}",
                page,
            )
            evidence_label.setObjectName("processing_pair_evidence")
            evidence_label.setTextFormat(Qt.TextFormat.PlainText)
            evidence_label.setWordWrap(True)
            evidence_label.setAccessibleDescription(
                "Schreibgeschützte technische Prüfsummen aus gespeicherten "
                "Paaren, ohne Dateinamen, Zeitstempel oder GPS-Koordinaten."
            )
            details_layout.addWidget(evidence_label)
            status_text = (
                "Mindestens eine gespeicherte Zuordnung erfüllt die aktuellen "
                "Metadatenkriterien nicht. Bitte technisch prüfen; keine "
                "automatische Reparatur."
                if pair_audit.require_review else
                "Die gespeicherten Paarungen sind anhand der "
                "Aufnahmemetadaten nachvollziehbar. Das beweist keine "
                "pixelgenaue RGB-/Thermalüberlagerung."
            )
            status = QLabel(status_text, page)
            status.setObjectName("processing_pair_evidence_status")
            status.setTextFormat(Qt.TextFormat.PlainText)
            status.setWordWrap(True)
            details_layout.addWidget(status)

        processing_status = QLabel(
            "Verarbeitung gemäß Projektstatus grundsätzlich zulässig; "
            "hier noch kein automatischer Verarbeitungsstart."
            if overview.process.allowed
            else "Verarbeitung gesperrt: " + "; ".join(overview.process.blockers),
            page,
        )
        processing_status.setObjectName("processing_workflow_status")
        processing_status.setWordWrap(True)
        processing_status.setTextFormat(Qt.TextFormat.PlainText)
        details_layout.addWidget(processing_status)

        review_status = QLabel(
            "Fachprüfung laut bisherigem Workflow technisch erreichbar; "
            "ein vollständiger Verarbeitungslauf wurde hier noch nicht nachgewiesen."
            if overview.review.allowed
            else "Fachprüfung gesperrt: " + "; ".join(overview.review.blockers),
            page,
        )
        review_status.setObjectName("processing_review_status")
        review_status.setWordWrap(True)
        review_status.setTextFormat(Qt.TextFormat.PlainText)
        details_layout.addWidget(review_status)
        layout.addWidget(details)
        details_toggle.toggled.connect(details.setVisible)
        details.setVisible(False)

    # The expert tool is deliberately separate from the introductory workflow.
    # It consumes a small local control-point JSON, NOT original image files.
    advanced = QPushButton("Erweitert: Kontrollpunktprüfung anzeigen", page)
    advanced.setObjectName("processing_registration_toggle")
    advanced.setCheckable(True)
    layout.addWidget(advanced)
    expert = QWidget(page)
    expert.setObjectName("processing_registration_panel")
    expert_layout = QVBoxLayout(expert)
    registration_help = QLabel(
        "Nur für fachkundig erstellte RGB-/Thermal-Kontrollpunkte. "
        "Die Homografie wird mit getrennten Anpassungs- und Kontrollpunkten "
        "bewertet. Keine automatische Bildüberlagerung, Modulzuordnung, "
        "Kunden- oder Berichtsfreigabe.",
        expert,
    )
    registration_help.setWordWrap(True)
    expert_layout.addWidget(registration_help)
    action = QPushButton("Lokale Kontrollpunkt-Datei prüfen (JSON)", expert)
    action.setObjectName("processing_check_registration_button")
    action.setEnabled(
        on_check_registration is not None
        and overview is not None
        and overview.summary.image_pairs > 0
    )
    if action.isEnabled():
        def request_control_file():
            path = (
                choose_control_file() if choose_control_file is not None else
                QFileDialog.getOpenFileName(
                    page, "Lokale RGB-/Thermal-Kontrollpunkte wählen",
                    "", "JSON (*.json)",
                )[0]
            )
            if path:
                on_check_registration(path)
        action.clicked.connect(request_control_file)
    expert_layout.addWidget(action)
    if registration_check_status is not None:
        status = QLabel(registration_check_status, expert)
        status.setObjectName("processing_registration_result")
        status.setWordWrap(True)
        status.setTextFormat(Qt.TextFormat.PlainText)
        expert_layout.addWidget(status)
    layout.addWidget(expert)
    advanced.toggled.connect(expert.setVisible)
    expert.setVisible(registration_check_status is not None)

    disclaimer = QLabel(
        "Importierte Bilder bedeuten keine abgeschlossene Analyse. "
        "Befundkandidaten sind keine bestätigten Defekte. "
        "Keine automatische KI-Freigabe, keine Temperaturkalibrierung "
        "und kein Berichtsexport auf dieser Seite.",
        page,
    )
    disclaimer.setObjectName("processing_safety_notice")
    disclaimer.setWordWrap(True)
    layout.addWidget(disclaimer)

    refresh = QPushButton("Gespeicherten Projektstand aktualisieren", page)
    refresh.setObjectName("refresh_processing_button")
    refresh.setEnabled(current_project_id is not None and on_refresh is not None)
    if on_refresh is not None and current_project_id is not None:
        refresh.clicked.connect(on_refresh)
    else:
        refresh.setAccessibleDescription(
            "Nur mit einem geöffneten Projekt und angebundenem Application Service verfügbar."
        )
    layout.addWidget(refresh)
    layout.addStretch(1)
    return page
