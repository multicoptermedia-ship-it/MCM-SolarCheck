from pathlib import Path
from mcm_solarcheck.reporting.evidence import plan_evidence_from_record
from mcm_solarcheck.storage.queries import FindingRecord


def record(**changes):
    values=dict(finding_id='F-1',thermal_frame_id='T-1',module_id='M-1',pixel_x=10,pixel_y=20,
        finding_type='thermal_anomaly',confidence=.9,raw_value=20000,raw_delta_from_median=500,
        temperature_c=None,reviewer_status='confirmed',latitude=None,longitude=None,altitude_m=None,
        rgb_frame_id='V-1',pair_id='P-1',pair_confidence=.99,rgb_pixel_x=123.5,rgb_pixel_y=456.5,
        transform_method='homography',transform_validated=True,transform_error_px=2.5,cross_sensor_status='assigned')
    values.update(changes);return FindingRecord(**values)


def test_validated_assigned_record_exposes_rgb_marker():
    plan=plan_evidence_from_record(record(),thermal_source='T.JPG',rgb_source='V.JPG')
    assert plan.thermal_pixel==(10,20);assert plan.rgb_marker==(123.5,456.5);assert plan.module_id=='M-1'
    assert plan.transform_error_px==2.5


def test_unvalidated_transform_never_exposes_rgb_marker():
    plan=plan_evidence_from_record(record(transform_validated=False),thermal_source='T.JPG',rgb_source='V.JPG')
    assert plan.rgb_marker is None


def test_ambiguous_assignment_never_exposes_rgb_marker():
    plan=plan_evidence_from_record(record(cross_sensor_status='ambiguous_edge'),thermal_source='T.JPG',rgb_source='V.JPG')
    assert plan.rgb_marker is None


def test_missing_module_identity_never_exposes_rgb_marker():
    plan=plan_evidence_from_record(record(module_id=None),thermal_source='T.JPG',rgb_source='V.JPG')
    assert plan.rgb_marker is None


def test_missing_rgb_source_never_exposes_marker():
    plan=plan_evidence_from_record(record(),thermal_source=Path('T.JPG'))
    assert plan.rgb_source is None;assert plan.rgb_marker is None
