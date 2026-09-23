from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.vision.grid_module_detector import grid_module_detections

def fam(angle,offs):
 return GridLineFamily(angle,tuple(GridLine(angle,o,10,100) for o in offs))

def test_adjacent_grid_lines_form_cells():
 d=grid_module_detections((fam(0,(100,250,400)),fam(90,(-100,-200,-300))),500,500)
 assert len(d)==4
 assert all(x.confidence==.80 for x in d)

def test_incomplete_grid_fails_closed():
 assert grid_module_detections((fam(0,(100,)),fam(90,(100,200))),500,500)==()

def test_outside_cells_are_rejected():
 d=grid_module_detections((fam(0,(100,200)),fam(90,(100,-100,-200))),300,300)
 assert len(d)==1


def test_rotated_grid_intersection_uses_line_normal_offsets():
 from math import sqrt
 from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
 a=GridLineFamily(45,(GridLine(45,0,1,100),GridLine(45,10,1,100)))
 b=GridLineFamily(135,(GridLine(135,0,1,100),GridLine(135,10,1,100)))
 d=grid_module_detections((a,b),100,100,margin_px=0)
 assert len(d)==1
 p=d[0].polygon_px
 assert max(abs(x) for x,y in p)<15 and max(abs(y) for x,y in p)<15


def test_expected_cadence_gap_does_not_bridge_missing_module_boundary():
 d=grid_module_detections((fam(0,(100,130,190)),fam(90,(-100,-130,-160))),500,500,expected_gaps_px=(30,30))
 assert len(d)==2
 assert all(max(x for x,y in item.polygon_px)-min(x for x,y in item.polygon_px)<40 for item in d)


def test_invalid_grid_dimensions_fail_closed():
 assert grid_module_detections((fam(0,(10,20)),fam(90,(-10,-20))),100.0,100)==()
 assert grid_module_detections((fam(0,(10,20)),fam(90,(-10,-20))),100,0)==()

def test_invalid_grid_margin_fails_closed():
 fs=(fam(0,(10,20)),fam(90,(-10,-20)))
 assert grid_module_detections(fs,100,100,margin_px=-1)==()
 assert grid_module_detections(fs,100,100,margin_px=float('nan'))==()

def test_invalid_gap_tolerance_fails_closed():
 fs=(fam(0,(10,20)),fam(90,(-10,-20)))
 assert grid_module_detections(fs,100,100,gap_relative_tolerance=-.1)==()
 assert grid_module_detections(fs,100,100,gap_relative_tolerance=float('inf'))==()

def test_nonfinite_expected_gap_fails_closed():
 fs=(fam(0,(10,20)),fam(90,(-10,-20)))
 assert grid_module_detections(fs,100,100,expected_gaps_px=(10,float('nan')))==()

def test_nonfinite_grid_line_offset_fails_closed():
 assert grid_module_detections((fam(0,(10,float('inf'))),fam(90,(-10,-20))),100,100)==()
