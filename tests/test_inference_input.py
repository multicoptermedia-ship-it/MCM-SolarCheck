import pytest

from mcm_solarcheck.review.inference_input import InferenceInput, require_preprocessing_contract


def test_rendered_input_can_satisfy_exact_model_contract():
    image=object()
    value=InferenceInput(image, "rendered_rgb", "T-1")
    assert require_preprocessing_contract(value, "rendered_rgb") is image


def test_raw_radiometric_representation_is_rejected():
    with pytest.raises(ValueError, match="explicitly rendered"):
        InferenceInput(object(), "radiometric_raw", "T-1")


def test_preprocessing_mismatch_fails_closed():
    value=InferenceInput(object(), "grayscale_8bit", "T-1")
    with pytest.raises(ValueError, match="expects rendered_rgb"):
        require_preprocessing_contract(value, "rendered_rgb")
