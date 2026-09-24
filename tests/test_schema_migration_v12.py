from mcm_solarcheck.review.defect_classes import DefectClass
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.review.training_geometry import ReviewedGeometry
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_v11_database_migrates_to_v12_and_preserves_corpus(tmp_path):
    path=tmp_path/"p.sqlite"
    db=ProjectDatabase(path)
    # Build the historical v11 shape through the current v10->v11 migration helper path
    import sqlite3
    with sqlite3.connect(path) as raw:
        raw.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE schema_info(version INTEGER NOT NULL);
        INSERT INTO schema_info VALUES(11);
        CREATE TABLE projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE training_labels(label_id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,source_frame_id TEXT NOT NULL,module_id TEXT,finding_id TEXT,defect_class TEXT NOT NULL,reviewer TEXT NOT NULL,supersedes_label_id INTEGER REFERENCES training_labels(label_id),note TEXT,inspection_group_id TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE training_samples(sample_id TEXT NOT NULL,project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,source_frame_id TEXT NOT NULL,source_file TEXT NOT NULL,modality TEXT NOT NULL CHECK(modality IN ('thermal','rgb')),content_sha256 TEXT NOT NULL,label_status TEXT NOT NULL,rights_status TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(project_id,source_frame_id,modality));
        INSERT INTO projects(project_id,name) VALUES('P','Project');
        INSERT INTO training_samples VALUES('thermal:abc','P','T1','t.jpg','thermal','abc','human_reviewed','approved',CURRENT_TIMESTAMP);
        """)
    db.initialize()
    with db.connect() as check:
        assert check.execute("SELECT version FROM schema_info").fetchone()[0]==12
        assert check.execute("SELECT COUNT(*) FROM training_samples").fetchone()[0]==1
        assert check.execute("SELECT COUNT(*) FROM training_geometries").fetchone()[0]==0


def test_reviewed_geometry_is_bound_to_exact_ground_truth(tmp_path):
    image=tmp_path/"t.jpg"; image.write_bytes(b"thermal")
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    db.save_ground_truth("P",GroundTruthLabel("T1","alice",DefectClass.THERMAL_HOTSPOT_CANDIDATE,module_id="M1"))
    label_id=db.ground_truth("P","T1")[0]["label_id"]
    geometry=ReviewedGeometry("T1","alice","rendered_rgb",box_xyxy=(1,2,20,30))
    db.save_training_geometry("P",label_id,geometry)
    row=db.training_geometries("P","T1")[0]
    assert row["label_id"]==label_id
    assert row["box_xyxy"]==(1,2,20,30)
