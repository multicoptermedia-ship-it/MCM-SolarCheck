"""Synthetic coverage regression tests for the user's real 29/36 M3T dataset layout."""
from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile

import pytest

from mcm_solarcheck.domain.models import Finding, ImagePair
from mcm_solarcheck.importers.batch import M3TBatchResult, M3TBatchSummary
from mcm_solarcheck.importers.m3t_archive_inventory import inspect_m3t_archives
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import IncompleteImportError
from mcm_solarcheck.services.vertical_partial_m3t_analysis import analyze_partial_m3t_project


def make_zip(path, sequences, suffix):
    with ZipFile(path, "w") as zf:
        for seq in sequences:
            zf.writestr(f"DJI_20250825121339_{seq:04d}_{suffix}.JPG", b"placeholder")


def test_29_paired_7_thermal_only_without_original_images(tmp_path):
    thermal, rgb = tmp_path / "thermal.zip", tmp_path / "rgb.zip"
    make_zip(thermal, range(1, 37), "T")
    make_zip(rgb, range(1, 30), "V")
    result = inspect_m3t_archives(thermal, rgb)
    assert result.thermal_files == 36
    assert result.rgb_files == 29
    assert len(result.paired_sequences) == 29
    assert result.thermal_only_sequences == tuple(f"{i:04d}" for i in range(30, 37))
    assert not result.rgb_only_sequences


def test_rejects_archive_traversal(tmp_path):
    thermal, rgb = tmp_path / "thermal.zip", tmp_path / "rgb.zip"
    with ZipFile(thermal, "w") as zf:
        zf.writestr("../DJI_20250825121339_0001_T.JPG", b"bad")
    make_zip(rgb, [1], "V")
    with pytest.raises(ValueError):
        inspect_m3t_archives(thermal, rgb)


def fake_import():
    from types import SimpleNamespace
    rgb = tuple(SimpleNamespace(frame_id=f"V-{i:04d}") for i in range(1, 30))
    results = tuple(
        SimpleNamespace(
            frame=SimpleNamespace(frame_id=f"T-{i:04d}"),
            findings=(Finding(f"finding-{i}", f"T-{i:04d}", 1, 1),),
        ) for i in range(1, 37)
    )
    pairs = tuple(
        ImagePair(f"pair-{i}", f"V-{i:04d}", f"T-{i:04d}", .95, "test")
        for i in range(1, 30)
    )
    batch = M3TBatchResult(results, (), M3TBatchSummary(36, 36, 0, 36, 0, 0, 36))
    return ProjectImportResult(rgb, batch, pairs)


def test_partial_analysis_is_explicit_and_preserves_unmatched():
    imported = fake_import()
    with pytest.raises(IncompleteImportError):
        analyze_partial_m3t_project(imported)
    result = analyze_partial_m3t_project(imported, acknowledge_incomplete_coverage=True)
    assert result.paired_analysis.paired_frames == 29
    assert len(result.paired_analysis.candidates) == 29
    assert len(result.unpaired_thermal_frame_ids) == 7
    assert "T-0036" in result.unpaired_thermal_frame_ids
    assert result.completeness == "partial_rgb_thermal_coverage"


def test_changed_decisions_require_fresh_approval(tmp_path):
    from mcm_solarcheck.services.vertical_local_review_draft import LocalReviewDraft
    from mcm_solarcheck.services.vertical_local_report_controller import LocalReviewedReportController
    from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
    from mcm_solarcheck.services.vertical_report_adapter import ReportContext
    analysis = ImportedCandidateAnalysis(
        1, 1, (Finding("candidate-1", "T-0001", 1, 2, module_id="module-1"),)
    )
    draft = LocalReviewDraft(analysis)
    context = ReportContext(
        "report", "project", "Customer", "Site",
        datetime(2026, 10, 11, tzinfo=timezone.utc), "expert", 1, "test",
    )
    controller = LocalReviewedReportController(draft, context)
    draft.decide("candidate-1", "accept")
    controller.approve(reviewer_id="expert", evidence_reference="signed")
    draft.decide("candidate-1", "reject")
    with pytest.raises(PermissionError, match="changed"):
        controller.export(tmp_path / "stale.pdf", authorize_export=lambda project: True)
