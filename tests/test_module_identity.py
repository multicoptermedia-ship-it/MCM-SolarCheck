import pytest

from mcm_solarcheck.vision.module_identity import ModuleIdentityTracker, ModuleObservation


def obs(frame, local, x, y, width=100, height=160):
    return ModuleObservation(frame, local, (x, y), width, height)


def test_reuses_identity_across_frames_for_same_module():
    tracker = ModuleIdentityTracker()
    first = tracker.assign(obs("V-0001", "det-1", 100, 100))
    second = tracker.assign(obs("V-0002", "det-7", 108, 102))
    assert first.module_id == "M-0001"
    assert second.module_id == "M-0001"
    assert second.status == "matched"


def test_far_observation_gets_new_physical_identity():
    tracker = ModuleIdentityTracker()
    tracker.assign(obs("V-0001", "det-1", 100, 100))
    result = tracker.assign(obs("V-0002", "det-2", 300, 100))
    assert result.module_id == "M-0002"
    assert result.status == "new"


def test_close_competing_modules_are_ambiguous_not_guessed():
    tracker = ModuleIdentityTracker(max_normalized_distance=0.6, ambiguity_margin=0.2)
    tracker.assign(obs("V-0001", "a", 100, 100))
    tracker.assign(obs("V-0001", "b", 140, 100))
    result = tracker.assign(obs("V-0002", "c", 120, 100))
    assert result.module_id is None
    assert result.status == "ambiguous"


def test_two_observations_in_same_frame_do_not_share_identity():
    tracker = ModuleIdentityTracker(max_normalized_distance=1.0)
    first = tracker.assign(obs("V-0001", "a", 100, 100))
    second = tracker.assign(obs("V-0001", "b", 105, 100))
    assert first.module_id != second.module_id


def test_invalid_module_size_is_rejected():
    with pytest.raises(ValueError):
        obs("V-0001", "a", 0, 0, width=0)
