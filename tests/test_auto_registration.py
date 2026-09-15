import numpy as np
import pytest
import mcm_solarcheck.pairing.auto_registration as ar
from mcm_solarcheck.pairing.structural_features import StructuralPoint
from mcm_solarcheck.pairing.structural_matching import StructuralMatch


def image(w,h):return np.zeros((h,w,3),dtype=np.uint8)


def matches(n):
    return tuple(StructuralMatch(StructuralPoint(20+i*30,20+(i%4)*50),StructuralPoint(150+i*180,120+(i%4)*290),.01) for i in range(n))


def test_refuses_when_structural_matches_are_insufficient(monkeypatch):
    monkeypatch.setattr(ar,'detect_structural_lines',lambda image:())
    monkeypatch.setattr(ar,'structural_intersections',lambda lines,w,h:())
    monkeypatch.setattr(ar,'match_structural_points',lambda *args,**kwargs:matches(2))
    result=ar.register_structural_images(image(640,512),image(4000,3000))
    assert result.status=='insufficient_structural_matches';assert result.matches==2
    assert result.estimate.transform.validated is False;assert result.estimate.transform.matrix is None


def test_valid_correspondences_reach_holdout_validation(monkeypatch):
    monkeypatch.setattr(ar,'detect_structural_lines',lambda image:())
    monkeypatch.setattr(ar,'structural_intersections',lambda lines,w,h:())
    good=tuple(StructuralMatch(StructuralPoint(30+x,40+y),StructuralPoint(100+5*(30+x),50+5*(40+y)),.01) for x,y in ((0,0),(80,5),(170,20),(15,100),(130,120),(280,180),(450,280),(560,390),(70,330),(350,70),(500,150),(220,400)))
    monkeypatch.setattr(ar,'match_structural_points',lambda *args,**kwargs:good)
    result=ar.register_structural_images(image(640,512),image(4000,3000))
    assert result.status=='validated';assert result.estimate.transform.validated is True
    assert result.estimate.quality.control_points>=4


def test_configuration_cannot_undercut_holdout_requirements():
    with pytest.raises(ValueError):ar.register_structural_images(image(640,512),image(4000,3000),minimum_matches=8,minimum_fit_points=6,minimum_validation_points=4)
