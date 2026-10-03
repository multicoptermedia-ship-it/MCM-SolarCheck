import pytest

from mcm_solarcheck.review.model_authorization import (
    ModelUseAuthorization,
    require_customer_project_authorization,
)
from mcm_solarcheck.review.model_candidates import PV_HSD_2025_YOLOV8S_P1
from mcm_solarcheck.review.model_validation import ModelValidationDecision


def test_customer_use_requires_verified_commercial_rights():
    auth=ModelUseAuthorization(False, ModelValidationDecision(True, ()))
    assert auth.customer_project_allowed is False
    with pytest.raises(PermissionError):
        require_customer_project_authorization(PV_HSD_2025_YOLOV8S_P1, auth)


def test_customer_use_requires_accepted_m3t_validation():
    auth=ModelUseAuthorization(
        True, ModelValidationDecision(False, ("defect recall below acceptance threshold",))
    )
    assert auth.customer_project_allowed is False
    with pytest.raises(ValueError, match="defect recall"):
        require_customer_project_authorization(PV_HSD_2025_YOLOV8S_P1, auth)


def test_customer_use_is_allowed_only_when_both_gates_pass():
    auth=ModelUseAuthorization(True, ModelValidationDecision(True, ()))
    assert auth.customer_project_allowed is True
    require_customer_project_authorization(PV_HSD_2025_YOLOV8S_P1, auth)
