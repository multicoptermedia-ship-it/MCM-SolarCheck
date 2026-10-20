"""Read-only, bounded display of already-persisted expert audit events."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QVBoxLayout, QWidget,
)

from mcm_solarcheck.storage.queries import ExpertReviewHistory

HISTORY_PAGE_SIZE = 25
NOTE_DISPLAY_LIMIT = 4096


def make_review_history_panel(
    parent=None, *, history: ExpertReviewHistory | None = None,
    on_page_requested=None,
) -> QWidget:
    """Separate audit history from the editable pending-candidate decision form."""
    panel = QWidget(parent)
    panel.setObjectName("review_history_panel")
    layout = QVBoxLayout(panel)
    header = QLabel("Bereits dokumentierte Fachprüfungen (nur lesend)", panel)
    header.setObjectName("review_history_heading")
    header.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(header)

    total = history.total if history is not None else 0
    offset = history.offset if history is not None else 0
    entries = history.entries if history is not None else ()
    count = QLabel(
        f"Dokumentierte Entscheidungen: {total} · "
        f"Angezeigt: {len(entries)} (maximal {HISTORY_PAGE_SIZE})", panel,
    )
    count.setObjectName("review_history_count")
    count.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(count)

    listing = QListWidget(panel)
    listing.setObjectName("review_history_events")
    listing.setAccessibleDescription(
        "Nur tatsächlich gespeicherte, ältere Prüferentscheidungen des "
        "aktiven Offline-Projekts. Auswahl ist ausschließlich lesend."
    )
    listing.setMaximumHeight(155)
    for event in entries:
        item = QListWidgetItem(
            f"{event.finding_id} · {event.status} · "
            f"{event.reviewer} · {event.reviewed_at_utc}"
        )
        listing.addItem(item)
    layout.addWidget(listing)
    details = QLabel(
        "Bitte eine dokumentierte Entscheidung auswählen.", panel,
    )
    details.setObjectName("review_history_selected")
    details.setTextFormat(Qt.TextFormat.PlainText)
    details.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    details.setWordWrap(True)
    layout.addWidget(details)

    def select_event():
        row = listing.currentRow()
        if not 0 <= row < len(entries):
            details.setText("Bitte eine dokumentierte Entscheidung auswählen.")
            return
        event = entries[row]
        original_note = event.note
        if original_note is None:
            note = "keine Prüfnotiz"
        elif len(original_note) > NOTE_DISPLAY_LIMIT:
            note = (
                original_note[:NOTE_DISPLAY_LIMIT]
                + " … (Anzeige gekürzt; gespeicherter Audit unverändert)"
            )
        else:
            note = original_note
        details.setText(
            f"Befund: {event.finding_id}\n"
            f"Status bei dieser Entscheidung: {event.status}\n"
            f"Prüfer: {event.reviewer}\n"
            f"Zeitpunkt (UTC): {event.reviewed_at_utc}\n"
            f"Thermalbild: {event.thermal_frame_id}\n"
            f"Modul: {event.module_id or 'nicht zugeordnet'}\n"
            f"Prüfnotiz: {note}"
        )

    listing.itemSelectionChanged.connect(select_event)
    navigation = QHBoxLayout()
    back = QPushButton("Frühere Seite der Historie", panel)
    back.setObjectName("review_history_previous")
    forward = QPushButton("Weitere ältere Entscheidungen", panel)
    forward.setObjectName("review_history_next")
    position = QLabel(
        f"Entscheidungen {offset + 1}–{offset + len(entries)} von {total}"
        if entries else f"Keine Einträge auf dieser Seite ({total} gesamt)",
        panel,
    )
    position.setObjectName("review_history_page_status")
    position.setTextFormat(Qt.TextFormat.PlainText)
    back.setEnabled(on_page_requested is not None and offset > 0)
    forward.setEnabled(
        on_page_requested is not None and offset + len(entries) < total
        and len(entries) > 0
    )
    if on_page_requested is not None:
        back.clicked.connect(
            lambda checked=False: on_page_requested(
                max(0, offset - HISTORY_PAGE_SIZE),
            )
        )
        forward.clicked.connect(
            lambda checked=False: on_page_requested(
                offset + HISTORY_PAGE_SIZE,
            )
        )
    navigation.addWidget(back)
    navigation.addWidget(position, 1)
    navigation.addWidget(forward)
    layout.addLayout(navigation)
    return panel
