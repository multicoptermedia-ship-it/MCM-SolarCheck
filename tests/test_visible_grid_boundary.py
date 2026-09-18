from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.visible_grid_boundary import visible_grid_boundaries,VisibleBoundary,assess_visible_boundaries

def test_visible_boundaries_require_observed_extreme_support():
    lines=(StructuralLine(0,10,100,10,100,0),StructuralLine(0,30,100,30,100,0))
    fam=GridLineFamily(0,(GridLine(0,10,1,90),GridLine(0,20,1,70),GridLine(0,30,1,80)))
    got=visible_grid_boundaries(lines,(fam,),endpoint_tolerance_px=2)
    assert [(b.side,b.endpoint) for b in got]==[('first',(0,10)),('last',(0,30))]

def test_missing_extreme_support_fails_closed():
    lines=(StructuralLine(0,20,100,20,100,0),)
    fam=GridLineFamily(0,(GridLine(0,10,1,70),GridLine(0,20,1,90),GridLine(0,30,1,70)))
    assert visible_grid_boundaries(lines,(fam,),endpoint_tolerance_px=2)==()

def test_unrelated_angle_is_not_boundary_evidence():
    lines=(StructuralLine(10,0,10,100,100,90),)
    fam=GridLineFamily(0,(GridLine(0,10,1,100),GridLine(0,30,1,100)))
    assert visible_grid_boundaries(lines,(fam,),endpoint_tolerance_px=2)==()

def test_boundary_parameter_validation():
    import pytest
    with pytest.raises(ValueError):visible_grid_boundaries((),(),endpoint_tolerance_px=0)
    with pytest.raises(ValueError):visible_grid_boundaries((),(),angle_tolerance_deg=45)


def test_boundary_quality_is_resolution_normalized():
    t=GridLineFamily(0,tuple(GridLine(0,o,1,20) for o in (0,10,20,30)))
    r=GridLineFamily(0,tuple(GridLine(0,o,1,120) for o in (0,60,120,180)))
    tb=VisibleBoundary(0,'first',(0,0),20)
    rb=VisibleBoundary(0,'first',(0,0),120)
    tq=assess_visible_boundaries((tb,),(t,))[0]
    rq=assess_visible_boundaries((rb,),(r,))[0]
    assert tq.accepted and rq.accepted
    assert tq.normalized_support==rq.normalized_support==2

def test_excessively_long_non_grid_edge_is_rejected():
    f=GridLineFamily(0,tuple(GridLine(0,o,1,20) for o in (0,10,20,30)))
    q=assess_visible_boundaries((VisibleBoundary(0,'first',(0,0),100),),(f,))[0]
    assert not q.accepted

def test_boundary_quality_requires_neighboring_grid_evidence():
    f=GridLineFamily(0,(GridLine(0,0,1,20),GridLine(0,10,1,20)))
    q=assess_visible_boundaries((VisibleBoundary(0,'first',(0,0),20),),(f,))[0]
    assert not q.accepted
