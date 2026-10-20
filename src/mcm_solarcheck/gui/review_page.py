"""Windows expert review workspace backed by persisted, unreviewed project findings."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from mcm_solarcheck.review.findings import ReviewStatus
from mcm_solarcheck.gui.review_evidence import review_evidence_text
from mcm_solarcheck.services.review_image_preview import ReviewImageEvidence

MAX_REVIEW_PAGE_FINDINGS = 50


def make_review_page(
    parent=None, *, current_project_id=None, overview=None, pending=(),
    on_review=None, on_refresh=None, last_review_status=None,
    offset=0, on_page_requested=None, on_preview_images=None,
):
    """Present expert choices; never classify or approve a report automatically."""
    page = QWidget(parent)
    page.setObjectName("review_page")
    layout = QVBoxLayout(page)

    title = QLabel("Fachprüfung – ungeprüfte Befunde", page)
    title.setObjectName("page_heading")
    layout.addWidget(title)
    project = QLabel(
        f"Aktives Projekt: {current_project_id}"
        if current_project_id is not None else "Kein aktives Projekt ausgewählt.",
        page,
    )
    project.setObjectName("review_project_context")
    project.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(project)

    if overview is None:
        state_label = QLabel(
            "Kein Projekt mit angeschlossenem Review-Service ausgewählt.", page,
        )
        state_label.setObjectName("review_workflow_status")
        layout.addWidget(state_label)
    else:
        allowed = overview.review.allowed
        state_label = QLabel(
            "Fachprüfung laut gespeicherter Projektdaten möglich."
            if allowed else "Fachprüfung gesperrt: "
            + "; ".join(overview.review.blockers),
            page,
        )
        state_label.setObjectName("review_workflow_status")
        state_label.setWordWrap(True)
        state_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(state_label)

        count = QLabel(
            f"Offene Befunde: {overview.summary.unreviewed_findings} · "
            f"Angezeigt: {len(pending)} (maximal {MAX_REVIEW_PAGE_FINDINGS})",
            page,
        )
        count.setObjectName("review_pending_count")
        layout.addWidget(count)

    finding_list = QListWidget(page)
    finding_list.setObjectName("pending_review_findings")
    finding_list.setAccessibleDescription(
        "Nur aktuell gespeicherte, noch nicht fachlich entschiedene Befunde."
    )
    records = {finding.finding_id: finding for finding in pending}
    for finding in pending:
        module = finding.module_id or "nicht zugeordnet"
        item = QListWidgetItem(
            f"{finding.finding_id} · {finding.finding_type} · "
            f"Thermalbild {finding.thermal_frame_id} · Modul {module}"
        )
        item.setData(Qt.ItemDataRole.UserRole, finding.finding_id)
        finding_list.addItem(item)
    layout.addWidget(finding_list)

    evidence = QLabel(
        "Bitte einen offenen Befund auswählen, um die gespeicherten "
        "Einzelnachweise zu sehen.",
        page,
    )
    evidence.setObjectName("review_selected_evidence")
    evidence.setTextFormat(Qt.TextFormat.PlainText)
    evidence.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    evidence.setWordWrap(True)
    evidence.setAccessibleDescription(
        "Nur gespeicherte Einzelbefunddaten; keine automatische Kalibrierung, "
        "Bildvalidierung, Diagnose oder Freigabe."
    )
    layout.addWidget(evidence)

    def update_evidence():
        item = finding_list.currentItem()
        record = (
            records.get(item.data(Qt.ItemDataRole.UserRole))
            if item is not None else None
        )
        evidence.setText(
            review_evidence_text(record)
            if record is not None else
            "Bitte einen offenen Befund auswählen, um die gespeicherten "
            "Einzelnachweise zu sehen."
        )

    finding_list.itemSelectionChanged.connect(update_evidence)

    preview_button = QPushButton(
        "RGB-/Thermal-Vorschau aus lokalem Flugordner öffnen …", page,
    )
    preview_button.setObjectName("review_preview_images_button")
    preview_button.setEnabled(False)
    layout.addWidget(preview_button)
    preview_status = QLabel(
        "Bildvorschau nur nach bewusst gewähltem lokalem Flugordner. "
        "Keine Originalbild-Verifizierung, Thermokalibrierung oder Diagnose.",
        page,
    )
    preview_status.setObjectName("review_preview_images_status")
    preview_status.setTextFormat(Qt.TextFormat.PlainText)
    preview_status.setWordWrap(True)
    layout.addWidget(preview_status)
    preview_row = QHBoxLayout()
    thermal_preview = QLabel("Thermal: kein Bild geladen", page)
    thermal_preview.setObjectName("review_preview_thermal")
    rgb_preview = QLabel("RGB: kein Bild geladen", page)
    rgb_preview.setObjectName("review_preview_rgb")
    for display in (thermal_preview, rgb_preview):
        display.setTextFormat(Qt.TextFormat.PlainText)
        display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        display.setMinimumHeight(150)
        display.setWordWrap(True)
        display.setAccessibleDescription(
            "Sichtbild-Vorschau, keine Temperaturmessung oder geprüfte "
            "räumliche Zuordnung; ausschließlich lokale Originaldateien."
        )
        preview_row.addWidget(display, 1)
    layout.addLayout(preview_row)

    integrity_row = QHBoxLayout()
    thermal_integrity = QLabel("", page)
    thermal_integrity.setObjectName("review_preview_thermal_integrity")
    rgb_integrity = QLabel("", page)
    rgb_integrity.setObjectName("review_preview_rgb_integrity")
    for label in (thermal_integrity, rgb_integrity):
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        integrity_row.addWidget(label, 1)
    layout.addLayout(integrity_row)

    locator_row = QHBoxLayout()
    thermal_locator = QLabel("", page)
    thermal_locator.setObjectName("review_preview_thermal_locator")
    rgb_locator = QLabel("", page)
    rgb_locator.setObjectName("review_preview_rgb_locator")
    for label in (thermal_locator, rgb_locator):
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        locator_row.addWidget(label, 1)
    layout.addLayout(locator_row)

    locator_messages = {
        "marked": (
            "Grüne Zielmarke: gespeicherte Pixelposition im unverdrehten "
            "Sichtbild gleicher Abmessungen. Nur Positionshilfe, keine "
            "radiometrische Zuordnung oder Defektdiagnose."
        ),
        "different_geometry": (
            "Keine Zielmarke: Bild- und gespeicherte Pixelabmessungen "
            "stimmen nicht exakt überein."
        ),
        "orientation": (
            "Keine Zielmarke: Bild enthält eine EXIF-Drehorientierung."
        ),
        "outside": (
            "Keine Zielmarke: gespeicherte Pixelposition ist ungültig "
            "oder liegt außerhalb des Bildes."
        ),
        "unvalidated": (
            "Keine RGB-Zielmarke: geometrische Bildverknüpfung "
            "ist nicht als validiert gespeichert."
        ),
        "unavailable": "Keine Zielmarke ohne verfügbaren Bildnachweis.",
    }

    integrity_messages = {
        "verified": (
            "SHA-256 stimmt mit der beim Import gespeicherten Datei-Prüfsumme "
            "überein (keine Garantie für Bildherkunft oder Befund)."
        ),
        "unverified": (
            "Keine Import-Prüfsumme vorhanden: Bildidentität nicht überprüfbar."
        ),
        "mismatch": (
            "Abweichende Import-Prüfsumme: Bild wird nicht angezeigt."
        ),
        "unavailable": "Bildnachweis nicht verfügbar oder nicht verknüpft.",
    }

    def reset_image_preview():
        thermal_preview.clear()
        thermal_preview.setText("Thermal: kein Bild geladen")
        rgb_preview.clear()
        rgb_preview.setText("RGB: kein Bild geladen")
        thermal_integrity.setText("")
        rgb_integrity.setText("")
        thermal_locator.setText("")
        rgb_locator.setText("")
        preview_status.setText(
            "Für die Bildvorschau bitte ausdrücklich einen lokalen Flugordner wählen."
        )
        preview_button.setEnabled(bool(
            on_preview_images is not None and finding_list.currentItem() is not None
        ))

    def load_preview():
        selected = finding_list.currentItem()
        if selected is None or not preview_button.isEnabled():
            return
        finding_id = selected.data(Qt.ItemDataRole.UserRole)
        folder = QFileDialog.getExistingDirectory(
            page, "Lokalen Flugordner mit RGB-/Thermalbildern auswählen",
        )
        if not folder:
            return
        # A modal dialog may change selection or active project while open.
        if finding_list.currentItem() is not selected:
            return
        result = on_preview_images(finding_id, folder)
        if result is None or finding_list.currentItem() is not selected:
            return
        if isinstance(result, ReviewImageEvidence):
            payloads = (result.thermal_png, result.rgb_png)
            statuses = (result.thermal_integrity, result.rgb_integrity)
            marker_statuses = (result.thermal_marker, result.rgb_marker)
        else:
            # Legacy/local test callbacks cannot claim a verified file hash.
            payloads = result
            statuses = tuple(
                "unverified" if payload is not None else "unavailable"
                for payload in payloads
            )
            marker_statuses = ("unavailable", "unavailable")
        for payload, target, prefix in zip(
            payloads, (thermal_preview, rgb_preview), ("Thermal", "RGB"),
        ):
            target.clear()
            frame = QPixmap()
            if payload is not None and frame.loadFromData(payload, "PNG"):
                target.setPixmap(frame.scaled(
                    320, 210, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            else:
                target.setText(prefix + ": Bild nicht verfügbar")
        for integrity_label, state in zip(
            (thermal_integrity, rgb_integrity), statuses,
        ):
            integrity_label.setText(integrity_messages.get(
                state, integrity_messages["unavailable"],
            ))
        for marker_label, state in zip(
            (thermal_locator, rgb_locator), marker_statuses,
        ):
            marker_label.setText(locator_messages.get(
                state, locator_messages["unavailable"],
            ))
        preview_status.setText(
            "Sichtbilder aus dem ausdrücklich ausgewählten lokalen Ordner. "
            "RGB nur bei gespeicherter Verknüpfung; Thermal-JPEG ist kein "
            "radiometrischer Messwert. Originaldateien wurden nicht verändert."
        )

    finding_list.itemSelectionChanged.connect(reset_image_preview)
    if on_preview_images is not None:
        preview_button.clicked.connect(load_preview)


    # Pagination is read-only; only explicitly submitted decisions persist.
    navigation = QHBoxLayout()
    previous = QPushButton("Vorherige Befunde", page)
    previous.setObjectName("review_previous_page")
    page_count = QLabel("", page)
    page_count.setObjectName("review_page_status")
    following = QPushButton("Weitere Befunde", page)
    following.setObjectName("review_next_page")
    count = overview.summary.unreviewed_findings if overview is not None else 0
    enabled = (
        overview is not None and current_project_id is not None
        and on_page_requested is not None
    )
    page_count.setText(
        f"Offene Befunde {offset + 1}–{offset + len(pending)} von {count}"
        if pending else f"Keine offenen Befunde auf dieser Seite ({count} insgesamt)"
    )
    page_count.setTextFormat(Qt.TextFormat.PlainText)
    previous.setEnabled(bool(enabled and offset >= MAX_REVIEW_PAGE_FINDINGS))
    following.setEnabled(bool(
        enabled and pending and offset + len(pending) < count
    ))
    if enabled:
        previous.clicked.connect(
            lambda checked=False: on_page_requested(
                max(0, offset - MAX_REVIEW_PAGE_FINDINGS),
            )
        )
        following.clicked.connect(
            lambda checked=False: on_page_requested(
                offset + MAX_REVIEW_PAGE_FINDINGS,
            )
        )
    navigation.addWidget(previous)
    navigation.addWidget(page_count, 1)
    navigation.addWidget(following)
    layout.addLayout(navigation)

    caution = QLabel(
        "Eine Bestätigung ist eine fachliche Entscheidung über einen gespeicherten "
        "Kandidaten, keine automatische Diagnose. Fehlende Modulzuordnung, "
        "Temperaturkalibrierung und Berichtfreigabe bleiben gesonderte Prüfschritte. "
        "Die Detailansicht zeigt gespeicherte Werte, keine Originalbilder. "
        "Die Liste zeigt jeweils eine begrenzte Seite offener Befunde.",
        page,
    )
    caution.setObjectName("review_safety_notice")
    caution.setWordWrap(True)
    layout.addWidget(caution)

    reviewer = QLineEdit(page)
    reviewer.setObjectName("expert_reviewer")
    reviewer.setPlaceholderText("Prüferkennung (Pflichtfeld)")
    layout.addWidget(reviewer)

    decision = QComboBox(page)
    decision.setObjectName("expert_decision")
    decision.addItem("Bitte fachliche Entscheidung wählen", None)
    decision.addItem("Bestätigen", ReviewStatus.CONFIRMED.value)
    decision.addItem("Verwerfen", ReviewStatus.REJECTED.value)
    decision.addItem("Unklar – weitere Prüfung nötig", ReviewStatus.UNCLEAR.value)
    layout.addWidget(decision)

    note = QPlainTextEdit(page)
    note.setObjectName("expert_review_note")
    note.setPlaceholderText("Begründung / Prüfnotiz (optional)")
    note.setMaximumHeight(85)
    layout.addWidget(note)

    submit = QPushButton("Ausgewählte Entscheidung protokollieren", page)
    submit.setObjectName("submit_expert_review")
    layout.addWidget(submit)

    allowed = (
        overview is not None and overview.review.allowed
        and current_project_id is not None and on_review is not None
    )

    def update_submit():
        submit.setEnabled(bool(
            allowed and finding_list.currentItem() is not None
            and reviewer.text().strip()
            and decision.currentData() in (
                ReviewStatus.CONFIRMED.value,
                ReviewStatus.REJECTED.value,
                ReviewStatus.UNCLEAR.value,
            )
        ))

    def submit_review():
        item = finding_list.currentItem()
        if not submit.isEnabled() or item is None:
            return
        on_review(
            item.data(Qt.ItemDataRole.UserRole),
            ReviewStatus(decision.currentData()),
            reviewer.text().strip(),
            note.toPlainText().strip() or None,
        )

    finding_list.itemSelectionChanged.connect(update_submit)
    reviewer.textChanged.connect(update_submit)
    decision.currentIndexChanged.connect(update_submit)
    if on_review is not None:
        submit.clicked.connect(submit_review)
    update_submit()

    refresh = QPushButton("Offene Befunde aktualisieren", page)
    refresh.setObjectName("refresh_review_button")
    refresh.setEnabled(
        current_project_id is not None and on_refresh is not None
    )
    if on_refresh is not None and current_project_id is not None:
        refresh.clicked.connect(on_refresh)
    layout.addWidget(refresh)

    if last_review_status:
        result = QLabel(last_review_status, page)
        result.setObjectName("review_decision_status")
        result.setTextFormat(Qt.TextFormat.PlainText)
        result.setWordWrap(True)
        layout.addWidget(result)

    layout.addStretch(1)
    return page
