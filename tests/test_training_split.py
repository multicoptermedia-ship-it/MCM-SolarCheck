import pytest
from mcm_solarcheck.review.training_split import split_for_sample


def test_split_is_stable_for_same_sample():
    assert split_for_sample("thermal:abc")==split_for_sample("thermal:abc")


def test_split_returns_known_partition():
    assert split_for_sample("thermal:abc") in {"train","validation","test"}


def test_invalid_split_policy_fails_closed():
    with pytest.raises(ValueError):
        split_for_sample("thermal:abc",train=90,validation=10,test=10)
