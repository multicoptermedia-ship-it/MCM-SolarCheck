import pytest

from mcm_solarcheck.review.defect_classes import DefectClass
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_ground_truth_promotes_label_but_not_rights(tmp_path):
    image=tmp_path/"t.jpg"; image.write_bytes(b"thermal")
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    label=GroundTruthLabel("T1","inspector",DefectClass.THERMAL_HOTSPOT_CANDIDATE,module_id="M1")
    db.save_ground_truth("P",label)
    row=db.training_samples("P")[0]
    assert row["label_status"] == "human_reviewed"
    assert row["rights_status"] == "unverified"
    assert db.training_samples("P",trainable_only=True) == ()
    assert db.ground_truth("P","T1")[0]["module_id"] == "M1"


def test_ground_truth_requires_indexed_image(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    label=GroundTruthLabel("T1","inspector",DefectClass.NORMAL,module_id="M1")
    with pytest.raises(KeyError):
        db.save_ground_truth("P",label)


def test_ground_truth_requires_physical_reference():
    with pytest.raises(ValueError):
        GroundTruthLabel("T1","inspector",DefectClass.NORMAL)
