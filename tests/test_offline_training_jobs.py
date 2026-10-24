"""Synthetic offline trainer integration: no pretrained PV model is shipped or trained.

A verified local injected backend is the *only* path to execution. The dummy
runner writes bytes, not usable model weights. It exists to validate durable
job status, integrity gates, user cancellation and desktop status truthfulness.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import Event
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PIL import Image

from mcm_solarcheck.review.defect_classes import DefectClass
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.review.training_split import split_for_group
from mcm_solarcheck.services.offline_report_training import OfflineReportTraining
from mcm_solarcheck.services.offline_training_jobs import TrainingCancelled
from mcm_solarcheck.services.offline_training_preflight import (
    OfflineTrainerConfiguration, verify_staged_classification_dataset,
)
from mcm_solarcheck.services.shell_navigation import ShellRoute
from test_offline_report_training_optin import _approve
from test_gui_report_draft_vertical import seeded_window


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _six_reviewed_samples(window, tmp_path):
    groups = {"train": [], "validation": [], "test": []}
    for n in range(10000):
        name = f"inspection-group-{n:04d}"
        label = split_for_group(name)
        if len(groups[label]) < 2:
            groups[label].append(name)
        if all(len(x) == 2 for x in groups.values()):
            break
    assert all(len(x) == 2 for x in groups.values())
    samples = []
    for i, group in enumerate(sum(groups.values(), [])):
        source = tmp_path / f"private-image-{i}.JPG"
        Image.new("RGB", (24, 24), (i * 18, 2, 3)).save(source, format="JPEG")
        samples.append((f"FRAME-{i}", source, group))
    db = window._project_service.database
    db.save_training_samples(
        "P1",
        [index_m3t_training_sample(frame, path, "rgb")
         for frame, path, _group in samples],
    )
    for i, (frame, _path, group) in enumerate(samples):
        db.save_ground_truth("P1", GroundTruthLabel(
            frame, "Prueferin",
            DefectClass.NORMAL if i % 2 else DefectClass.THERMAL_HOTSPOT_CANDIDATE,
            module_id=f"M-{i}", inspection_group_id=group,
        ))
        db.approve_training_frame("P1", frame, rights_approved=True)
    return samples


def _config(tmp_path, *, wrong_sha=False):
    weights = tmp_path / "vetted-local-weights.pt"
    weights.write_bytes(b"test-only-pretrained-checkpoint")
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()
    if wrong_sha:
        digest = "0" * 64
    return OfflineTrainerConfiguration(
        backend="explicit-local-classification-stub",
        backend_version="test-v1",
        model_weights=weights,
        model_sha256=digest,
        weights_license_review="synthetic-test-license-review",
        epochs=1, seed=51,
    )


def _wait_for(training, approval, status, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        item = training.state("P1", approval.approval_id)
        if item is not None and item.status == status:
            return item
        time.sleep(0.02)
    raise AssertionError(f"local test trainer did not reach {status}")


def test_injected_reviewed_trainer_runs_in_background_and_never_deploys_model(
    tmp_path, app,
):
    window = seeded_window(tmp_path)
    started, release = Event(), Event()

    def trainer(dataset, config, output, progress, cancel):
        assert set(dataset.splits) == {"train", "validation", "test"}
        assert len(dataset.classes) >= 2
        assert dataset.sample_count == 6
        assert config.epochs == 1
        progress(17)
        started.set()
        assert release.wait(8)
        assert not cancel.is_set()
        progress(93)
        result = output / "model-test-only.pt"
        result.write_bytes(b"synthetic weights, not a usable trained model")
        return result

    try:
        _six_reviewed_samples(window, tmp_path)
        training = OfflineReportTraining(
            window._project_service, training_configuration=_config(tmp_path),
            training_launcher=trainer,
        )
        window._offline_report_training = training
        approval = _approve(window, use_training=True)
        assert started.wait(8)
        running = training.state("P1", approval.approval_id)
        assert running.status == "training_running"
        assert running.progress_percent == 17
        assert running.weights_sha256 is None
        window._refresh_report_page()
        page = window._pages[ShellRoute.REPORT]
        assert "17 %" in page.findChild(QLabel, "report_training_status").text()
        assert page.findChild(QPushButton, "report_training_refresh") is not None
        assert training._training_jobs.is_active(running.request_id)
        release.set()
        completed = _wait_for(training, approval, "training_completed_not_deployed")
        assert completed.progress_percent == 100
        assert completed.weights_sha256 == hashlib.sha256(
            b"synthetic weights, not a usable trained model",
        ).hexdigest()
        window._pages[ShellRoute.REPORT].findChild(
            QPushButton, "report_training_refresh",
        ).click()
        assert "NICHT" in window._pages[ShellRoute.REPORT].findChild(
            QLabel, "report_training_status",
        ).text()
        assert window._project_service.report_release_decision(
            "P1", "REPORT-TRAIN",
            __import__("datetime").datetime(
                2026, 10, 19, 12, tzinfo=__import__("datetime").timezone.utc,
            ),
            expected_draft=window._draft_report,
        ) == approval
    finally:
        release.set()
        window.close()


def test_revocation_while_backend_running_requests_cancel_and_blocks_result(
    tmp_path, app,
):
    window = seeded_window(tmp_path)
    started = Event()

    def cooperative(dataset, config, output, progress, cancel):
        progress(10)
        started.set()
        assert cancel.wait(8)
        raise TrainingCancelled()

    try:
        _six_reviewed_samples(window, tmp_path)
        window._offline_report_training = OfflineReportTraining(
            window._project_service, training_configuration=_config(tmp_path),
            training_launcher=cooperative,
        )
        approval = _approve(window, use_training=True)
        assert started.wait(8)
        training = window._offline_report_training
        state = training.state("P1", approval.approval_id)
        folder = tmp_path / "training-data" / state.request_id
        assert folder.is_dir()
        button = window._pages[ShellRoute.REPORT].findChild(
            QPushButton, "report_training_revoke"
        )
        button.click()
        revoked = _wait_for(training, approval, "revoked")
        assert revoked.weights_sha256 is None
        end = time.monotonic() + 8
        while folder.exists() and time.monotonic() < end:
            time.sleep(0.02)
        assert not folder.exists()
        assert not training._training_jobs.is_active(state.request_id)
        assert training.state("P1", approval.approval_id).status == "revoked"
    finally:
        window.close()


def test_fake_backend_exception_is_sanitized_and_no_success_reported(
    tmp_path, app,
):
    window = seeded_window(tmp_path)

    def failed(dataset, config, output, progress, cancel):
        progress(33)
        raise RuntimeError("PRIVATE_CUSTOMER_NAME_AND_PATH_MUST_NOT_LEAK")

    try:
        _six_reviewed_samples(window, tmp_path)
        window._offline_report_training = OfflineReportTraining(
            window._project_service, training_configuration=_config(tmp_path),
            training_launcher=failed,
        )
        approval = _approve(window, use_training=True)
        training = window._offline_report_training
        failed_state = _wait_for(training, approval, "training_failed")
        assert failed_state.error_code == "trainer_failed_or_invalid_output"
        assert failed_state.weights_sha256 is None
        window._refresh_report_page()
        status_text = window._pages[ShellRoute.REPORT].findChild(
            QLabel, "report_training_status"
        ).text()
        assert "fehlgeschlagen" in status_text
        assert "PRIVATE_CUSTOMER" not in status_text
    finally:
        window.close()


def test_model_hash_mismatch_prevents_launch_without_losing_signed_report(
    tmp_path, app,
):
    window = seeded_window(tmp_path)
    called = []

    def must_not_run(*args):
        called.append(True)
        raise AssertionError("no validated model weights")

    try:
        _six_reviewed_samples(window, tmp_path)
        window._offline_report_training = OfflineReportTraining(
            window._project_service,
            training_configuration=_config(tmp_path, wrong_sha=True),
            training_launcher=must_not_run,
        )
        approval = _approve(window, use_training=True)
        state = window._offline_report_training.state("P1", approval.approval_id)
        assert state.status == "staged_waiting_for_trainer"
        assert called == []
        assert state.sample_count == 6
        assert window._project_service.report_release_decision(
            "P1", "REPORT-TRAIN",
            __import__("datetime").datetime(
                2026, 10, 19, 12, tzinfo=__import__("datetime").timezone.utc,
            ),
        ) == approval
    finally:
        window.close()


def test_hash_change_or_missing_splits_fails_readiness_preflight(tmp_path, app):
    window = seeded_window(tmp_path)
    try:
        _six_reviewed_samples(window, tmp_path)
        approval = _approve(window, use_training=True)
        state = window._offline_report_training.state("P1", approval.approval_id)
        assert state.status == "staged_waiting_for_trainer"
        folder = tmp_path / "training-data" / state.request_id
        verified = verify_staged_classification_dataset(folder)
        assert verified.sample_count == 6
        assert verified.classes == ("normal", "thermal_hotspot_candidate")
        content = next(folder.glob("sample-*.jpg"))
        content.write_bytes(b"tampered!")
        with pytest.raises(PermissionError, match="hash"):
            verify_staged_classification_dataset(folder)
        # Restore checksums by restoring from original reviewed files via index
        # is intentionally not automated. Tampered data must be re-approved.
    finally:
        window.close()


def test_no_implicit_installed_trainer_or_download_from_default_composition(tmp_path, app):
    window = seeded_window(tmp_path)
    try:
        assert window._offline_report_training._training_jobs is None
        assert not (tmp_path / "training-data").exists()
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
