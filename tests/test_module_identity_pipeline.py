from types import SimpleNamespace
from mcm_solarcheck.vision.module_identity import ModuleIdentityTracker
from mcm_solarcheck.vision.module_identity_pipeline import assign_confirmed_module_identities

def m(fid,mid,x):return SimpleNamespace(frame_id=fid,module_id=mid,polygon_px=((x,0),(x+10,0),(x+10,20),(x,20)))
def test_identity_pipeline_reuses_unambiguous_physical_module():
 t=ModuleIdentityTracker()
 a=assign_confirmed_module_identities((m("f1","l1",0),),t);b=assign_confirmed_module_identities((m("f2","l2",1),),t)
 assert a.status=="assigned" and b.status=="assigned"
 assert a.assignments[0].module_id==b.assignments[0].module_id

def test_identity_pipeline_fails_closed_on_inconsistent_geometry():
 t=ModuleIdentityTracker();mods=(m("f","a",0),SimpleNamespace(frame_id="f",module_id="b",polygon_px=((0,0),(100,0),(100,200),(0,200))))
 assert assign_confirmed_module_identities(mods,t).status=="geometry_inconsistent"
