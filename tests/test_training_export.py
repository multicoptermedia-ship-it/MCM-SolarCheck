from mcm_solarcheck.review.defect_classes import DefectClass
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.review.training_export import build_training_index
from mcm_solarcheck.review.training_snapshot import build_training_snapshot
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_training_index_carries_provenance_label_and_stable_split(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    image=tmp_path/"t.jpg"; image.write_bytes(b"thermal")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    db.save_ground_truth("P",GroundTruthLabel("T1","alice",DefectClass.NORMAL,module_id="M1"))
    db.approve_training_frame("P","T1",rights_approved=True)
    rows=build_training_index(build_training_snapshot(db,"P"))
    assert len(rows)==1
    row=rows[0]
    assert row["defect_class"]=="normal"
    assert row["module_id"]=="M1"
    assert row["modality"]=="thermal"
    assert len(row["content_sha256"])==64
    assert row["split"] in {"train","validation","test"}
