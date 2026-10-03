from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.advisory_pipeline import apply_yolo_advisory
from mcm_solarcheck.review.dataset_build import build_dataset
from mcm_solarcheck.review.defect_classes import DatasetClassMap, DefectClass
from mcm_solarcheck.review.findings import ReviewStatus, review_finding
from mcm_solarcheck.review.ground_truth import GroundTruthLabel
from mcm_solarcheck.review.inference_evidence import ModuleInferenceEvidence
from mcm_solarcheck.review.model_lineage import TrainingRun
from mcm_solarcheck.review.model_manifest import ModelManifest
from mcm_solarcheck.review.model_release import attach_release_provenance, create_model_release
from mcm_solarcheck.review.model_validation import ModelValidationDecision
from mcm_solarcheck.review.trained_model_validation import TrainedModelValidation
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample
from mcm_solarcheck.review.training_runner import execute_training
from mcm_solarcheck.review.training_snapshot import build_training_snapshot
from mcm_solarcheck.review.yolo_adapter import YoloAdapter, YoloDetection
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_phase7_reviewed_data_to_validated_advisory_to_human_decision(tmp_path):
    image=tmp_path/"thermal.jpg"; image.write_bytes(b"representative-m3t-render")
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    db.save_training_samples("P",[index_m3t_training_sample("T1",image,"thermal")])
    db.save_ground_truth("P",GroundTruthLabel("T1","inspector",DefectClass.THERMAL_HOTSPOT_CANDIDATE,module_id="M1",inspection_group_id="flight-1"))
    db.approve_training_frame("P","T1",rights_approved=True)

    snapshot=build_training_snapshot(db,"P")
    dataset=build_dataset(snapshot)
    assert snapshot.sample_count==1 and dataset.sample_count==1

    run=TrainingRun(dataset.dataset_id,snapshot.snapshot_id,"controlled-test-trainer","1","rendered_rgb",{"epochs":1,"seed":42})
    def trainer(_dataset,_run):
        weights=tmp_path/"model.pt"; weights.write_bytes(b"validated-weights"); return weights
    artifact=execute_training(dataset,run,trainer=trainer)
    validation=TrainedModelValidation(artifact,ModelValidationDecision(True,()),"validation-inspector")
    release=create_model_release(validation)

    class_map=DatasetClassMap("mcm-e2e",{"hotspot":DefectClass.THERMAL_HOTSPOT_CANDIDATE})
    adapter=YoloAdapter("mcm-trained",release.release_id,class_map,"thermal")
    manifest=ModelManifest("mcm-trained",release.release_id,"thermal","MCM reviewed corpus","internal-reviewed-data",artifact.weights_sha256,"rendered_rgb","controlled-test")
    finding=Finding("F1","T1",10,10,module_id="M1")
    advisory=apply_yolo_advisory(
        finding,
        detections=(YoloDetection("hotspot",0.91,(1,1,20,20)),),
        adapter=adapter,
        evidence=ModuleInferenceEvidence("M1","T1","thermal",(0,0,100,100)),
        manifest=manifest,
    )
    advisory=attach_release_provenance(advisory,release,dataset_id=dataset.dataset_id,snapshot_id=snapshot.snapshot_id)
    assert advisory.reviewer_status=="unreviewed"
    assert advisory.metadata["classification_status"]=="suggested"
    assert advisory.metadata["classification_release_id"]==release.release_id

    reviewed,audit=review_finding(advisory,status=ReviewStatus.CONFIRMED,reviewer="human-inspector")
    assert reviewed.reviewer_status=="confirmed"
    assert reviewed.metadata["review_source"]=="human"
    assert reviewed.metadata["classification_release_id"]==release.release_id
    assert audit.status is ReviewStatus.CONFIRMED
