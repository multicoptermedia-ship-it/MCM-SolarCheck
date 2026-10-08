import json
from types import SimpleNamespace
import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.dataset_build import build_dataset
from mcm_solarcheck.review.inference_input import InferenceInput
from mcm_solarcheck.review.model_authorization import ModelUseAuthorization, require_customer_project_authorization
from mcm_solarcheck.review.model_manifest import ModelManifest
from mcm_solarcheck.review.model_release import create_model_release
from mcm_solarcheck.review.model_validation import ModelValidationDecision
from mcm_solarcheck.review.trained_model_validation import TrainedModelValidation
from mcm_solarcheck.review.model_lineage import TrainedModelArtifact


def _manifest():
    return ModelManifest("external","v1","thermal","external-dataset","permission-required","a"*64,"rendered_rgb","yolo")


def test_customer_model_fails_closed_without_rights():
    auth=ModelUseAuthorization(False,ModelValidationDecision(True,()))
    with pytest.raises(PermissionError,match="rights"):
        require_customer_project_authorization(_manifest(),auth)


def test_customer_model_fails_closed_without_validation():
    auth=ModelUseAuthorization(True,ModelValidationDecision(False,("representative M3T validation missing",)))
    with pytest.raises(ValueError,match="validation"):
        require_customer_project_authorization(_manifest(),auth)


def test_raw_radiometric_input_cannot_enter_rendered_model():
    with pytest.raises(ValueError,match="rendered image"):
        InferenceInput(object(),"radiometric_raw","T1")


def test_rejected_trained_model_cannot_be_released():
    artifact=TrainedModelArtifact("r"*64,"a"*64,"pt")
    validation=TrainedModelValidation(artifact,ModelValidationDecision(False,("failed acceptance",)),"inspector")
    with pytest.raises(ValueError,match="failed acceptance"):
        create_model_release(validation)


def test_empty_snapshot_cannot_become_dataset(tmp_path):
    snapshot=SimpleNamespace(snapshot_id="s"*64,manifest_json=json.dumps({"samples":[],"labels":[]}))
    with pytest.raises(ValueError,match="at least one"):
        build_dataset(snapshot)


def test_machine_suggestion_never_changes_human_status_by_metadata():
    finding=Finding("F","T",1,1,module_id="M",metadata={"classification_status":"suggested","classification_label":"thermal_hotspot_candidate"})
    assert finding.reviewer_status=="unreviewed"
