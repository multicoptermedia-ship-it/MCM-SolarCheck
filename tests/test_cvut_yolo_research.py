"""No model, installation, image or Torch import needed for these guards."""
import pytest

from mcm_solarcheck.vision import cvut_yolo_research as research


@pytest.mark.parametrize('variant', ['thermal', 'unknown', 'N'])
def test_only_observed_rgb_members_are_allowed(variant):
    with pytest.raises(ValueError, match='variant'):
        research.published_rgb_state(b'not-loaded', None, variant)


@pytest.mark.parametrize('variant', ['n', 's'])
def test_member_identity_is_checked_before_tensor_loading(variant):
    with pytest.raises(ValueError, match='identity'):
        research.published_rgb_state(b'not-loaded', None, variant)


@pytest.mark.parametrize('obj,name', [(object(), 'forward'),
    (research._Passive, '__dict__'), (research._Passive, 'state_dict')])
def test_serialized_attribute_lookup_cannot_call_other_methods(obj, name):
    with pytest.raises(ValueError, match='attribute'):
        research._guarded_getattr(obj, name)


def test_serialized_forward_is_never_executable():
    method = research._guarded_getattr(research._Passive, 'forward')
    with pytest.raises(ValueError, match='never execute'):
        method()


@pytest.mark.parametrize('stage', [-1, 1, 23, True])
def test_unbounded_stage_rejected_before_model_access(stage):
    with pytest.raises(ValueError, match='stage'):
        research.configure_public_training(None, None, stage)
