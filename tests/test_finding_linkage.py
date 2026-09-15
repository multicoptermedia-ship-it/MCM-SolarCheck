from mcm_solarcheck.domain.models import Finding, PVModule
from mcm_solarcheck.pairing.geometry import PixelTransform, unavailable_transform
from mcm_solarcheck.vision.finding_linkage import link_finding_to_rgb_module


def finding(module_id=None):
    return Finding("F-1", "T-0001", 100, 100, module_id=module_id)


def module():
    return PVModule("M-0042", "V-0001", ((500,400),(900,400),(900,800),(500,800)))


def transform(error=2.0):
    return PixelTransform("homography", True, 640, 512, 4000, 3000,
                          ((5.0,0.0,100.0),(0.0,5.0,50.0),(0.0,0.0,1.0)), error)


def test_assigned_module_and_audit_metadata_are_persisted():
    result = link_finding_to_rgb_module(
        finding(), rgb_frame_id="V-0001", rgb_modules=(module(),), transform=transform(),
        pair_id="P-0001", pair_confidence=1.0,
    )
    assert result.module_id == "M-0042"
    assert result.metadata["cross_sensor_status"] == "assigned"
    assert result.metadata["rgb_pixel_x"] == "600.000"
    assert result.metadata["rgb_pixel_y"] == "550.000"
    assert result.metadata["transform_error_px"] == "2.000"
    assert result.metadata["pair_id"] == "P-0001"
    assert result.metadata["pair_confidence"] == "1.000000"


def test_unvalidated_transform_is_audited_and_does_not_assign():
    result = link_finding_to_rgb_module(
        finding(), rgb_frame_id="V-0001", rgb_modules=(module(),), transform=unavailable_transform()
    )
    assert result.module_id is None
    assert result.metadata["cross_sensor_status"] == "transform_unvalidated"
    assert result.metadata["transform_validated"] == "false"


def test_ambiguous_attempt_does_not_destroy_existing_module_id():
    edge_transform = PixelTransform("homography", True, 640, 512, 4000, 3000,
                                    ((5.0,0.0,0.0),(0.0,5.0,0.0),(0.0,0.0,1.0)), 2.0)
    edge_module = PVModule("M-0042", "V-0001", ((499,400),(900,400),(900,800),(499,800)))
    result = link_finding_to_rgb_module(
        finding("M-OLD"), rgb_frame_id="V-0001", rgb_modules=(edge_module,), transform=edge_transform
    )
    assert result.module_id == "M-OLD"
    assert result.metadata["cross_sensor_status"] == "ambiguous_edge"
