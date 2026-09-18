from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_segment_clipping import clip_lines_at_crossing_grid

def fam(angle,offsets):
    return GridLineFamily(angle,tuple(GridLine(angle,o,1,100) for o in offsets))

def test_long_line_is_split_at_crossing_grid():
    lines=(StructuralLine(0,10,100,10,100,0),)
    got=clip_lines_at_crossing_grid(lines,fam(0,(10,20)),fam(90,(-20,-40,-60,-80)))
    assert [round(x.length) for x in got]==[20,20,20,20,20]

def test_crossings_outside_observed_segment_do_not_extend_it():
    lines=(StructuralLine(20,10,60,10,40,0),)
    got=clip_lines_at_crossing_grid(lines,fam(0,(10,20)),fam(90,(0,-20,-40,-60,-80,-100)))
    assert sum(round(x.length) for x in got)==40
    assert all(20<=x.x1<=60 and 20<=x.x2<=60 for x in got)

def test_unrelated_lines_are_not_emitted():
    lines=(StructuralLine(10,0,10,100,100,90),)
    assert clip_lines_at_crossing_grid(lines,fam(0,(10,20)),fam(90,(-20,-40)))==()

def test_clipping_parameter_validation():
    import pytest
    with pytest.raises(ValueError):clip_lines_at_crossing_grid((),fam(0,(0,10)),fam(90,(0,10)),angle_tolerance_deg=45)
