"""Privacy-safe cadence quality audit. Only synthetic JPEG fixtures."""
from __future__ import annotations

from mcm_solarcheck.gui.offline_cadence_diagnostic_text import (
    CADENCE_REASON_DE, describe_cadence_rejections,
)
from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.services.offline_cadence_diagnostics import (
    KNOWN_CADENCE_REJECTION_REASONS, safe_cadence_reason,
)
from mcm_solarcheck.services.offline_module_sample import (
    sample_imported_rgb_module_evidence,
)
from mcm_solarcheck.services.workflow import WorkflowStage


def test_codes_have_german_labels_and_unknown_strings_cannot_escape():
    assert all(k in CADENCE_REASON_DE for k in KNOWN_CADENCE_REJECTION_REASONS)
    sensitive = r"C:\Users\Private\DroneOriginal.JPG"
    assert safe_cadence_reason(sensitive) == "other_quality_gate"
    assert safe_cadence_reason(["not a code"]) == "other_quality_gate"
    rendered = describe_cadence_rejections((
        ("no_finitely_supported_cells", 1),
        ("no_spatial_overlap", 1),
        ("ambiguous_lattice_supported_phase", 1),
        (sensitive, 1),
    ))
    assert "keine ausreichend gestützten Rasterflächen" in rendered
    assert "keine ausreichende räumliche Überlappung" in rendered
    assert "mehrere gleichwertige Rasterphasen" in rendered
    assert "Private" not in rendered and "JPG" not in rendered
    assert "weiter(e)" not in rendered  # fixed labels only
    assert "nicht näher klassifizierte Qualitätsprüfung" in rendered


def test_three_frame_sample_counts_exact_rejections_and_never_persists(tmp_path):
    from hashlib import sha256
    from PIL import Image

    service = build_offline_services(tmp_path / "isolated.sqlite3").projects
    service.create_project("P1", "Synthetic")
    service.create_project("P2", "Other project")
    for i in range(3):
        path = tmp_path / f"fake-{i}.jpg"
        Image.new("RGB", (64, 48), (60, 110, 130)).save(path)
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames"
                "(project_id,frame_id,source_file,width,height)"
                " VALUES (?,?,?,?,?)",
                ("P1", f"R{i}", str(path), 64, 48),
            )
            sql.execute(
                "INSERT INTO training_samples"
                "(sample_id,project_id,source_frame_id,source_file,modality,"
                "content_sha256,label_status,rights_status)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (f"S{i}", "P1", f"R{i}", str(path), "rgb",
                 sha256(path.read_bytes()).hexdigest(), "pending", "private"),
            )

    class NoGrid:
        def detect_with_diagnostics_array(self, bgr):
            return (), None

    class NoImage:
        def detect_array(self, bgr):
            return ()

    class ThreeReasons:
        reasons = iter((
            "unresolved_cadence_phase",
            "no_finitely_supported_cells",
            "no_spatial_overlap",
        ))
        def detect_array_with_status(self, bgr):
            return (), next(self.reasons)

    result = sample_imported_rgb_module_evidence(
        service.database, "P1",
        grid_detector=NoGrid(),
        image_detector=NoImage(),
        cadence_detector=ThreeReasons(),
    )
    assert result.analyzed == 3
    assert result.cadence_rejected_phase == 1
    assert result.cadence_rejected_other == 2
    assert sum(n for _, n in result.cadence_rejection_details) == 3
    assert set(result.cadence_rejection_details) == {
        ("unresolved_cadence_phase", 1),
        ("no_finitely_supported_cells", 1),
        ("no_spatial_overlap", 1),
    }
    assert "nicht eindeutig aufgelöst" in describe_cadence_rejections(
        result.cadence_rejection_details
    )
    for stage in (WorkflowStage.REVIEW, WorkflowStage.REPORT, WorkflowStage.EXPORT):
        assert not service.state("P1").readiness(stage).ready
    with service.database.connect() as sql:
        for table in ("pv_modules", "offline_processing_runs", "finding_reviews"):
            assert sql.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert sample_imported_rgb_module_evidence(
        service.database, "P2",
        grid_detector=NoGrid(), image_detector=NoImage(),
    ).sample_size == 0


def test_untrusted_detector_status_is_counted_only_as_generic_safe_reason(tmp_path):
    from hashlib import sha256
    from PIL import Image

    service = build_offline_services(tmp_path / "isolated.sqlite3").projects
    service.create_project("P1", "Synthetic")
    path = tmp_path / "fake.jpg"
    Image.new("RGB", (64, 48), (60, 110, 130)).save(path)
    with service.database.connect() as sql:
        sql.execute(
            "INSERT INTO image_frames(project_id,frame_id,source_file,width,height)"
            " VALUES (?,?,?,?,?)", ("P1", "R1", str(path), 64, 48),
        )
        sql.execute(
            "INSERT INTO training_samples"
            "(sample_id,project_id,source_frame_id,source_file,modality,"
            "content_sha256,label_status,rights_status)"
            " VALUES (?,?,?,?,?,?,?,?)",
            ("S1", "P1", "R1", str(path), "rgb",
             sha256(path.read_bytes()).hexdigest(), "pending", "private"),
        )

    class NoGrid:
        def detect_with_diagnostics_array(self, bgr):
            return (), None
    class NoImage:
        def detect_array(self, bgr):
            return ()
    class UntrustedReason:
        def detect_array_with_status(self, bgr):
            return (), "C:/SensitiveData/drone-secret.JPG"
    result = sample_imported_rgb_module_evidence(
        service.database, "P1",
        grid_detector=NoGrid(), image_detector=NoImage(),
        cadence_detector=UntrustedReason(),
    )
    assert result.cadence_rejection_details == (("other_quality_gate", 1),)
    assert "secret" not in describe_cadence_rejections(
        result.cadence_rejection_details
    )
