from datetime import datetime, timezone
from pathlib import Path

import pytest

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.review.findings import ReviewStatus, review_finding
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def _database(tmp_path):
    db = ProjectDatabase(tmp_path / "review.sqlite")
    db.initialize(); db.create_project("P-1", "Review Test")
    frame = ThermalFrame(frame_id="T-1", source_file=Path("T.JPG"), thermal_width=640, thermal_height=512, thermal_source="raw")
    stats = RawThermalStatistics(1, 1000, 500, 500, 900, 990, 999)
    db.save_thermal_frame("P-1", frame, ThermalQualityResult(ThermalQualityGrade.PASS, (), stats))
    finding = Finding("F-1", "T-1", 10, 20, raw_value=900)
    db.save_findings("P-1", (finding,))
    return db, finding


def test_human_review_updates_status_and_keeps_audit_history(tmp_path):
    db, finding = _database(tmp_path)
    reviewed, audit = review_finding(finding, status=ReviewStatus.CONFIRMED, reviewer="Inspector A", note="Visible hotspot pattern", reviewed_at_utc=datetime(2026,1,1,tzinfo=timezone.utc))
    assert reviewed.reviewer_status == "confirmed"
    assert reviewed.metadata["review_source"] == "human"
    db.save_review(audit)
    with db.connect() as con:
        assert con.execute("SELECT reviewer_status FROM findings WHERE finding_id='F-1'").fetchone()[0] == "confirmed"
        row = con.execute("SELECT status, reviewer, note FROM finding_reviews WHERE finding_id='F-1'").fetchone()
        assert tuple(row) == ("confirmed", "Inspector A", "Visible hotspot pattern")


def test_review_requires_named_reviewer():
    with pytest.raises(ValueError):
        review_finding(Finding("F", "T", 1, 1), status=ReviewStatus.REJECTED, reviewer=" ")


def test_completed_review_cannot_be_unreviewed():
    with pytest.raises(ValueError):
        review_finding(Finding("F", "T", 1, 1), status=ReviewStatus.UNREVIEWED, reviewer="Inspector")
