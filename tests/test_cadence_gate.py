from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.cadence_gate import assess_module_cadence

def fam(angle,offsets):return GridLineFamily(angle,tuple(GridLine(angle,x,1,10) for x in offsets))
def mod(w,h):return ModuleDetection(((0,0),(w,0),(w,h),(0,h)),.8)

def test_both_axes_use_family_normal_for_independent_cadence():
 q=assess_module_cadence((fam(0,(0,10,20,30,40,50)),fam(90,(0,10,20,30,40,50))),(mod(30,20),mod(30,20)))
 assert q.accepted and [a.dominant_multiple for a in q.axes]==[2,3]

def test_missing_image_support_fails_closed():
 assert assess_module_cadence((fam(0,(0,10,20,30,40,50)),fam(90,(0,10,20,30,40,50))),()).reason=='independent_image_support_required'

def test_one_unconfirmed_axis_rejects_gate():
 q=assess_module_cadence((fam(0,(0,10,20,30,40,50)),fam(90,(0,10,20,30,40,50))),(mod(30,10),mod(30,10)))
 assert not q.accepted and q.reason=='cadence_not_confirmed'
