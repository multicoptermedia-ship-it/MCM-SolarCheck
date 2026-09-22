"""Assign stable physical identities to confirmed module observations."""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.vision.module_identity import ModuleIdentityTracker,IdentityAssignment
from mcm_solarcheck.vision.module_observations import module_observations
from mcm_solarcheck.vision.module_consistency import assess_observation_geometry

@dataclass(frozen=True)
class ModuleIdentityRun:
 assignments:tuple[IdentityAssignment,...]
 status:str

def assign_confirmed_module_identities(modules,tracker:ModuleIdentityTracker)->ModuleIdentityRun:
 observations=module_observations(modules)
 if not observations:return ModuleIdentityRun((),"no_modules")
 quality=assess_observation_geometry(observations)
 if not quality.accepted:return ModuleIdentityRun((),"geometry_inconsistent")
 assignments=tuple(tracker.assign_many(observations))
 status="ambiguous" if any(a.module_id is None for a in assignments) else "assigned"
 return ModuleIdentityRun(assignments,status)
