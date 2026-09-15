import sqlite3
from pathlib import Path

from mcm_solarcheck.domain.models import ImageFrame, ImagePair, PVModule, Position, ThermalFrame
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_project_import_counts_unpaired_frames():
    rgb = (ImageFrame("V-1", Path("a.JPG")), ImageFrame("V-2", Path("b.JPG")))
    class Batch:
        results = (type("R", (), {"frame": ThermalFrame("T-1", Path("t.JPG"))})(),)
    pair = ImagePair("P", "V-1", "T-1", 1.0, "sequence")
    result = ProjectImportResult(rgb, Batch(), (pair,))
    assert result.unpaired_rgb_count == 1
    assert result.unpaired_thermal_count == 0


def test_sqlite_v2_persists_rgb_pair_and_module(tmp_path):
    db = ProjectDatabase(tmp_path / "project.sqlite")
    db.initialize(); db.create_project("P-1", "PV Test")
    rgb = ImageFrame("V-0001", Path("V.JPG"), width=4000, height=3000, position=Position(51.0, 6.5))
    db.save_image_frames("P-1", (rgb,))

    # Insert minimal thermal parent row directly; thermal quality persistence is tested separately.
    with db.connect() as con:
        con.execute("INSERT INTO thermal_frames(frame_id,project_id,source_file,thermal_source) VALUES (?,?,?,?)",
                    ("T-0001", "P-1", "T.JPG", "fixture"))
    pair = ImagePair("PAIR-1", "V-0001", "T-0001", 0.99, "sequence+time+position", 0.22, 0.158)
    module = PVModule("T-0001:M-0001", "T-0001", ((10,10),(100,10),(100,80),(10,80)), 0.94, "fixture")
    db.save_pairs("P-1", (pair,)); db.save_modules("P-1", (module,))

    con = sqlite3.connect(db.path); con.row_factory = sqlite3.Row
    assert con.execute("SELECT COUNT(*) FROM image_frames").fetchone()[0] == 1
    stored_pair = con.execute("SELECT * FROM image_pairs").fetchone()
    assert stored_pair["confidence"] == 0.99
    assert stored_pair["distance_m"] == 0.22
    stored_module = con.execute("SELECT * FROM pv_modules").fetchone()
    assert stored_module["detector"] == "fixture"
    assert "100" in stored_module["polygon_json"]
    con.close()
