import sqlite3
from pathlib import Path

from mcm_solarcheck.domain.models import Finding, Position, RTKQuality, ThermalFrame
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def test_project_frame_and_finding_persistence(tmp_path):
    path = tmp_path / "solarcheck.sqlite"
    db = ProjectDatabase(path)
    db.initialize()
    db.create_project("P-1", "Test PV Plant")

    frame = ThermalFrame(
        frame_id="T-0001",
        source_file=Path("DJI_0001_T.JPG"),
        camera_make="DJI",
        camera_model="M3T",
        position=Position(51.0, 6.5, 112.0),
        rtk=RTKQuality(status="RTK", std_lat_m=0.01),
        thermal_width=640,
        thermal_height=512,
        thermal_source="DJI M3T APP3 raw",
        metadata={"ImageSource": "InfraredCamera"},
    )
    stats = RawThermalStatistics(17112, 22472, 19800.0, 19790.0, 20500.0, 21000.0, 5360)
    quality = ThermalQualityResult(ThermalQualityGrade.PASS, (), stats)
    db.save_thermal_frame("P-1", frame, quality)

    finding = Finding(
        finding_id="T-0001:raw:0001",
        thermal_frame_id="T-0001",
        pixel_x=100,
        pixel_y=200,
        raw_value=22000,
        raw_delta_from_median=2210.0,
        position=frame.position,
        rtk=frame.rtk,
        metadata={"temperature_status": "uncalibrated_raw"},
    )
    db.save_findings("P-1", (finding,))

    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    stored_frame = con.execute("SELECT * FROM thermal_frames").fetchone()
    stored_finding = con.execute("SELECT * FROM findings").fetchone()
    assert stored_frame["quality_grade"] == "pass"
    assert stored_frame["raw_min"] == 17112
    assert stored_frame["rtk_status"] == "RTK"
    assert stored_finding["raw_value"] == 22000
    assert stored_finding["temperature_c"] is None
    assert stored_finding["reviewer_status"] == "unreviewed"
    con.close()


def test_foreign_keys_prevent_orphan_frame(tmp_path):
    db = ProjectDatabase(tmp_path / "solarcheck.sqlite")
    db.initialize()
    frame = ThermalFrame(frame_id="T-X", source_file=Path("x.JPG"))
    stats = RawThermalStatistics(1, 2, 1.5, 1.5, 2, 2, 1)
    quality = ThermalQualityResult(ThermalQualityGrade.PASS, (), stats)
    try:
        db.save_thermal_frame("missing-project", frame, quality)
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("orphan thermal frame should violate foreign key")
