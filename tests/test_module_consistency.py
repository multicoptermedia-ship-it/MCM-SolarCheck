from mcm_solarcheck.vision.module_identity import ModuleObservation
from mcm_solarcheck.vision.module_consistency import assess_observation_geometry
def o(i,w,h):return ModuleObservation(i,i,(0,0),w,h)
def test_consistency_accepts_similar_module_geometry():
 assert assess_observation_geometry((o("a",100,200),o("b",105,195))).accepted
def test_consistency_rejects_size_outlier_and_empty():
 assert not assess_observation_geometry((o("a",100,200),o("b",400,400))).accepted
 assert not assess_observation_geometry(()).accepted
