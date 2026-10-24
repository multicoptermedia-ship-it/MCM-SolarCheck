"""Offline training opt-in belongs to an approved report, not report progress."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QLineEdit, QPushButton

from mcm_solarcheck.review.defect_classes import DefectClass
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.services.offline_report_training import OfflineReportTraining
from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP
from mcm_solarcheck.services.shell_navigation import ShellRoute
from test_gui_report_draft_vertical import seeded_window

UTC = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _prepare(window):
    window._prepare_report_draft("P1", "REPORT-TRAIN", UTC)
    assert window._draft_report is not None
    window.show_route(ShellRoute.REPORT)
    return window._pages[ShellRoute.REPORT]


def _approve(window, *, use_training=False, reference="customer-rights-accepted"):
    page = _prepare(window)
    checkbox = page.findChild(QCheckBox, "report_training_opt_in")
    assert checkbox is not None
    assert checkbox.text() == "solarcheck-Datensatz für das KI-Training freigeben"
    assert not checkbox.isChecked()
    page.findChild(QLineEdit, "report_release_reviewer").setText("Prueferin")
    if use_training:
        checkbox.setChecked(True)
        page.findChild(QLineEdit, "report_training_rights_reference").setText(reference)
    submit = page.findChild(QPushButton, "approve_report_release")
    assert submit.isEnabled()
    submit.click()
    approval = window._project_service.report_release_decision(
        "P1", "REPORT-TRAIN", UTC, expected_draft=window._draft_report,
    )
    assert approval is not None
    return approval


def test_unchecked_optin_approves_report_without_ledger_or_copy(tmp_path, app):
    window = seeded_window(tmp_path)
    try:
        approval = _approve(window, use_training=False)
        assert window._offline_report_training.state("P1", approval.approval_id) is None
        assert not (tmp_path / "training-data").exists()
        assert window._project_service.report_release_decision(
            "P1", "REPORT-TRAIN", UTC,
        ) == approval
    finally:
        window.close()


def test_checked_optin_requires_rights_reference_but_never_blocks_report_without_it(
    tmp_path, app,
):
    window = seeded_window(tmp_path)
    try:
        page = _prepare(window)
        page.findChild(QLineEdit, "report_release_reviewer").setText("Prueferin")
        training = page.findChild(QCheckBox, "report_training_opt_in")
        reference = page.findChild(QLineEdit, "report_training_rights_reference")
        approve = page.findChild(QPushButton, "approve_report_release")
        assert not reference.isEnabled()
        assert approve.isEnabled()
        training.setChecked(True)
        assert reference.isEnabled()
        assert not approve.isEnabled()
        reference.setText("x")
        assert not approve.isEnabled()
        reference.setText("Customer-rights-ref-123")
        assert approve.isEnabled()
        training.setChecked(False)
        assert approve.isEnabled()
        assert not training.isChecked()
        assert reference.text() == "Customer-rights-ref-123"
        approve.click()
        assert not (tmp_path / "training-data").exists()
    finally:
        window.close()


def test_checked_optin_records_request_but_no_unvalidated_training_launch(
    tmp_path, app,
):
    window = seeded_window(tmp_path)
    try:
        approval = _approve(window, use_training=True)
        request = window._offline_report_training.state("P1", approval.approval_id)
        assert request is not None
        assert request.status == "pending_training_data_review"
        assert request.sample_count == 0
        assert not (tmp_path / "training-data" / request.request_id).exists()
        status = window._pages[ShellRoute.REPORT].findChild(
            QLabel, "report_training_status"
        )
        assert status is not None
        assert "kein KI-Training gestartet" in status.text()
        assert "customer-rights-accepted" not in status.text()
        with pytest.raises(PermissionError, match="already"):
            window._offline_report_training.request(
                project_id="P1", report=window._draft_report,
                approval=approval, authorized_by="Prueferin",
                rights_reference="customer-rights-accepted",
                affirmative_opt_in=True,
            )
    finally:
        window.close()


def test_training_optin_requires_active_release_and_exact_project(tmp_path, app):
    window = seeded_window(tmp_path)
    try:
        approval = _approve(window)
        training = window._offline_report_training
        with pytest.raises(PermissionError):
            training.request(
                project_id="P2", report=window._draft_report, approval=approval,
                authorized_by="Prueferin", rights_reference="customer-agreement",
                affirmative_opt_in=True,
            )
        with pytest.raises(PermissionError):
            training.request(
                project_id="P1", report=window._draft_report, approval=approval,
                authorized_by="Prueferin", rights_reference="customer-agreement",
                affirmative_opt_in=False,
            )
        with pytest.raises(PermissionError):
            training.request(
                project_id="P1", report=window._draft_report, approval=approval,
                authorized_by="Another reviewer", rights_reference="customer-agreement",
                affirmative_opt_in=True,
            )
        with pytest.raises(PermissionError):
            training.request(
                project_id="P1", report=window._draft_report, approval=approval,
                authorized_by="Prueferin", rights_reference="",
                affirmative_opt_in=True,
            )
        window._project_service.database.create_project("P1", "Changed project evidence")
        with pytest.raises(PermissionError, match="changed"):
            training.request(
                project_id="P1", report=window._draft_report, approval=approval,
                authorized_by="Prueferin", rights_reference="customer-agreement",
                affirmative_opt_in=True,
            )
    finally:
        window.close()


def test_only_reviewed_and_rights_approved_images_staged_and_revoked(
    tmp_path, app,
):
    window = seeded_window(tmp_path)
    try:
        source = tmp_path / "original-m3t.JPG"
        from PIL import Image
        Image.new("RGB", (16, 16), (12, 34, 56)).save(source, format="JPEG")
        db = window._project_service.database
        db.save_training_samples("P1", [
            index_m3t_training_sample("T1", source, "thermal"),
        ])
        db.save_ground_truth("P1", GroundTruthLabel(
            "T1", "Prueferin", DefectClass.NORMAL, module_id="M1",
        ))
        db.approve_training_frame("P1", "T1", rights_approved=True)
        source_bytes = source.read_bytes()
        approval = _approve(window, use_training=True)
        state = window._offline_report_training.state("P1", approval.approval_id)
        assert state is not None
        assert state.status == "staged_waiting_for_trainer"
        assert state.sample_count == 1
        staging = tmp_path / "training-data" / state.request_id
        copied = list(staging.glob("sample-*.jpg"))
        assert len(copied) == 1
        assert copied[0].read_bytes() == source_bytes
        assert source.read_bytes() == source_bytes
        index = (staging / "training-index.json").read_text("utf-8")
        assert str(source) not in index
        assert "original-m3t" not in index
        assert not list(staging.glob("*.pt"))
        window._offline_report_training.revoke("P1", approval.approval_id)
        assert not staging.exists()
        assert source.read_bytes() == source_bytes
        state = window._offline_report_training.state("P1", approval.approval_id)
        assert state.status == "revoked"
    finally:
        window.close()


def test_training_staging_does_not_use_unapproved_or_unreviewed_sample(
    tmp_path, app,
):
    window = seeded_window(tmp_path)
    try:
        image = tmp_path / "unreviewed.JPG"
        image.write_bytes(b"do not copy this")
        window._project_service.database.save_training_samples("P1", [
            index_m3t_training_sample("T1", image, "thermal"),
        ])
        approval = _approve(window, use_training=True)
        state = window._offline_report_training.state("P1", approval.approval_id)
        assert state.status == "pending_training_data_review"
        assert not (tmp_path / "training-data" / state.request_id).exists()
        assert image.read_bytes() == b"do not copy this"
    finally:
        window.close()


def test_optin_revocation_is_accessible_from_report_page(tmp_path, app):
    window = seeded_window(tmp_path)
    try:
        approval = _approve(window, use_training=True)
        page = window._pages[ShellRoute.REPORT]
        revoke = page.findChild(QPushButton, "report_training_revoke")
        assert revoke is not None and revoke.isEnabled()
        revoke.click()
        state = window._offline_report_training.state("P1", approval.approval_id)
        assert state is not None and state.status == "revoked"
        page = window._pages[ShellRoute.REPORT]
        assert page.findChild(QPushButton, "report_training_revoke") is None
        assert "widerrufen" in page.findChild(QLabel, "report_training_status").text()
    finally:
        window.close()


@pytest.fixture(autouse=True)
def _simulate_completed_processing_only_for_legacy_ui_regressions(monkeypatch):
    """These historic UI tests exercise post-processing UI in isolation.

    A future trusted processing worker is simulated ONLY inside this test
    module. The real offline application remains fail-closed by default;
    tests/test_offline_review_requires_processing.py verifies that contract.
    """
    monkeypatch.setattr(
        "mcm_solarcheck.services.offline_review_gate.verified_offline_processing_blockers",
        lambda database, project_id: (),
    )
