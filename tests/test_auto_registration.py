import numpy as np
import pytest
import mcm_solarcheck.pairing.auto_registration as ar
from mcm_solarcheck.pairing.oriented_features import OrientedStructuralPoint
from mcm_solarcheck.pairing.oriented_matching import OrientedMatch
from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_line_matching import GridLineFamilyMatch


def image(w,h):return np.zeros((h,w,3),dtype=np.uint8)
def point(x,y):return OrientedStructuralPoint(x,y,0,90)
def matches(n):return tuple(OrientedMatch(point(20+i*30,20+(i%4)*50),point(150+i*180,120+(i%4)*290),.01) for i in range(n))
def family(offsets,angle):return GridLineFamily(angle,tuple(GridLine(angle,o,1,100) for o in offsets))
def family_match(t,r):return GridLineFamilyMatch(t,r,False,0,0,min(len(t.lines),len(r.lines)),0)


def setup(monkeypatch,good):
    monkeypatch.setattr(ar,'detect_structural_lines',lambda image:())
    monkeypatch.setattr(ar,'oriented_intersections',lambda lines,w,h:())
    monkeypatch.setattr(ar,'match_oriented_points',lambda *args,**kwargs:good)


def setup_grid(monkeypatch,good):
    monkeypatch.setattr(ar,'detect_structural_lines',lambda image:())
    thermal=(family((10,30,50,80),90),family((20,40,70,100),0))
    rgb=(family((60,180,300,480),90),family((120,240,420,600),0))
    calls=iter((thermal,rgb))
    monkeypatch.setattr(ar,'extract_grid_line_families',lambda *args,**kwargs:next(calls))
    monkeypatch.setattr(ar,'match_grid_line_families',lambda *args,**kwargs:good)


def test_refuses_when_oriented_matches_are_insufficient(monkeypatch):
    setup(monkeypatch,matches(2));result=ar.register_structural_images(image(640,512),image(4000,3000))
    assert result.status=='insufficient_oriented_structural_matches';assert result.matches==2
    assert result.estimate.transform.validated is False;assert result.estimate.transform.matrix is None
    assert result.estimate.transform.method=='oriented_structural_homography';assert result.estimate.fit_points==0


def test_valid_correspondences_reach_holdout_validation(monkeypatch):
    coords=((30,40),(110,45),(200,60),(45,140),(160,160),(310,220),(480,320),(590,430),(100,370),(380,110),(530,190),(250,440))
    good=tuple(OrientedMatch(point(x,y),point(100+5*x,50+5*y),.01) for x,y in coords);setup(monkeypatch,good)
    result=ar.register_structural_images(image(640,512),image(4000,3000))
    assert result.status=='validated';assert result.estimate.transform.validated is True
    assert result.estimate.quality.control_points>=4


def test_configuration_cannot_undercut_holdout_requirements():
    with pytest.raises(ValueError):ar.register_structural_images(image(640,512),image(4000,3000),minimum_matches=8,minimum_fit_points=6,minimum_validation_points=4)


def test_global_grid_refuses_without_two_family_matches(monkeypatch):
    setup_grid(monkeypatch,())
    result=ar.register_global_grid_images(image(640,512),image(4000,3000))
    assert result.status=='insufficient_global_grid_family_matches'
    assert result.thermal_points==8;assert result.rgb_points==8;assert result.matches==0
    assert result.estimate.transform.validated is False;assert result.estimate.transform.method=='global_grid_homography';assert result.estimate.fit_points==0


def test_global_grid_reaches_independent_holdout_validation(monkeypatch):
    tv=family((10,30,50,80),90);th=family((20,40,70,100),0);rv=family((60,180,300,480),90);rh=family((120,240,420,600),0)
    setup_grid(monkeypatch,(family_match(tv,rv),family_match(th,rh)))
    result=ar.register_global_grid_images(image(640,512),image(4000,3000))
    assert result.status=='validated';assert result.matches==16;assert result.estimate.transform.validated is True
    assert result.estimate.fit_points>=6;assert result.estimate.quality.control_points>=4;assert result.estimate.quality.rms_error_px<1e-6


def test_global_grid_refuses_when_intersections_do_not_cover_fit_and_holdout(monkeypatch):
    tv=family((10,30,50),90);th=family((20,40,70),0);rv=family((60,180,300),90);rh=family((120,240,420),0)
    setup_grid(monkeypatch,(family_match(tv,rv),family_match(th,rh)))
    result=ar.register_global_grid_images(image(640,512),image(4000,3000),minimum_family_lines=3)
    assert result.status=='insufficient_global_grid_control_points';assert result.matches==9
    assert result.estimate.transform.validated is False;assert result.estimate.fit_points==0


def test_global_grid_configuration_preserves_independent_validation():
    with pytest.raises(ValueError):ar.register_global_grid_images(image(640,512),image(4000,3000),minimum_fit_points=3)
    with pytest.raises(ValueError):ar.register_global_grid_images(image(640,512),image(4000,3000),minimum_validation_points=3)
