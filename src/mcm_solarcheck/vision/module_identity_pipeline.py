"""Fail-closed physical identity assignment for PV module observations.

Raw per-frame pixel modules are intentionally not matched across frames here. Cross-frame
identity requires observations that a caller has already expressed in one explicit common
coordinate space.
"""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.vision.module_identity import ModuleIdentityTracker,IdentityAssignment,ModuleObservation
from mcm_solarcheck.vision.module_observations import module_observations
from mcm_solarcheck.vision.module_consistency import assess_observation_geometry

@dataclass(frozen=True)
class ModuleIdentityRun:
 assignments:tuple[IdentityAssignment,...]
 status:str

def _assign(observations,tracker):
 observations=tuple(observations)
 if not observations:return ModuleIdentityRun((),"no_modules")
 quality=assess_observation_geometry(observations)
 if not quality.accepted:return ModuleIdentityRun((),"geometry_inconsistent")
 assignments=tuple(tracker.assign_many(observations))
 return ModuleIdentityRun(assignments,"ambiguous" if any(a.module_id is None for a in assignments) else "assigned")

def assign_confirmed_module_identities(modules,tracker:ModuleIdentityTracker)->ModuleIdentityRun:
 """Assign one raw detector frame only; never imply cross-frame pixel registration."""
 modules=tuple(modules)
 if len({m.frame_id for m in modules})>1:return ModuleIdentityRun((),"mixed_coordinate_frames")
 if tracker.modules and modules:
  prior_frames={o.frame_id for pm in tracker.modules.values() for o in pm.observations}
  if modules[0].frame_id not in prior_frames:return ModuleIdentityRun((),"common_coordinate_space_required")
 return _assign(module_observations(modules),tracker)

def assign_registered_observations(observations,tracker:ModuleIdentityTracker,*,coordinate_space_id:str)->ModuleIdentityRun:
 """Assign observations only after caller explicitly supplies a common registered space."""
 if not coordinate_space_id.strip():return ModuleIdentityRun((),"common_coordinate_space_required")
 previous=getattr(tracker,"_mcm_coordinate_space_id",None)
 if previous is not None and previous!=coordinate_space_id:return ModuleIdentityRun((),"coordinate_space_mismatch")
 run=_assign(tuple(observations),tracker)
 if run.assignments:setattr(tracker,"_mcm_coordinate_space_id",coordinate_space_id)
 return run
