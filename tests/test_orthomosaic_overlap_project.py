from pathlib import Path

import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.orthomosaic_overlap_candidates import select_overlap_candidates
from mcm_solarcheck.services.orthomosaic_rgb_overlap_project import inspect_rgb_project_overlap


def test_cross_strip_candidates_are_unique_and_bounded():
    pairs = select_overlap_candidates(("a", "b", "c"), cross_strip_pairs=(("a", "c"), ("b", "a")))
    assert len(pairs) == 3
    assert pairs[-1].reason == "cross_strip"
    with pytest.raises(ValueError):
        select_overlap_candidates(("a", "b", "c"), cross_strip_pairs=(("a", "z"),))
    with pytest.raises(ValueError):
        select_overlap_candidates(("a", "b", "c"), cross_strip_pairs=(("a", "c"),), max_candidates=2)


def test_project_audit_checks_cross_strip_pixels_and_never_claims_verified(tmp_path: Path):
    rng = np.random.default_rng(2026)
    img = rng.integers(0, 256, size=(480, 560), dtype=np.uint8)
    frames = []
    for frame_id in ("a", "b", "c"):
        path = tmp_path / (frame_id + ".png")
        assert cv2.imwrite(str(path), img)
        frames.append((frame_id, path))
    audit = inspect_rgb_project_overlap(tuple(frames), cross_strip_pairs=(("a", "c"),))
    assert len(audit.results) == 3
    assert audit.connectivity.connected
    assert audit.to_summary()["candidate_count"] == 3
    assert not audit.project_overlap_verified
    assert not audit.to_summary()["project_overlap_verified"]


def test_unknown_cross_strip_is_rejected_before_decoding():
    with pytest.raises(ValueError):
        inspect_rgb_project_overlap((("a", "missing-a"), ("b", "missing-b")),
                                    cross_strip_pairs=(("a", "other"),))
