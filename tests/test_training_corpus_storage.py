from dataclasses import replace

from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_training_corpus_roundtrip_and_trainable_filter(tmp_path):
    db=ProjectDatabase(tmp_path / "project.sqlite")
    db.initialize()
    db.create_project("P1", "Project")
    image=tmp_path / "thermal.jpg"
    image.write_bytes(b"m3t")
    pending=index_m3t_training_sample("T-1", image, "thermal")
    db.save_training_samples("P1", [pending])
    rows=db.training_samples("P1")
    assert len(rows) == 1
    assert rows[0]["label_status"] == "unlabeled"
    assert db.training_samples("P1", trainable_only=True) == ()

    approved=replace(pending, label_status="human_reviewed", rights_status="approved")
    db.save_training_samples("P1", [approved])
    trainable=db.training_samples("P1", trainable_only=True)
    assert len(trainable) == 1
    assert trainable[0]["sample_id"] == pending.sample_id


def test_training_corpus_deduplicates_same_content(tmp_path):
    db=ProjectDatabase(tmp_path / "project.sqlite")
    db.initialize(); db.create_project("P1", "Project")
    a=tmp_path/"a.jpg"; b=tmp_path/"b.jpg"
    a.write_bytes(b"same"); b.write_bytes(b"same")
    db.save_training_samples("P1", [
        index_m3t_training_sample("T-1", a, "thermal"),
        index_m3t_training_sample("T-2", b, "thermal"),
    ])
    assert len(db.training_samples("P1")) == 1
