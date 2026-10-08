from mcm_solarcheck.review.defect_classes import DefectClass
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.storage.sqlite import ProjectDatabase
import pytest


def _db(tmp_path):
    image=tmp_path/"t.jpg"; image.write_bytes(b"thermal")
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    return db


def test_ground_truth_correction_is_append_only(tmp_path):
    db=_db(tmp_path)
    db.save_ground_truth("P",GroundTruthLabel("T1","alice",DefectClass.THERMAL_HOTSPOT_CANDIDATE,module_id="M1"))
    first=db.ground_truth("P")[0]
    db.save_ground_truth("P",GroundTruthLabel("T1","bob",DefectClass.NORMAL,module_id="M1",supersedes_label_id=first["label_id"],note="false positive"))
    history=db.ground_truth("P")
    assert len(history)==2
    assert history[0]["defect_class"]=="thermal_hotspot_candidate"
    assert history[1]["defect_class"]=="normal"
    assert history[1]["supersedes_label_id"]==history[0]["label_id"]


def test_correction_cannot_move_to_another_module(tmp_path):
    db=_db(tmp_path)
    db.save_ground_truth("P",GroundTruthLabel("T1","alice",DefectClass.NORMAL,module_id="M1"))
    label_id=db.ground_truth("P")[0]["label_id"]
    with pytest.raises(ValueError,match="physical reference"):
        db.save_ground_truth("P",GroundTruthLabel("T1","bob",DefectClass.NORMAL,module_id="M2",supersedes_label_id=label_id))
