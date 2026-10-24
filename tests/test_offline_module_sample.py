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
