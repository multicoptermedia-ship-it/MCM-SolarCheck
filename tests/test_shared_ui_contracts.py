"""Checks for the shared, non-authoritative presentation contract."""
import pytest

from shared_ui.contracts import FindingView, RuntimeInfo, RuntimeMode


def test_runtime_modes():
    assert RuntimeInfo(RuntimeMode.ONLINE).to_dict() == {"mode": "online", "features_ready": False}
    assert RuntimeInfo(RuntimeMode.OFFLINE).to_dict()["mode"] == "offline"


def test_finding_view():
    finding = FindingView("M12", "hotspot", 0.85, "unreviewed")
    assert finding.to_dict()["finding_type"] == "hotspot"


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_invalid_confidence(confidence):
    with pytest.raises(ValueError):
        FindingView("M12", "hotspot", confidence, "unreviewed")
