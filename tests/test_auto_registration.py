import numpy as np
import pytest
import mcm_solarcheck.pairing.auto_registration as ar
from mcm_solarcheck.pairing.oriented_features import OrientedStructuralPoint
from mcm_solarcheck.pairing.oriented_matching import OrientedMatch


def image(w,h):return np.zeros((h,w,3),dtype=np.uint8)

def point(x,y):return OrientedStructuralPoint(x,y,0,90)

def matches(n):return tuple(OrientedMatch(point(20+i*30,20+(i%4)*50),point(150+i*180,120+(i%4)*290),.01) for i in range(n))


def setup(monkeypatch,good):
    monkeypatch.setattr(ar,'detect_structural_lines',lambda image:())
    monkeypatch.setattr(ar,'oriented_intersections',lambda lines,w,h:())
    monkeypatch.setattr(ar,'match_oriented_points',lambda *args,**kwargs:good)


def test_refuses_when_oriented_matches_are_insufficient(monkeypatch):
    setup(monkeypatch,matches(2));result=ar.register_structural_images(image(640,512),image(4000,3000))
    assert result.status=='insufficient_oriented_structural_matches';assert result.matches==2
    assert result.estimate.transform.validated is False;assert result.estimate.transform.matrix is None
    assert result.estimate.transform.method=='oriented_structural_homography'


def test_valid_correspondences_reach_holdout_validation(monkeypatch):
    coords=((30,40),(110,45),(200,60),(45,140),(160,160),(310,220),(480,320),(590,430),(100,370),(380,110),(530,190),(250,440))
    good=tuple(OrientedMatch(point(x,y),point(100+5*x,50+5*y),.01) for x,y in coords);setup(monkeypatch,good)
    result=ar.register_structural_images(image(640,512),image(4000,3000))
    assert result.status=='validated';assert result.estimate.transform.validated is True
    assert result.estimate.quality.control_points>=4


def test_configuration_cannot_undercut_holdout_requirements():
    with pytest.raises(ValueError):ar.register_structural_images(image(640,512),image(4000,3000),minimum_matches=8,minimum_fit_points=6,minimum_validation_points=4)
