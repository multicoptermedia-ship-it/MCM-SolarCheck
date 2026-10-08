import pytest
from mcm_solarcheck.review.classification import DefectClassification


def test_malformed_external_strings_fail_closed():
    with pytest.raises(ValueError):
        DefectClassification(None,0.5,"provider")
    with pytest.raises(ValueError):
        DefectClassification("normal",0.5,None)
    with pytest.raises(ValueError):
        DefectClassification("normal",0.5,"provider",model_version=123)
