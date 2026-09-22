from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_diagnostics import diagnose_module_evidence
def d(x):return ModuleDetection(((x,0),(x+100,0),(x+100,200),(x,200)),.8)
def test_diagnostics_counts_confirmed_and_rejected():
 q=diagnose_module_evidence((d(0),d(300)),(d(10),))
 assert (q.grid_candidates,q.image_candidates,q.confirmed,q.rejected_unconfirmed,q.status)==(2,1,1,1,"confirmed")
def test_diagnostics_explains_fail_closed_states():
 assert diagnose_module_evidence((),(d(0),)).status=="no_grid_geometry"
 assert diagnose_module_evidence((d(0),),()).status=="no_image_support"
 assert diagnose_module_evidence((d(0),),(d(500),)).status=="evidence_disagrees"
