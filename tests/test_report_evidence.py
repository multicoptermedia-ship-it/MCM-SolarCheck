from pathlib import Path
import pytest
from mcm_solarcheck.reporting.evidence import EvidenceImagePlan,plan_evidence_images

def test_evidence_plan_keeps_thermal_pixel_but_does_not_guess_rgb_marker():
    plan=plan_evidence_images(finding_id='F-1',thermal_source='T.JPG',pixel_x=123,pixel_y=45,rgb_source='V.JPG',pairing_confidence=.99,pairing_method='sequence+time+position')
    assert plan.thermal_pixel==(123,45);assert plan.rgb_source==Path('V.JPG');assert plan.rgb_marker is None

def test_rgb_marker_requires_rgb_source():
    with pytest.raises(ValueError):EvidenceImagePlan('F-1',Path('T.JPG'),(1,2),rgb_marker=(10.,20.))

def test_invalid_pairing_confidence_is_rejected():
    with pytest.raises(ValueError):plan_evidence_images(finding_id='F-1',thermal_source='T.JPG',pixel_x=1,pixel_y=2,pairing_confidence=1.1)
