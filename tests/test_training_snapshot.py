from mcm_solarcheck.review.defect_classes import DefectClass
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.review.training_snapshot import build_training_snapshot, write_training_snapshot
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_snapshot_contains_only_rights_approved_reviewed_data_and_is_stable(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    image=tmp_path/"t.jpg"; image.write_bytes(b"thermal")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    db.save_ground_truth("P",GroundTruthLabel("T1","alice",DefectClass.NORMAL,module_id="M1"))
    assert build_training_snapshot(db,"P").sample_count==0
    db.approve_training_frame("P","T1",rights_approved=True)
    first=build_training_snapshot(db,"P")
    second=build_training_snapshot(db,"P")
    assert first.sample_count==1 and first.label_count==1
    assert first.snapshot_id==second.snapshot_id


def test_snapshot_uses_latest_correction_without_erasing_audit(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    image=tmp_path/"t.jpg"; image.write_bytes(b"thermal")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    db.save_ground_truth("P",GroundTruthLabel("T1","alice",DefectClass.THERMAL_HOTSPOT_CANDIDATE,module_id="M1"))
    first=db.ground_truth("P")[0]
    db.save_ground_truth("P",GroundTruthLabel("T1","bob",DefectClass.NORMAL,module_id="M1",supersedes_label_id=first["label_id"]))
    db.approve_training_frame("P","T1",rights_approved=True)
    snapshot=build_training_snapshot(db,"P")
    assert '"defect_class":"normal"' in snapshot.manifest_json
    assert snapshot.label_count==1
    assert len(db.ground_truth("P"))==2


def test_snapshot_manifest_write_is_idempotent_but_immutable(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    image=tmp_path/"t.jpg"; image.write_bytes(b"thermal")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    db.save_ground_truth("P",GroundTruthLabel("T1","alice",DefectClass.NORMAL,module_id="M1"))
    db.approve_training_frame("P","T1",rights_approved=True)
    snapshot=build_training_snapshot(db,"P")
    target=tmp_path/"snapshots"/(snapshot.snapshot_id+".json")
    write_training_snapshot(snapshot,target)
    write_training_snapshot(snapshot,target)
    assert target.read_text(encoding="utf-8")==snapshot.manifest_json
    target.write_text("tampered",encoding="utf-8")
    import pytest
    with pytest.raises(FileExistsError):
        write_training_snapshot(snapshot,target)
