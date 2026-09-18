from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_envelope import grid_envelope

def fam(angle,offsets):
    return GridLineFamily(angle_deg=angle,lines=tuple(GridLine(angle_deg=angle,offset_px=o,support=2,length_px=100) for o in offsets))

def test_grid_envelope_uses_extreme_lines_only():
    e=grid_envelope(fam(90,(0,10,20,30)),fam(0,(0,5,10)))
    assert e is not None
    assert e.width_lines==4 and e.height_lines==3
    assert set((round(x,6),round(y,6)) for x,y in e.corners)=={(0,0),(0,10),(30,0),(30,10)}

def test_grid_envelope_requires_two_lines_per_axis():
    assert grid_envelope(fam(0,(0,)),fam(90,(0,10))) is None

def test_parallel_families_fail_closed():
    assert grid_envelope(fam(0,(0,10)),fam(0,(20,30))) is None
