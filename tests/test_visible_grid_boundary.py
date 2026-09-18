from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.visible_grid_boundary import visible_grid_boundaries

def test_visible_boundaries_require_observed_extreme_support():
    lines=(StructuralLine(0,10,100,10,0,90),StructuralLine(0,30,100,30,0,80))
    fam=GridLineFamily(0,(GridLine(0,10,1,90),GridLine(0,20,1,70),GridLine(0,30,1,80)))
    got=visible_grid_boundaries(lines,(fam,),endpoint_tolerance_px=2)
    assert [(b.side,b.endpoint) for b in got]==[('first',(0,10)),('last',(0,30))]

def test_missing_extreme_support_fails_closed():
    lines=(StructuralLine(0,20,100,20,0,90),)
    fam=GridLineFamily(0,(GridLine(0,10,1,70),GridLine(0,20,1,90),GridLine(0,30,1,70)))
    assert visible_grid_boundaries(lines,(fam,),endpoint_tolerance_px=2)==()

def test_unrelated_angle_is_not_boundary_evidence():
    lines=(StructuralLine(10,0,10,100,90,100),)
    fam=GridLineFamily(0,(GridLine(0,10,1,100),GridLine(0,30,1,100)))
    assert visible_grid_boundaries(lines,(fam,),endpoint_tolerance_px=2)==()

def test_boundary_parameter_validation():
    import pytest
    with pytest.raises(ValueError):visible_grid_boundaries((),(),endpoint_tolerance_px=0)
    with pytest.raises(ValueError):visible_grid_boundaries((),(),angle_tolerance_deg=45)
