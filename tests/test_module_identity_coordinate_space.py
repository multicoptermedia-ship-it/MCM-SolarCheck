from mcm_solarcheck.vision.module_identity import ModuleIdentityTracker,ModuleObservation
from mcm_solarcheck.vision.module_identity_pipeline import assign_registered_observations

def test_coordinate_space_is_explicit_tracker_state():
 t=ModuleIdentityTracker();o=ModuleObservation('f','m',(1,2),10,20)
 r=assign_registered_observations((o,),t,coordinate_space_id='roof-A')
 assert r.status=='assigned' and t.coordinate_space_id=='roof-A'
 assert assign_registered_observations((o,),t,coordinate_space_id='roof-B').status=='coordinate_space_mismatch'
