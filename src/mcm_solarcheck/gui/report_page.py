"""Desktop report preparation view; no generated file and no release approval."""
from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


def parse_inspection_start_utc(text: str) -> datetime:
    """Require an explicitly recorded, offset-aware UTC inspection timestamp."""
    try:
        value = datetime.fromisoformat(text.strip())
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Prüfbeginn als ISO-8601 UTC eingeben") from exc
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("Prüfbeginn muss UTC mit +00:00 oder Z sein")
    return value


def make_report_page(
    parent=None, *, current_project_id=None, availability=None,
    profile=None, draft=None, on_prepare=None, last_status=None,
):
    page = QWidget(parent)
    page.setObjectName("report_page")
    layout = QVBoxLayout(page)
    heading = QLabel("Bericht – nicht freigegebenen Entwurf vorbereiten", page)
    heading.setObjectName("page_heading")
    layout.addWidget(heading)

    context = QLabel(
        f"Aktives Projekt: {current_project_id}"
        if current_project_id is not None else "Kein Projekt ausgewählt.",
        page,
    )
    context.setObjectName("report_project_context")
    context.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(context)

    blocked = []
    if availability is None:
        blocked.append("Kein Offline-Berichtsservice ausgewählt")
    elif not availability.allowed:
        blocked.extend(availability.blockers)
    if profile is None:
        blocked.append("Projektstammdaten fehlen")
    state = QLabel(
        "Berichtsentwurf kann auf Basis gespeicherter Daten vorbereitet werden."
        if not blocked else "Berichtsvorbereitung gesperrt: " + "; ".join(blocked),
        page,
    )
    state.setObjectName("report_readiness_status")
    state.setTextFormat(Qt.TextFormat.PlainText)
    state.setWordWrap(True)
    layout.addWidget(state)

    report_id = QLineEdit(page)
    report_id.setObjectName("report_draft_id")
    report_id.setPlaceholderText("Eindeutige Bericht-ID (Pflichtfeld)")
    layout.addWidget(report_id)
    started = QLineEdit(page)
    started.setObjectName("report_inspection_started_utc")
    started.setPlaceholderText("Tatsächlicher Prüfbeginn in UTC, z. B. 2026-10-19T12:00:00+00:00")
    layout.addWidget(started)

    prepare = QPushButton("Berichtsentwurf vorbereiten", page)
    prepare.setObjectName("prepare_report_draft")
    layout.addWidget(prepare)

    def update_prepare():
        valid = False
        try:
            parse_inspection_start_utc(started.text())
            valid = True
        except ValueError:
            pass
        prepare.setEnabled(bool(
            current_project_id is not None and on_prepare is not None
            and not blocked and report_id.text().strip() and valid
        ))

    def prepare_report():
        if prepare.isEnabled():
            on_prepare(
                report_id.text().strip(),
                parse_inspection_start_utc(started.text()),
            )

    report_id.textChanged.connect(update_prepare)
    started.textChanged.connect(update_prepare)
    if on_prepare is not None:
        prepare.clicked.connect(prepare_report)
    update_prepare()

    if draft is not None:
        summary = QLabel(
            f"Vorbereiteter Entwurf: {draft.report_id} · "
            f"Freigabestatus: {draft.release_status} · "
            f"Anlage: {draft.site_name} · "
            f"Dokumentierte Detailbefunde: {len(draft.details)}. "
            "Zum Speichern bitte den Bereich Export öffnen.",
            page,
        )
        summary.setObjectName("report_draft_preview")
        summary.setTextFormat(Qt.TextFormat.PlainText)
        summary.setWordWrap(True)
        layout.addWidget(summary)
    if last_status:
        result = QLabel(last_status, page)
        result.setObjectName("report_draft_status")
        result.setTextFormat(Qt.TextFormat.PlainText)
        result.setWordWrap(True)
        layout.addWidget(result)

    caution = QLabel(
        "Nur ein Berichtsentwurf: keine Kundenfreigabe, keine zusätzliche "
        "Temperaturkalibrierung und keine automatische Normkonformitäts- "
        "oder Orthofoto-Bestätigung. Prüfbeginn muss der tatsächliche "
        "Aufnahmezeitpunkt sein.",
        page,
    )
    caution.setObjectName("report_draft_safety_notice")
    caution.setWordWrap(True)
    layout.addWidget(caution)
    layout.addStretch(1)
    return page
