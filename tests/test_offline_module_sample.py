"""Synthetic authenticated RGB sampling; never writes PV modules/findings."""
from __future__ import annotations

from hashlib import sha256

import pytest
from PIL import Image

from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.services.offline_module_sample import (
    MAX_SAMPLE_FRAMES, ModuleSampleCancelled, sample_imported_rgb_module_evidence,
)
from mcm_solarcheck.services.workflow import WorkflowStage


def seed(tmp_path, *, frames=4, with_hash=True):
    s = build_offline_services(tmp_path / "modules.sqlite3").projects
    s.create_project("P1", "Synthetic")
    s.create_project("P2", "Another")
    sources = []
    for i in range(frames):
        p = tmp_path / f"rgb-{i}.jpg"
        Image.new("RGB", (64, 48), (80, 130, 110)).save(p)
        sources.append(p)
        with s.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames "
                "(project_id,frame_id,source_file,width,height) VALUES (?,?,?,?,?)",
                ("P1", f"V{i:03d}", str(p), 64, 48),
            )
            if with_hash:
                sql.execute(
                    "INSERT INTO training_samples "
                    "(sample_id,project_id,source_frame_id,source_file,modality,"
                    "content_sha256,label_status,rights_status)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (f"S{i}", "P1", f"V{i:03d}", str(p), "rgb",
                     sha256(p.read_bytes()).hexdigest(), "pending", "private"),
                )
    return s, sources


class FakeGrid:
    def detect_with_diagnostics_array(self, bgr):
        assert bgr.shape == (48, 64, 3)
        return (), None


class FakeImage:
    def detect_array(self, bgr):
        assert bgr.shape == (48, 64, 3)
        return ()


def test_bounded_readonly_rgb_sample_keeps_all_permissions_closed(tmp_path):
    s, src = seed(tmp_path)
    before = [p.read_bytes() for p in src]
    progress = []
    r = sample_imported_rgb_module_evidence(
        s.database, "P1", grid_detector=FakeGrid(), image_detector=FakeImage(),
        on_progress=lambda *v: progress.append(v),
    )
    assert r.available_rgb == 4 and r.sample_size == MAX_SAMPLE_FRAMES == 3
    assert r.checked == r.analyzed == 3
    assert r.issues == r.unverified == 0
    assert r.structural_proposals == r.visual_proposals == r.overlapping_proposals == 0
    assert r.frames_with_overlap == 0 and not r.changed_inputs
    assert progress == [(1, 3, 0), (2, 3, 0), (3, 3, 0)]
    assert [p.read_bytes() for p in src] == before
    assert not s.state("P1").readiness(WorkflowStage.REVIEW).ready
    assert not s.state("P1").readiness(WorkflowStage.REPORT).ready
    assert not s.state("P1").readiness(WorkflowStage.EXPORT).ready
    assert sample_imported_rgb_module_evidence(s.database, "P2").sample_size == 0
    with s.database.connect() as sql:
        assert sql.execute("SELECT COUNT(*) FROM pv_modules").fetchone()[0] == 0
        assert sql.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0
        assert sql.execute("SELECT COUNT(*) FROM offline_processing_runs").fetchone()[0] == 0


def test_missing_checksum_never_triggers_detector(tmp_path):
    s, _ = seed(tmp_path, frames=1, with_hash=False)
    r = sample_imported_rgb_module_evidence(
        s.database, "P1", grid_detector=FakeGrid(), image_detector=FakeImage(),
    )
    assert r.analyzed == 0 and r.unverified == 1
    assert r.overlapping_proposals == 0


@pytest.mark.parametrize("mode", ["changed_bytes", "missing", "wrong_dimensions"])
def test_invalid_input_is_not_recognized_as_module(tmp_path, mode):
    s, paths = seed(tmp_path, frames=1)
    if mode == "changed_bytes":
        paths[0].write_bytes(paths[0].read_bytes() + b"changed")
    elif mode == "missing":
        paths[0].unlink()
    else:
        with s.database.connect() as sql:
            sql.execute(
                "UPDATE image_frames SET width=200 WHERE project_id='P1'"
            )
    r = sample_imported_rgb_module_evidence(
        s.database, "P1", grid_detector=FakeGrid(), image_detector=FakeImage(),
    )
    assert r.analyzed == 0 and r.issues == 1
    assert r.overlapping_proposals == 0


