"""Offline export of a freshly revalidated draft report; no automatic release."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget


def make_export_page(
    parent=None, *, current_project_id=None, availability=None,
    draft=None, on_export=None, last_status=None,
):
    page = QWidget(parent)
    page.setObjectName("export_page")
    layout = QVBoxLayout(page)
    heading = QLabel("Export – lokalen Berichtsentwurf speichern", page)
    heading.setObjectName("page_heading")
    layout.addWidget(heading)
    context = QLabel(
        f"Aktives Projekt: {current_project_id}"
        if current_project_id is not None else "Kein Projekt ausgewählt.",
        page,
    )
    context.setObjectName("export_project_context")
    context.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(context)

    reasons = []
    if availability is None:
        reasons.append("Offline-Exportservice nicht verfügbar")
    elif not availability.allowed:
        reasons.extend(availability.blockers)
    if draft is None or draft.project_id != current_project_id:
        reasons.append("Zuerst für dieses Projekt einen Entwurf vorbereiten")
    elif draft.release_status != "draft":
        reasons.append("Nur Entwürfe dürfen hier gespeichert werden")
    state = QLabel(
        "Ein vorbereiteter Entwurf ist verfügbar; die Freigaben werden "
        "vor jedem Export erneut geprüft."
        if not reasons else "Export gesperrt: " + "; ".join(reasons),
        page,
    )
    state.setObjectName("export_readiness_status")
    state.setTextFormat(Qt.TextFormat.PlainText)
    state.setWordWrap(True)
    layout.addWidget(state)

    formats = QComboBox(page)
    formats.setObjectName("draft_export_format")
    formats.addItem("PDF (.pdf)", "pdf")
    formats.addItem("ODT (.odt)", "odt")
    formats.addItem("DOCX (.docx)", "docx")
    layout.addWidget(formats)
    action = QPushButton("Berichtsentwurf lokal speichern …", page)
    action.setObjectName("export_report_draft")
    action.setEnabled(
        current_project_id is not None and on_export is not None and not reasons
    )
    if on_export is not None:
        action.clicked.connect(
            lambda: on_export(formats.currentData()) if action.isEnabled() else None
        )
    layout.addWidget(action)

    if last_status:
        status = QLabel(last_status, page)
        status.setObjectName("report_export_status")
        status.setTextFormat(Qt.TextFormat.PlainText)
        status.setWordWrap(True)
        layout.addWidget(status)

    caution = QLabel(
        "Der exportierte Bericht trägt ausdrücklich den Freigabestatus 'draft'. "
        "Vorhandene Dateien werden nicht überschrieben. "
        "Dieser Schritt ist keine fachliche Veröffentlichung.",
        page,
    )
    caution.setObjectName("export_draft_safety_notice")
    caution.setWordWrap(True)
    layout.addWidget(caution)
    layout.addStretch(1)
    return page
