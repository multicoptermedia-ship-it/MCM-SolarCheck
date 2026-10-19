"""Offline PV plant overview from project-scoped local module observations.

This is an evidence inventory, not a surveyed site plan or a validated
orthophoto. Page size and aggregation are controlled by the application service.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

COLUMN_HEADINGS = (
    "Modulbeobachtung", "Bild", "Detektor", "Konfidenz",
    "ID-Vorschlag", "Identitätsstatus", "Befunde",
    "Ungeprüft", "Bestätigt", "Verworfen", "Unklar",
)


def make_plant_overview_page(
    parent=None, *, current_project_id=None, overview=None,
    on_refresh=None, on_page_requested=None,
):
    """Display bounded, persisted evidence without any inferred GIS position."""
    page = QWidget(parent)
    page.setObjectName("plant_overview_page")
    layout = QVBoxLayout(page)
    title = QLabel("Anlagenübersicht – vorhandene Modulbeobachtungen", page)
    title.setObjectName("page_heading")
    layout.addWidget(title)

    context = QLabel(
        f"Aktives Projekt: {current_project_id}"
        if current_project_id is not None
        else "Kein aktives Projekt ausgewählt.",
        page,
    )
    context.setObjectName("plant_project_context")
    context.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(context)

    if overview is None:
        state = QLabel(
            "Keine gespeicherten Moduldaten verfügbar. "
            "Bitte ein Offline-Projekt öffnen.",
            page,
        )
        state.setObjectName("plant_empty_state")
        state.setWordWrap(True)
        layout.addWidget(state)
    else:
        state = QLabel(
            "Gespeicherte Modulbeobachtungen: "
            f"{overview.summary.pv_modules} · "
            f"Befundkandidaten: {overview.summary.findings} · "
            "Befunde ohne passende Modulbeobachtung: "
            f"{overview.unassigned_findings}",
            page,
        )
        state.setObjectName("plant_evidence_summary")
        state.setTextFormat(Qt.TextFormat.PlainText)
        state.setWordWrap(True)
        layout.addWidget(state)

        review = QLabel(
            f"Ungeprüft: {overview.summary.unreviewed_findings} · "
            f"Bestätigt: {overview.summary.confirmed_findings} · "
            f"Verworfen: {overview.summary.rejected_findings} · "
            f"Unklar: {overview.summary.unclear_findings}",
            page,
        )
        review.setObjectName("plant_review_summary")
        layout.addWidget(review)

    table = QTableWidget(page)
    table.setObjectName("plant_modules_table")
    table.setColumnCount(len(COLUMN_HEADINGS))
    table.setHorizontalHeaderLabels(COLUMN_HEADINGS)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSortingEnabled(False)
    table.setAccessibleDescription(
        "Lesende Übersicht lokaler Modulbeobachtungen. "
        "Gespeicherte geometrische ID-Vorschläge sind nicht vermessungstechnisch bestätigt."
    )
    modules = overview.modules if overview is not None else ()
    table.setRowCount(len(modules))
    for row_index, module in enumerate(modules):
        identity = module.proposed_physical_id or "nicht zugeordnet"
        identity_status = (
            f"{module.identity_status} (algorithmisch)"
            if module.identity_status else "nicht belegt"
        )
        values = (
            module.module_id,
            module.frame_id,
            module.detector,
            ("—" if module.detection_confidence is None
             else f"{module.detection_confidence:.3f}"),
            identity,
            identity_status,
            str(module.findings), str(module.unreviewed),
            str(module.confirmed), str(module.rejected), str(module.unclear),
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row_index, column, item)
    layout.addWidget(table)

    navigation = QHBoxLayout()
    previous = QPushButton("Vorherige Module", page)
    previous.setObjectName("plant_previous_page")
    next_page = QPushButton("Weitere Module", page)
    next_page.setObjectName("plant_next_page")
    count = QLabel("", page)
    count.setObjectName("plant_page_status")

    enabled = (
        current_project_id is not None and overview is not None
        and on_page_requested is not None
    )
    offset = overview.offset if overview is not None else 0
    limit = overview.limit if overview is not None else 100
    total = overview.summary.pv_modules if overview is not None else 0
    count.setText(
        f"Modulbeobachtungen {offset + 1}–{offset + len(modules)} von {total}"
        if modules else f"Keine Modulbeobachtungen auf dieser Seite ({total} insgesamt)"
    )
    previous.setEnabled(bool(enabled and offset > 0))
    next_page.setEnabled(bool(enabled and offset + len(modules) < total))
    if enabled:
        previous.clicked.connect(
            lambda: on_page_requested(max(0, offset - limit))
        )
        next_page.clicked.connect(
            lambda: on_page_requested(offset + limit)
        )
    navigation.addWidget(previous)
    navigation.addWidget(count)
    navigation.addWidget(next_page)
    layout.addLayout(navigation)

    refresh = QPushButton("Anlagenübersicht aktualisieren", page)
    refresh.setObjectName("refresh_plant_overview")
    refresh.setEnabled(
        current_project_id is not None and on_refresh is not None
    )
    if on_refresh is not None and current_project_id is not None:
        refresh.clicked.connect(on_refresh)
    layout.addWidget(refresh)

    disclaimer = QLabel(
        "Angezeigt werden lokale Bild-/Detektorbeobachtungen, keine gezählten "
        "einzigartigen physischen PV-Module. Algorithmische Identitätsvorschläge "
        "sind nicht unabhängig validiert. Ohne nachgewiesene Georeferenzierung "
        "wird weder ein Lageplan noch ein metrisches Orthofoto dargestellt. "
        "Ungeprüfte Befunde gelten nicht als bestätigte Defekte.",
        page,
    )
    disclaimer.setObjectName("plant_overview_safety_notice")
    disclaimer.setTextFormat(Qt.TextFormat.PlainText)
    disclaimer.setWordWrap(True)
    layout.addWidget(disclaimer)
    return page
