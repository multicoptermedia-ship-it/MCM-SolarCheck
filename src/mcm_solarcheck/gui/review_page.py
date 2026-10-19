"""Windows expert review workspace backed by persisted, unreviewed project findings."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from mcm_solarcheck.review.findings import ReviewStatus

MAX_REVIEW_PAGE_FINDINGS = 50


def make_review_page(
    parent=None, *, current_project_id=None, overview=None, pending=(),
    on_review=None, on_refresh=None, last_review_status=None,
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
    for finding in pending:
        module = finding.module_id or "nicht zugeordnet"
        item = QListWidgetItem(
            f"{finding.finding_id} · {finding.finding_type} · "
            f"Thermalbild {finding.thermal_frame_id} · Modul {module}"
        )
        item.setData(Qt.ItemDataRole.UserRole, finding.finding_id)
        finding_list.addItem(item)
    layout.addWidget(finding_list)

    caution = QLabel(
        "Eine Bestätigung ist eine fachliche Entscheidung über einen gespeicherten "
        "Kandidaten, keine automatische Diagnose. Fehlende Modulzuordnung, "
        "Temperaturkalibrierung und Berichtfreigabe bleiben gesonderte Prüfschritte. "
        "Die Liste zeigt nur die ersten offenen Befunde.",
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
