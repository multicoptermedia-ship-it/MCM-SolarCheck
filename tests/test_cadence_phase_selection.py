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


def test_invalid_phase_multiples_fail_closed():
 fs=(fam(0,(0,10,20,30,40)),fam(90,(0,-10,-20,-30,-40)))
 support=(cell(0,0,20,20),)
 assert select_cadence_phase(fs,(1,2),support,100,100).reason=='invalid_multiples'
 assert select_cadence_phase(fs,(True,2),support,100,100).reason=='invalid_multiples'

def test_invalid_phase_dimensions_fail_closed():
 fs=(fam(0,(0,10,20,30,40)),fam(90,(0,-10,-20,-30,-40)))
 support=(cell(0,0,20,20),)
 assert select_cadence_phase(fs,(2,2),support,0,100).reason=='invalid_dimensions'
 assert select_cadence_phase(fs,(2,2),support,100.0,100).reason=='invalid_dimensions'

def test_invalid_phase_iou_threshold_fails_closed():
 fs=(fam(0,(0,10,20,30,40)),fam(90,(0,-10,-20,-30,-40)))
 support=(cell(0,0,20,20),)
 assert select_cadence_phase(fs,(2,2),support,100,100,minimum_iou=float('nan')).reason=='invalid_minimum_iou'
 assert select_cadence_phase(fs,(2,2),support,100,100,minimum_iou=1.1).reason=='invalid_minimum_iou'

def test_invalid_phase_ambiguity_margin_fails_closed():
 fs=(fam(0,(0,10,20,30,40)),fam(90,(0,-10,-20,-30,-40)))
 support=(cell(0,0,20,20),)
 assert select_cadence_phase(fs,(2,2),support,100,100,ambiguity_margin=-.1).reason=='invalid_ambiguity_margin'
 assert select_cadence_phase(fs,(2,2),support,100,100,ambiguity_margin=float('inf')).reason=='invalid_ambiguity_margin'
