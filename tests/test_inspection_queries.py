from pathlib import Path

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.storage.queries import InspectionQueries
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def _fixture_db(tmp_path):
    db = ProjectDatabase(tmp_path / "queries.sqlite")
    db.initialize()
    db.create_project("P-1", "Inspection")
    frame = ThermalFrame(
        frame_id="T-0001", source_file=Path("T.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    stats = RawThermalStatistics(17000, 22000, 19500, 19400, 21000, 21500, 5000)
    quality = ThermalQualityResult(ThermalQualityGrade.PASS, (), stats)
    db.save_thermal_frame("P-1", frame, quality)
    db.save_findings("P-1", (
        Finding("F-1", "T-0001", 10, 20, raw_value=21000, reviewer_status="confirmed"),
        Finding("F-2", "T-0001", 30, 40, raw_value=20500, reviewer_status="unreviewed"),
    ))
    return db


def test_summary_separates_review_and_calibration_state(tmp_path):
    queries = InspectionQueries(_fixture_db(tmp_path))
    summary = queries.summary("P-1")
    assert summary.thermal_frames == 1
    assert summary.findings == 2
    assert summary.confirmed_findings == 1
    assert summary.unreviewed_findings == 1
    assert summary.calibrated_findings == 0


def test_confirmed_findings_are_report_ready_but_keep_celsius_null(tmp_path):
    queries = InspectionQueries(_fixture_db(tmp_path))
    findings = queries.findings("P-1", confirmed_only=True)
    assert [finding.finding_id for finding in findings] == ["F-1"]
    assert findings[0].raw_value == 21000
    assert findings[0].temperature_c is None


def test_unknown_project_summary_fails_explicitly(tmp_path):
    db = ProjectDatabase(tmp_path / "empty.sqlite")
    db.initialize()
    queries = InspectionQueries(db)
    try:
        queries.summary("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown project must not return an empty summary")


def test_summary_counts_only_provenanced_celsius_as_calibrated(tmp_path):
    db=_fixture_db(tmp_path)
    db.save_findings("P-1", (
        Finding("F-CAL", "T-0001", 50, 60, temperature_c=42.5, metadata={"temperature_status":"calibrated","temperature_provider":"reference"}),
        Finding("F-NUM", "T-0001", 70, 80, temperature_c=43.0),
        Finding("F-STATUS", "T-0001", 90, 100, temperature_c=44.0, metadata={"temperature_status":"calibrated"}),
    ))
    assert InspectionQueries(db).summary("P-1").calibrated_findings == 1


def test_malformed_temperature_metadata_fails_closed(tmp_path):
    db=_fixture_db(tmp_path)
    db.save_findings("P-1", (Finding("F-BAD", "T-0001", 50, 60, temperature_c=42.5),))
    with db.connect() as conn:
        conn.execute("UPDATE findings SET metadata_json=? WHERE project_id=? AND finding_id=?", ("{broken", "P-1", "F-BAD"))
    queries=InspectionQueries(db)
    assert queries.summary("P-1").calibrated_findings == 0
    record=next(item for item in queries.findings("P-1") if item.finding_id=="F-BAD")
    assert record.temperature_status is None
    assert record.temperature_provider is None


def test_non_object_temperature_metadata_fails_closed(tmp_path):
    db=_fixture_db(tmp_path)
    db.save_findings("P-1", (Finding("F-LIST", "T-0001", 50, 60, temperature_c=42.5),))
    with db.connect() as conn:
        conn.execute("UPDATE findings SET metadata_json=? WHERE project_id=? AND finding_id=?", ('["calibrated"]', "P-1", "F-LIST"))
    queries=InspectionQueries(db)
    assert queries.summary("P-1").calibrated_findings == 0
    record=next(item for item in queries.findings("P-1") if item.finding_id=="F-LIST")
    assert record.temperature_status is None
    assert record.temperature_provider is None


def test_nonfinite_provenanced_celsius_is_not_counted_as_calibrated(tmp_path):
    db=_fixture_db(tmp_path)
    db.save_findings("P-1", (
        Finding("F-NAN", "T-0001", 50, 60, temperature_c=float("nan"), metadata={"temperature_status":"calibrated","temperature_provider":"reference"}),
    ))
    assert InspectionQueries(db).summary("P-1").calibrated_findings == 0
