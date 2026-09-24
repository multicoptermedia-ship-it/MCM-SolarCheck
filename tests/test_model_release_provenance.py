from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.model_release import ModelRelease, attach_release_provenance


def test_release_provenance_does_not_change_human_review_state():
    finding=Finding("F1","T1",1,2,reviewer_status="confirmed",metadata={"review_source":"human"})
    release=ModelRelease("x"*64,"r"*64,"a"*64,"inspector")
    result=attach_release_provenance(finding,release,dataset_id="d"*64,snapshot_id="s"*64)
    assert result.reviewer_status=="confirmed"
    assert result.metadata["review_source"]=="human"
    assert result.metadata["classification_release_id"]=="x"*64
    assert result.metadata["classification_training_run_id"]=="r"*64
    assert result.metadata["classification_dataset_id"]=="d"*64
    assert result.metadata["classification_snapshot_id"]=="s"*64
