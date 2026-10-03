import pytest

from mcm_solarcheck.review.dataset_build import build_dataset
from mcm_solarcheck.review.defect_classes import DefectClass
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.review.training_snapshot import build_training_snapshot
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def _snapshot(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    image=tmp_path/"t.jpg"; image.write_bytes(b"thermal")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    db.save_ground_truth("P",GroundTruthLabel("T1","alice",DefectClass.NORMAL,module_id="M1",inspection_group_id="flight-1"))
    db.approve_training_frame("P","T1",rights_approved=True)
    return db, image, build_training_snapshot(db,"P")


def test_dataset_build_records_snapshot_distribution_and_is_stable(tmp_path):
    _,_,snapshot=_snapshot(tmp_path)
    a=build_dataset(snapshot); b=build_dataset(snapshot)
    assert a.dataset_id==b.dataset_id
    assert a.snapshot_id==snapshot.snapshot_id
    assert a.sample_count==1
    assert a.class_counts=={"normal":1}
    assert sum(a.split_counts.values())==1


def test_dataset_build_rejects_changed_image_bytes(tmp_path):
    _,image,snapshot=_snapshot(tmp_path)
    image.write_bytes(b"tampered")
    with pytest.raises(ValueError,match="SHA-256 changed"):
        build_dataset(snapshot)


def test_dataset_build_rejects_missing_image(tmp_path):
    _,image,snapshot=_snapshot(tmp_path)
    image.unlink()
    with pytest.raises(FileNotFoundError):
        build_dataset(snapshot)
