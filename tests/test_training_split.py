import pytest
from mcm_solarcheck.review.training_split import split_for_sample, split_for_group, assert_no_group_leakage


def test_split_is_stable_for_same_sample():
    assert split_for_sample("thermal:abc")==split_for_sample("thermal:abc")


def test_split_returns_known_partition():
    assert split_for_sample("thermal:abc") in {"train","validation","test"}


def test_invalid_split_policy_fails_closed():
    with pytest.raises(ValueError):
        split_for_sample("thermal:abc",train=90,validation=10,test=10)


def test_same_physical_module_stays_in_one_split():
    assert split_for_group("module-42")==split_for_group("module-42")


def test_cross_split_module_leakage_is_rejected():
    with pytest.raises(ValueError,match="leakage"):
        assert_no_group_leakage([("module-42","train"),("module-42","test")])
