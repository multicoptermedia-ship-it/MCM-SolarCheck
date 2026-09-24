import sqlite3
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_v10_training_corpus_migrates_without_losing_provenance(tmp_path):
    path=tmp_path/"legacy.sqlite"
    db=sqlite3.connect(path)
    db.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE schema_info(version INTEGER NOT NULL);
    INSERT INTO schema_info VALUES(10);
    CREATE TABLE projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    INSERT INTO projects(project_id,name) VALUES('P1','Legacy');
    CREATE TABLE training_samples(
      sample_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
      source_frame_id TEXT NOT NULL,source_file TEXT NOT NULL,modality TEXT NOT NULL,
      content_sha256 TEXT NOT NULL,label_status TEXT NOT NULL,rights_status TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    INSERT INTO training_samples(sample_id,project_id,source_frame_id,source_file,modality,content_sha256,label_status,rights_status)
      VALUES('thermal:abc','P1','T1','legacy.jpg','thermal','abc','human_reviewed','approved');
    """)
    db.commit(); db.close()

    project=ProjectDatabase(path); project.initialize()
    rows=project.training_samples("P1")
    assert len(rows)==1
    assert rows[0]["source_frame_id"]=="T1"
    assert rows[0]["rights_status"]=="approved"
    with sqlite3.connect(path) as check:
        assert check.execute("SELECT version FROM schema_info").fetchone()[0]==11
        pk={row[1]:row[5] for row in check.execute("PRAGMA table_info(training_samples)")}
        assert pk["project_id"]==1
        assert pk["source_frame_id"]==2
        assert pk["modality"]==3
