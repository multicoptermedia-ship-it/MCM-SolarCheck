"""Read-only Windows processing workspace from authoritative project evidence."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)


def make_processing_page(
    parent=None, *, current_project_id=None, overview=None, on_refresh=None,
    on_check_registration=None, registration_check_status=None, choose_control_file=None,
    project_label=None,
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
