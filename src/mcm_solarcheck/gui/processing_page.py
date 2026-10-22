"""Read-only Windows processing workspace from authoritative project evidence."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


def make_processing_page(
    parent=None, *, current_project_id=None, overview=None, on_refresh=None,
):
    """Show persisted image/analysis facts without implying processing was run."""
    page = QWidget(parent)
    page.setObjectName("processing_page")
    layout = QVBoxLayout(page)

    heading = QLabel("Verarbeitung – gespeicherter Projektstand", page)
    heading.setObjectName("page_heading")
    layout.addWidget(heading)

    project = QLabel(
        f"Aktives Projekt: {current_project_id}"
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
        layout.addWidget(evidence)

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
            layout.addWidget(evidence_label)
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
            layout.addWidget(status)

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
        layout.addWidget(processing_status)

        review_status = QLabel(
            "Fachprüfung gemäß Projektstatus zugänglich; "
            "Befunde bleiben bis zur Einzelentscheidung ungeprüft."
            if overview.review.allowed
            else "Fachprüfung gesperrt: " + "; ".join(overview.review.blockers),
            page,
        )
        review_status.setObjectName("processing_review_status")
        review_status.setWordWrap(True)
        review_status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(review_status)

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
