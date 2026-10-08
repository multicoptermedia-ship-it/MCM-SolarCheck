import numpy as np
import pytest
from mcm_solarcheck.pairing import real_dataset_validation as validation
from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_line_matching import GridLineFamilyMatch
from mcm_solarcheck.pairing.registration import HomographyEstimate,RegistrationQuality
from mcm_solarcheck.pairing.geometry import PixelTransform


def family(angle,offsets):
    return GridLineFamily(angle,tuple(GridLine(angle,float(x),1,100.0) for x in offsets))


def test_unmatched_pair_reports_intermediate_evidence_and_fails_closed(monkeypatch,tmp_path):
    monkeypatch.setattr(validation.cv2,'imread',lambda *args,**kwargs:np.zeros((20,30,3),dtype=np.uint8))
    monkeypatch.setattr(validation,'detect_structural_lines',lambda image:(object(),)*7)
    tf=(family(90,(1,2,3,4)),family(0,(1,2,3,4)))
    rf=(family(91,(1,2,3,4)),family(1,(1,2,3,4)))
    calls=iter((tf,rf));monkeypatch.setattr(validation,'extract_grid_line_families',lambda *args,**kwargs:next(calls))
    monkeypatch.setattr(validation,'match_grid_line_families',lambda *args,**kwargs:())
    result=validation.validate_pair(tmp_path/'a_T.JPG',tmp_path/'a_V.JPG')
    assert result.status=='insufficient_global_grid_family_matches'
    assert result.thermal_lines==7 and result.rgb_lines==7
    assert len(result.thermal_families)==2 and result.control_points==0
    assert result.validated is False


def test_validated_pair_exposes_holdout_quality(monkeypatch,tmp_path):
    monkeypatch.setattr(validation.cv2,'imread',lambda *args,**kwargs:np.zeros((512,640,3),dtype=np.uint8))
    monkeypatch.setattr(validation,'detect_structural_lines',lambda image:(object(),)*8)
    tf=(family(90,(1,2,3,4)),family(0,(1,2,3,4)))
    rf=(family(91,(6,12,18,24)),family(1,(6,12,18,24)))
    calls=iter((tf,rf));monkeypatch.setattr(validation,'extract_grid_line_families',lambda *args,**kwargs:next(calls))
    matches=(GridLineFamilyMatch(tf[0],rf[0],False,0,0,4,0.01),GridLineFamilyMatch(tf[1],rf[1],False,0,0,4,0.02))
    monkeypatch.setattr(validation,'match_grid_line_families',lambda *args,**kwargs:matches)
    points=tuple(object() for _ in range(12));monkeypatch.setattr(validation,'grid_control_points',lambda matches:points)
    monkeypatch.setattr(validation,'split_grid_control_points',lambda points,**kwargs:(points[:8],points[8:]))
    estimate=HomographyEstimate(PixelTransform('homography_ransac_holdout',True,640,512,640,512,((1,0,0),(0,1,0),(0,0,1)),2.0),RegistrationQuality(4,2.0,3.0,True,'accepted'),8,8)
    monkeypatch.setattr(validation,'estimate_homography',lambda *args,**kwargs:estimate)
    result=validation.validate_pair(tmp_path/'a_T.JPG',tmp_path/'a_V.JPG')
    assert result.validated and result.status=='validated'
    assert (result.control_points,result.fit_points,result.holdout_points,result.inliers)==(12,8,4,8)
    assert result.rms_error_px==2.0 and result.max_error_px==3.0
    assert [round(m.rotation_deg) for m in result.family_matches]==[1,1]


def test_unreadable_image_is_rejected(monkeypatch,tmp_path):
    monkeypatch.setattr(validation.cv2,'imread',lambda *args,**kwargs:None)
    with pytest.raises(ValueError,match='cannot read thermal image'):
        validation.validate_pair(tmp_path/'missing_T.JPG',tmp_path/'missing_V.JPG')
