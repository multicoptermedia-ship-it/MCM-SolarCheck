"""Real synthetic JPEG pixels, no DJI images. Overlay never persists findings."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.services.offline_module_sample import ModuleSampleCancelled
from mcm_solarcheck.services.offline_rgb_module_overlay import (
    MAX_PREVIEW_SIDE, render_imported_rgb_module_overlay,
)
from mcm_solarcheck.services.workflow import WorkflowStage
from mcm_solarcheck.vision.detection import ModuleDetection


def seed(tmp_path, count=3):
    service = build_offline_services(tmp_path / "isolated.sqlite3").projects
    service.create_project("P1", "Synthetic")
    service.create_project("P2", "Unrelated")
    paths = []
    for idx in range(count):
        path = tmp_path / f"synthetic-{idx}.jpg"
        image = Image.new("RGB", (640, 512), (65 + idx, 110, 140))
        image.save(path)
        paths.append(path)
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames "
                "(project_id,frame_id,source_file,width,height) "
                "VALUES (?,?,?,?,?)",
                ("P1", f"R{idx}", str(path), 640, 512),
            )
            sql.execute(
                "INSERT INTO training_samples "
                "(sample_id,project_id,source_frame_id,source_file,"
                "modality,content_sha256,label_status,rights_status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    f"S{idx}", "P1", f"R{idx}", str(path), "rgb",
                    sha256(path.read_bytes()).hexdigest(), "pending", "private",
                ),
            )
    return service, paths


class FakeGrid:
    def detect_with_diagnostics_array(self, bgr):
        assert bgr.shape == (512, 640, 3)
        return (
            ModuleDetection(
                ((40, 40), (240, 40), (240, 180), (40, 180)), .7,
            ),
        ), None


class FakeImage:
    def detect_array(self, bgr):
        return (
            ModuleDetection(
                ((50, 50), (230, 50), (230, 170), (50, 170)), .8,
            ),
        )


class FakeCadence:
    def detect_array_with_status(self, bgr):
        return (), "ambiguous_lattice_supported_cadence"


def test_verified_rgb_overlay_is_bounded_ephemeral_and_does_not_unlock_workflow(tmp_path):
    service, sources = seed(tmp_path)
    originals = tuple(p.read_bytes() for p in sources)
    result = render_imported_rgb_module_overlay(
        service.database, "P1", sample_index=1,
        grid_detector=FakeGrid(), image_detector=FakeImage(),
        cadence_detector=FakeCadence(),
    )
    assert result.sample_index == 1 and result.total == 3
    assert result.structural == result.visual == 1
    assert result.cadence == 0
    assert result.cadence_reason == "ambiguous_lattice_supported_cadence"
    assert result.read_only
    assert result.png.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(result.png)) as image:
        assert image.width <= MAX_PREVIEW_SIDE
        assert image.height <= MAX_PREVIEW_SIDE
        assert image.mode == "RGB"
    assert tuple(p.read_bytes() for p in sources) == originals
    for stage in (WorkflowStage.REVIEW, WorkflowStage.REPORT, WorkflowStage.EXPORT):
        assert not service.state("P1").readiness(stage).ready
    with service.database.connect() as sql:
        for table in ("pv_modules", "finding_reviews", "offline_processing_runs"):
            assert sql.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


@pytest.mark.parametrize("bad_index", [-1, 3, 999, True, 1.0, "1"])
def test_sample_index_is_not_a_file_selection(bad_index, tmp_path):
    service, _ = seed(tmp_path)
    with pytest.raises(ValueError, match="sample index"):
        render_imported_rgb_module_overlay(
            service.database, "P1", sample_index=bad_index,
        )


@pytest.mark.parametrize("kind", ["checksum_mismatch", "missing", "no_hash"])
def test_unverifiable_original_is_never_rendered(tmp_path, kind):
    service, paths = seed(tmp_path, count=1)
    if kind == "checksum_mismatch":
        paths[0].write_bytes(paths[0].read_bytes() + b"tamper")
    elif kind == "missing":
        paths[0].unlink()
    else:
        with service.database.connect() as sql:
            sql.execute("DELETE FROM training_samples WHERE project_id='P1'")
    class MustNotRun:
        def detect_with_diagnostics_array(self, bgr):
            raise AssertionError("bad bytes reached detector")
    with pytest.raises(ValueError, match="could not be authenticated"):
        render_imported_rgb_module_overlay(
            service.database, "P1", grid_detector=MustNotRun(),
        )


def test_cancelled_or_empty_other_project_never_produces_overlay(tmp_path):
    service, paths = seed(tmp_path, count=1)
    with pytest.raises(ModuleSampleCancelled):
        render_imported_rgb_module_overlay(
            service.database, "P1", should_cancel=lambda: True,
        )
    with pytest.raises(ValueError):
        render_imported_rgb_module_overlay(service.database, "P2")
    assert paths[0].is_file()


def test_private_detector_reason_is_never_shown_as_text(tmp_path):
    service, _ = seed(tmp_path, count=1)
    class PrivateReason:
        def detect_array_with_status(self, _):
            return (), r"C:\private\original.JPG"
    class NoneGrid:
        def detect_with_diagnostics_array(self, bgr):
            return (), None
    class NoneImage:
        def detect_array(self, bgr):
            return ()
    result = render_imported_rgb_module_overlay(
        service.database, "P1", grid_detector=NoneGrid(),
        image_detector=NoneImage(), cadence_detector=PrivateReason(),
    )
    assert result.cadence_reason == "other_quality_gate"
    assert b"private" not in result.png
