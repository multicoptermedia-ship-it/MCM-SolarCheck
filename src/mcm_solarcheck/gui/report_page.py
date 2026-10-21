"""Desktop report preparation and explicit human approval; preview tracking is private."""
from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from mcm_solarcheck.services.review_progress import ReviewProgress


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
    progress: ReviewProgress | None = None, approval=None, on_approve=None,
    on_preview=None, training_request=None,
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

    if progress is not None:
        decision_progress = QLabel(
            f"Befundentscheidungen laut SQLite: "
            f"{progress.decided_findings} von {progress.total_findings} "
            f"({progress.decision_percent} %) · "
            f"Offen: {progress.open_findings} · "
            f"Unklar: {progress.unclear_findings}. "
            "Dies ist keine Berichtfreigabe.",
            page,
        )
        decision_progress.setObjectName("report_review_progress")
        decision_progress.setTextFormat(Qt.TextFormat.PlainText)
        decision_progress.setWordWrap(True)
        layout.addWidget(decision_progress)

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
    if draft is not None:
        approval_status = QLabel(
            "Fachliche Freigabe für diesen Datenstand dokumentiert: "
            f"{approval.approved_by} · {approval.approved_at_utc}. "
            "Keine automatische Normkonformität."
            if approval is not None else
            "Keine gültige menschliche Berichtsfreigabe für diesen Entwurf. "
            "Entscheidungsfortschritt allein genügt nicht.",
            page,
        )
        approval_status.setObjectName("report_release_status")
        approval_status.setTextFormat(Qt.TextFormat.PlainText)
        approval_status.setWordWrap(True)
        layout.addWidget(approval_status)

        preview = QPushButton("Berichtsentwurf vollständig ansehen …", page)
        preview.setObjectName("view_report_pdf")
        preview.setEnabled(on_preview is not None)
        if on_preview is not None:
            preview.clicked.connect(lambda _checked=False: on_preview())
        layout.addWidget(preview)

        approver = QLineEdit(page)
        approver.setObjectName("report_release_reviewer")
        approver.setPlaceholderText("Name der fachlich freigebenden Person")
        layout.addWidget(approver)
        unresolved_ack = QCheckBox(
            "Unklare Befunde und möglichen Nachprüfungsbedarf ausdrücklich zur Kenntnis genommen",
            page,
        )
        unresolved_ack.setObjectName("report_release_unclear_ack")
        layout.addWidget(unresolved_ack)
        followup = QLineEdit(page)
        followup.setObjectName("report_release_followup_note")
        followup.setPlaceholderText("Bei unklaren Befunden: dokumentierter Nachprüfungsbedarf")
        layout.addWidget(followup)
        training_opt_in = QCheckBox(
            "solarcheck-Datensatz für das KI-Training freigeben", page,
        )
        training_opt_in.setObjectName("report_training_opt_in")
        training_opt_in.setChecked(False)
        layout.addWidget(training_opt_in)
        training_rights = QLineEdit(page)
        training_rights.setObjectName("report_training_rights_reference")
        training_rights.setPlaceholderText(
            "Nachweis der Kunden-/Nutzungsfreigabe (Pflicht bei Trainingsfreigabe)"
        )
        training_rights.setEnabled(False)
        layout.addWidget(training_rights)
        training_notice = QLabel(
            "Freiwillige zusätzliche Trainingsentscheidung. Nur bereits menschlich "
            "geprüfte Bilder mit dokumentierten Nutzungsrechten dürfen lokal "
            "übernommen werden. Ohne geprüfte Trainingskonfiguration startet "
            "kein KI-Training. Die Berichtsfreigabe bleibt davon unabhängig.",
            page,
        )
        training_notice.setObjectName("report_training_notice")
        training_notice.setTextFormat(Qt.TextFormat.PlainText)
        training_notice.setWordWrap(True)
        layout.addWidget(training_notice)
        approve = QPushButton("Bericht ausdrücklich fachlich freigeben", page)
        approve.setObjectName("approve_report_release")
        layout.addWidget(approve)

        def update_approval():
            review_ready = bool(
                progress is not None and progress.total_findings > 0
                and progress.all_findings_decided and not progress.other_status_findings
            )
            unclear_ready = bool(
                progress is not None and (
                    progress.unclear_findings == 0 or (
                        unresolved_ack.isChecked() and followup.text().strip()
                    )
                )
            )
            approve.setEnabled(bool(
                current_project_id is not None and not blocked
                and approval is None and on_approve is not None and review_ready
                and unclear_ready and approver.text().strip()
                and (not training_opt_in.isChecked()
                     or len(training_rights.text().strip()) >= 3)
            ))

        approver.textChanged.connect(update_approval)
        unresolved_ack.toggled.connect(update_approval)
        followup.textChanged.connect(update_approval)
        training_opt_in.toggled.connect(training_rights.setEnabled)
        training_opt_in.toggled.connect(update_approval)
        training_rights.textChanged.connect(update_approval)
        if on_approve is not None:
            def confirm_report():
                if not approve.isEnabled():
                    return
                if training_opt_in.isChecked():
                    on_approve(
                        approver.text(), unresolved_ack.isChecked(), followup.text(),
                        True, training_rights.text().strip(),
                    )
                else:
                    on_approve(
                        approver.text(), unresolved_ack.isChecked(), followup.text(),
                    )
            approve.clicked.connect(confirm_report)
        update_approval()

        if training_request is not None:
            status_text = (
                "Trainingsfreigabe vermerkt: freigegebene Trainingsbeispiele "
                f"lokal bereitgestellt ({training_request.sample_count}). "
                "Es ist noch kein KI-Training gestartet; geprüfter Trainer fehlt."
                if training_request.status == "staged_waiting_for_trainer"
                else "Trainingsfreigabe vermerkt. Trainingsdaten oder nachgewiesene "
                     "Nutzungsrechte noch nicht vollständig geprüft. "
                     "Noch kein KI-Training gestartet."
            )
            indicator = QLabel(status_text, page)
            indicator.setObjectName("report_training_status")
            indicator.setTextFormat(Qt.TextFormat.PlainText)
            indicator.setWordWrap(True)
            layout.addWidget(indicator)

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
