from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.cadence_phase_selection import select_cadence_phase

def fam(angle,offsets):return GridLineFamily(angle,tuple(GridLine(angle,x,1,100) for x in offsets))
def cell(x0,y0,x1,y1):return ModuleDetection(((x0,y0),(x0,y1),(x1,y1),(x1,y0)),.9)

def test_independent_support_selects_unique_two_axis_phase():
 fs=(fam(0,(0,10,20,30,40,50,60)),fam(90,(0,-10,-20,-30,-40,-50,-60)))
 q=select_cadence_phase(fs,(3,3),(cell(0,0,30,30),cell(30,30,60,60)),100,100)
 assert q.accepted and q.reason=='accepted'

def test_no_support_fails_closed():
 fs=(fam(0,(0,10,20,30)),fam(90,(0,-10,-20,-30)))
 assert select_cadence_phase(fs,(2,2),(),100,100).reason=='insufficient_evidence'
