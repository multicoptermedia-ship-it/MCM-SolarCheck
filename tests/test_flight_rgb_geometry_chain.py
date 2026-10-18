"""Synthetic geometry-chain regression tests; no private DJI captures."""
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_geometry_chain import chain_rgb_links


def test_chain_preserves_order_and_translation():
    move = [[1, 0, 12], [0, 1, 5], [0, 0, 1]]
    links = [
        {"first": "a", "second": "b", "status": "registered", "homography": move},
        {"first": "b", "second": "c", "status": "registered", "homography": move},
    ]
    result = chain_rgb_links(links)
    assert len(result["segments"]) == 1
    assert result["metric_orthophoto_verified"] is False
    np.testing.assert_allclose(result["segments"][0]["frames"]["c"],
                               [[1, 0, 24], [0, 1, 10], [0, 0, 1]])


def test_failure_breaks_chain_instead_of_inventing_alignment():
    identity = np.eye(3).tolist()
    links = [
        {"first": "a", "second": "b", "status": "failed"},
        {"first": "b", "second": "c", "status": "registered", "homography": identity},
    ]
    result = chain_rgb_links(links)
    assert len(result["segments"]) == 2
    assert "c" not in result["segments"][0]["frames"]
    assert list(result["segments"][1]["frames"]) == ["b", "c"]


def test_invalid_matrix_rejected():
    with pytest.raises(ValueError, match="invalid homography"):
        chain_rgb_links([{"first": "a", "second": "b",
                          "status": "registered", "homography": [[1, 2]]}])
