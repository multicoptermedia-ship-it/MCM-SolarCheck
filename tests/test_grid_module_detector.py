from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.vision.grid_module_detector import grid_module_detections

def fam(angle,offs):
 return GridLineFamily(angle,tuple(GridLine(angle,o,10,100) for o in offs))

def test_adjacent_grid_lines_form_cells():
 d=grid_module_detections((fam(0,(-100,-250,-400)),fam(90,(100,200,300))),500,500)
 assert len(d)==4
 assert all(x.confidence==.80 for x in d)

def test_incomplete_grid_fails_closed():
 assert grid_module_detections((fam(0,(100,)),fam(90,(100,200))),500,500)==()

def test_outside_cells_are_rejected():
 d=grid_module_detections((fam(0,(-100,-200)),fam(90,(-100,100,200))),300,300)
 assert len(d)==1


def test_rotated_grid_intersection_uses_line_normal_offsets():
 from math import sqrt
 from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
 a=GridLineFamily(45,(GridLine(45,0,1,100),GridLine(45,10,1,100)))
 b=GridLineFamily(135,(GridLine(135,0,1,100),GridLine(135,10,1,100)))
 d=grid_module_detections((a,b),100,100,margin_px=-20)
 assert len(d)==1
 p=d[0].polygon_px
 assert max(abs(x) for x,y in p)<15 and max(abs(y) for x,y in p)<15
