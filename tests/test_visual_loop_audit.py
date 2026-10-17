"""Synthetic audit coverage for independent visual loop links."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_loop_audit import audit_visual_loops


def test_identical_frames_have_consistent_direct_links():
    frame = np.random.default_rng(73).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    findings = audit_visual_loops([frame.copy() for _ in range(4)])
    assert len(findings) == 3
    assert all(f.passes and f.max_corner_error_px < 1 for f in findings)
    assert [(f.start_index, f.end_index) for f in findings] == [(0, 2), (0, 3), (1, 3)]


def test_invalid_frame_count_is_rejected():
    frame = np.zeros((256, 320, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="3-8"):
        audit_visual_loops([frame, frame])


def test_unavailable_direct_link_is_not_treated_as_success(monkeypatch):
    from mcm_solarcheck.services import visual_loop_audit as module
    frame = np.random.default_rng(73).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    original = module.estimate_visual_link
    calls = [0]

    def fail_direct(a, b):
        calls[0] += 1
        if calls[0] == 3:
            raise ValueError("no overlap")
        return original(a, b)

    monkeypatch.setattr(module, "estimate_visual_link", fail_direct)
    findings = audit_visual_loops([frame, frame, frame])
    assert len(findings) == 1
    assert not findings[0].passes
    assert findings[0].direct_inliers == 0
