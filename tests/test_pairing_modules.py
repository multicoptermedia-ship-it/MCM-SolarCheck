from datetime import datetime, timezone
from pathlib import Path

from mcm_solarcheck.domain.models import Finding, ImageFrame, Position, PVModule, ThermalFrame
from mcm_solarcheck.pairing.rgb_thermal import pair_rgb_thermal_frames, pair_score
from mcm_solarcheck.vision.modules import assign_findings_to_modules, point_in_polygon


def test_pair_score_combines_sequence_time_and_position():
    rgb = ImageFrame("V-0001", Path("DJI_20250825121338_0001_V.JPG"),
        timestamp_utc=datetime(2025, 8, 25, 10, 13, 38, tzinfo=timezone.utc),
        position=Position(51.05624731, 6.56007931, 112.992))
    thermal = ThermalFrame("T-0001", Path("DJI_20250825121339_0001_T.JPG"),
        timestamp_utc=datetime(2025, 8, 25, 10, 13, 38, 158000, tzinfo=timezone.utc),
        position=Position(51.05624731, 6.56007897, 112.998))
    score, method, distance, dt = pair_score(rgb, thermal)
    assert score == 1.0
    assert method == "sequence+time+position"
    assert distance < 0.5
    assert dt < 0.25


def test_pairing_is_unique():
    rgb = (ImageFrame("V-0001", Path("DJI_x_0001_V.JPG")),)
    thermals = (
        ThermalFrame("T-0001", Path("DJI_x_0001_T.JPG")),
        ThermalFrame("T-other", Path("DJI_y_0001_T.JPG")),
    )
    pairs = pair_rgb_thermal_frames(rgb, thermals, minimum_confidence=0.65)
    assert len(pairs) == 1
    assert pairs[0].rgb_frame_id == "V-0001"


def test_point_in_module_polygon_and_assignment():
    module = PVModule("M-0173", "T-0042", ((10, 10), (100, 10), (100, 80), (10, 80)), 0.94, "fixture")
    assert point_in_polygon(50, 40, module.polygon_px)
    assert not point_in_polygon(150, 40, module.polygon_px)
    finding = Finding("F-1", "T-0042", 50, 40, raw_value=21000)
    assigned = assign_findings_to_modules((finding,), (module,))
    assert assigned[0].module_id == "M-0173"


def test_assignment_does_not_cross_frames():
    module = PVModule("M-1", "T-0002", ((0, 0), (100, 0), (100, 100), (0, 100)))
    finding = Finding("F-1", "T-0001", 50, 50)
    assert assign_findings_to_modules((finding,), (module,))[0].module_id is None