def test_cancellation_and_changed_inventory_reported(tmp_path):
    s, _ = seed(tmp_path, frames=1)
    with pytest.raises(ModuleSampleCancelled):
        sample_imported_rgb_module_evidence(s.database, "P1", should_cancel=lambda: True)
    cancelled = {"now": False}
    with pytest.raises(ModuleSampleCancelled):
        sample_imported_rgb_module_evidence(
            s.database, "P1", grid_detector=FakeGrid(), image_detector=FakeImage(),
            should_cancel=lambda: cancelled["now"],
            on_progress=lambda *_: cancelled.__setitem__("now", True),
        )
    def modify_after(*_):
        with s.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames(project_id,frame_id,source_file) VALUES (?,?,?)",
                ("P1", "ADDED", "missing.jpg"),
            )
    r = sample_imported_rgb_module_evidence(
        s.database, "P1", grid_detector=FakeGrid(), image_detector=FakeImage(),
        on_progress=modify_after,
    )
    assert r.changed_inputs
    assert r.overlapping_proposals == 0



class FakeRejectedCadence:
    def detect_array_with_status(self, bgr):
        assert bgr.shape == (48, 64, 3)
        return (), "cadence_not_confirmed"


class FakeSupportingCadence:
    def detect_array_with_status(self, bgr):
        from mcm_solarcheck.vision.detection import ModuleDetection
        assert bgr.shape == (48, 64, 3)
        return (
            ModuleDetection(((1, 1), (20, 1), (20, 12), (1, 12)), .65),
        ), "spatially_supported"


def test_existing_cadence_grid_failure_is_explained_without_approval(tmp_path):
    service, originals = seed(tmp_path, frames=3)
    source_bytes = [path.read_bytes() for path in originals]
    result = sample_imported_rgb_module_evidence(
        service.database, "P1",
        grid_detector=FakeGrid(), image_detector=FakeImage(),
        cadence_detector=FakeRejectedCadence(),
    )
    assert result.analyzed == 3 and result.cadence_proposals == 0
    assert result.cadence_rejected_grid == 3
    assert result.cadence_rejected_no_support == 0
    assert result.cadence_frames_with_proposals == 0
    assert [path.read_bytes() for path in originals] == source_bytes
    assert not service.state("P1").readiness(WorkflowStage.REVIEW).ready
    with service.database.connect() as sql:
        assert sql.execute("SELECT COUNT(*) FROM pv_modules").fetchone()[0] == 0
        assert sql.execute("SELECT COUNT(*) FROM offline_processing_runs").fetchone()[0] == 0


def test_cadence_suggestions_are_not_approved_or_saved(tmp_path):
    service, originals = seed(tmp_path, frames=1)
    result = sample_imported_rgb_module_evidence(
        service.database, "P1",
        grid_detector=FakeGrid(), image_detector=FakeImage(),
        cadence_detector=FakeSupportingCadence(),
    )
    assert result.cadence_proposals == 1
    assert result.cadence_frames_with_proposals == 1
    assert result.overlapping_proposals == 0
    assert result.technical_sample_only
    for stage in (
        WorkflowStage.REVIEW, WorkflowStage.REPORT, WorkflowStage.EXPORT
    ):
        assert not service.state("P1").readiness(stage).ready
    with service.database.connect() as sql:
        assert sql.execute("SELECT COUNT(*) FROM pv_modules").fetchone()[0] == 0
        assert sql.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0


def test_tampered_original_is_not_sent_to_cadence_detector(tmp_path):
    service, files = seed(tmp_path, frames=1)
    files[0].write_bytes(files[0].read_bytes() + b"changed")
    class NoCadenceExecution:
        def detect_array_with_status(self, _):
            raise AssertionError("tampered original reached detector")
    result = sample_imported_rgb_module_evidence(
        service.database, "P1",
        grid_detector=FakeGrid(), image_detector=FakeImage(),
        cadence_detector=NoCadenceExecution(),
    )
    assert result.analyzed == 0 and result.issues == 1
    assert result.cadence_proposals == 0


def test_cadence_zero_support_reports_independent_evidence_gap(tmp_path):
    service, _ = seed(tmp_path, frames=1)
    class NoIndependentEvidence:
        def detect_array_with_status(self, _):
            return (), "independent_image_support_required"
    result = sample_imported_rgb_module_evidence(
        service.database, "P1",
        grid_detector=FakeGrid(), image_detector=FakeImage(),
        cadence_detector=NoIndependentEvidence(),
    )
    assert result.cadence_rejected_no_support == 1
    assert result.cadence_rejected_grid == 0
