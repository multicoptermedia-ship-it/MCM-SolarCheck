"""Offline report drafts reuse persisted review, product gates and Phase 9 exporters."""
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pytest

from mcm_solarcheck.domain.models import Finding, PVModule, ThermalFrame
from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP, PROMOTIONAL_TRIAL
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


STAMP = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


def sample_service(tmp_path, *, ready=False):
    db = ProjectDatabase(tmp_path / "inspection.sqlite3")
    db.initialize()
    db.create_project("P1", "Solarpark Nord")
    db.create_project("P2", "Solarpark Sued")
    db.save_project_profile("P1", ProjectProfile(
        "Auftraggeber", "Anlage", "Weg 1", "50667", "Koeln",
        "Fachprueferin", site_timezone="Europe/Berlin",
    ))
    if ready:
        frame = ThermalFrame(
            frame_id="T1", source_file=Path("not-on-disk.JPG"),
            thermal_width=640, thermal_height=512, thermal_source="raw",
        )
        quality = ThermalQualityResult(
            ThermalQualityGrade.PASS, (),
            RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
        )
        db.save_thermal_frame("P1", frame, quality)
        db.save_modules("P1", (
            PVModule("M1", "T1", ((0, 0), (2, 0), (2, 2))),
        ))
        db.save_findings("P1", (
            Finding("F1", "T1", 4, 5, module_id="M1",
                    reviewer_status="confirmed"),
        ))
    return ProjectApplicationService(db)


@pytest.mark.parametrize("extension", [".pdf", ".odt", ".docx"])
def test_ready_offline_project_exports_only_a_draft(tmp_path, extension):
    service = sample_service(tmp_path, ready=True)
    output = tmp_path / f"geprueft{extension}"
    written = service.export_offline_draft(
        "P1", "ENTWURF-1", STAMP, output, capabilities=OFFLINE_DESKTOP,
    )
    assert written == output
    assert output.is_file()
    assert output.stat().st_size > 200
    assert service.import_summary("P1").confirmed_findings == 1
    if extension == ".pdf":
        assert output.read_bytes().startswith(b"%PDF")
    else:
        with ZipFile(output) as archive:
            assert archive.testzip() is None
            if extension == ".docx":
                assert "word/document.xml" in archive.namelist()
            else:
                assert "content.xml" in archive.namelist()


def test_existing_destination_cannot_be_overwritten(tmp_path):
    service = sample_service(tmp_path, ready=True)
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"important original bytes")

    with pytest.raises(FileExistsError, match="already exists"):
        service.export_offline_draft(
            "P1", "R", STAMP, output, capabilities=OFFLINE_DESKTOP,
        )
    assert output.read_bytes() == b"important original bytes"


def test_blocked_review_prohibits_draft_creation(tmp_path):
    service = sample_service(tmp_path)
    output = tmp_path / "blocked.pdf"
    with pytest.raises(ValueError, match="export action is blocked"):
        service.export_offline_draft(
            "P1", "R", STAMP, output, capabilities=OFFLINE_DESKTOP,
        )
    assert not output.exists()
    assert not tuple(tmp_path.glob(".solarcheck-draft-*"))


def test_other_project_cannot_export_this_project_evidence(tmp_path):
    service = sample_service(tmp_path, ready=True)
    output = tmp_path / "other.pdf"
    with pytest.raises(ValueError, match="export action is blocked"):
        service.export_offline_draft(
            "P2", "R", STAMP, output, capabilities=OFFLINE_DESKTOP,
        )
    assert not output.exists()


def test_invalid_product_and_path_fail_before_writing(tmp_path):
    service = sample_service(tmp_path, ready=True)
    out = tmp_path / "draft.pdf"
    with pytest.raises(PermissionError, match="offline desktop"):
        service.export_offline_draft(
            "P1", "R", STAMP, out, capabilities=PROMOTIONAL_TRIAL,
        )
    with pytest.raises(ValueError, match="PDF, ODT or DOCX"):
        service.export_offline_draft(
            "P1", "R", STAMP, tmp_path / "draft.exe",
            capabilities=OFFLINE_DESKTOP,
        )
    with pytest.raises(ValueError, match="absolute"):
        service.export_offline_draft(
            "P1", "R", STAMP, "relative.pdf", capabilities=OFFLINE_DESKTOP,
        )
    assert not out.exists()


def test_report_identity_mismatch_rejected_by_common_export_boundary(tmp_path):
    service = sample_service(tmp_path, ready=True)
    report = service.prepare_report("P1", "READY", STAMP)
    assert report.release_status == "draft"
    destination = tmp_path / "wrong-project.pdf"
    with pytest.raises(ValueError, match="does not match active project"):
        service.export_report("P2", OFFLINE_DESKTOP, report, destination)
    assert not destination.exists()


def test_unreviewed_after_previous_review_reblocks_export(tmp_path):
    service = sample_service(tmp_path, ready=True)
    service.database.save_findings(
        "P1", (Finding("F2", "T1", 7, 8, module_id="M1"),),
    )
    destination = tmp_path / "stale.pdf"
    with pytest.raises(ValueError, match="unreviewed findings remain"):
        service.export_offline_draft(
            "P1", "R", STAMP, destination, capabilities=OFFLINE_DESKTOP,
        )
    assert not destination.exists()
