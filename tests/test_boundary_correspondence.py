from mcm_solarcheck.pairing.visible_grid_boundary import VisibleBoundary,BoundaryQuality
from mcm_solarcheck.pairing.boundary_correspondence import boundary_correspondence_hypotheses,BoundaryCorrespondence,score_boundary_hypothesis

def q(f,s,ok=True):
    b=VisibleBoundary(f,s,(float(f),0.0),1.0)
    return BoundaryQuality(b,4,1.0,ok)

def test_both_boundary_orientations_are_preserved():
    t=(q(0,'first'),q(0,'last'),q(1,'first'),q(1,'last'))
    r=(q(0,'first'),q(0,'last'),q(1,'first'),q(1,'last'))
    got=boundary_correspondence_hypotheses(t,r,(0,1))
    assert len(got)==2 and all(len(h)==4 for h in got)
    assert got[0][0].rgb.side=='first'
    assert got[1][0].rgb.side=='last'

def test_axis_swap_is_respected():
    got=boundary_correspondence_hypotheses((q(0,'first'),),(q(1,'first'),),(1,0))
    assert len(got[0])==1 and got[0][0].rgb.family_index==1

def test_rejected_boundary_is_never_used():
    got=boundary_correspondence_hypotheses((q(0,'first'),),(q(0,'first',False),),(0,1))
    assert all(not h for h in got)

def test_missing_boundary_is_not_invented():
    got=boundary_correspondence_hypotheses((q(0,'first'),q(0,'last')),(q(0,'first'),),(0,1))
    assert max(map(len,got))==1

def test_axis_mapping_must_be_permutation():
    import pytest
    with pytest.raises(ValueError):boundary_correspondence_hypotheses((),(),(0,0))


def test_boundary_score_uses_independent_endpoint_geometry():
    from types import SimpleNamespace
    # thermal -> RGB is exact 6x scale
    transform=SimpleNamespace(matrix=((6.,0.,0.),(0.,6.,0.),(0.,0.,1.)))
    estimate=SimpleNamespace(estimate=SimpleNamespace(transform=transform))
    t=VisibleBoundary(0,'first',(5.,7.),1.)
    r=VisibleBoundary(0,'first',(30.,42.),1.)
    score=score_boundary_hypothesis(estimate,(BoundaryCorrespondence(t,r),))
    assert score is not None and score.rms_error_px<1e-9

def test_wrong_physical_boundary_identity_has_large_error():
    from types import SimpleNamespace
    transform=SimpleNamespace(matrix=((6.,0.,0.),(0.,6.,0.),(0.,0.,1.)))
    estimate=SimpleNamespace(estimate=SimpleNamespace(transform=transform))
    t=VisibleBoundary(0,'first',(5.,7.),1.)
    r=VisibleBoundary(0,'last',(130.,142.),1.)
    score=score_boundary_hypothesis(estimate,(BoundaryCorrespondence(t,r),))
    assert score is not None and score.rms_error_px>100
