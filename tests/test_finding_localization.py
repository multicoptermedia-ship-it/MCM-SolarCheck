from mcm_solarcheck.domain.models import Finding,Position
from mcm_solarcheck.review.localization import localize_finding


def finding(**changes):
    values=dict(finding_id="F-1",thermal_frame_id="T-1",pixel_x=10,pixel_y=20)
    values.update(changes)
    return Finding(**values)


def test_resolved_module_is_service_location():
    result=localize_finding(finding(module_id="M-0042",position=Position(50.0,7.0)))
    assert result.module_id=="M-0042"
    assert result.status=="module_resolved"
    assert result.gps_scope=="frame_evidence"


def test_frame_gps_does_not_fake_module_assignment():
    result=localize_finding(finding(position=Position(50.0,7.0)))
    assert result.module_id is None
    assert result.status=="module_unresolved"
    assert result.gps_scope=="frame_evidence"


def test_module_identity_does_not_require_absolute_gps():
    result=localize_finding(finding(module_id="M-0042"))
    assert result.status=="module_resolved"
    assert result.gps_scope=="none"


def test_blank_module_id_is_unresolved():
    result=localize_finding(finding(module_id="  "))
    assert result.status=="module_unresolved"
