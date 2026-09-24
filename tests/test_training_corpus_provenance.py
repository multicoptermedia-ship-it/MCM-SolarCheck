from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_identical_bytes_remain_separate_project_sources(tmp_path):
    image=tmp_path/"same.jpg"; image.write_bytes(b"same bytes")
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize()
    db.create_project("P1","One"); db.create_project("P2","Two")
    sample=index_m3t_training_sample("F1",image,"thermal")
    db.save_training_samples("P1",[sample])
    db.save_training_samples("P2",[sample])
    assert len(db.training_samples("P1"))==1
    assert len(db.training_samples("P2"))==1
    db.approve_training_frame("P1","F1",rights_approved=True)
    assert db.training_samples("P1")[0]["rights_status"]=="approved"
    assert db.training_samples("P2")[0]["rights_status"]=="unverified"


def test_identical_bytes_can_preserve_multiple_source_occurrences(tmp_path):
    image=tmp_path/"same.jpg"; image.write_bytes(b"same bytes")
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    a=index_m3t_training_sample("F1",image,"thermal")
    b=index_m3t_training_sample("F2",image,"thermal")
    assert a.sample_id==b.sample_id
    db.save_training_samples("P",[a,b])
    rows=db.training_samples("P")
    assert {r["source_frame_id"] for r in rows}=={"F1","F2"}
