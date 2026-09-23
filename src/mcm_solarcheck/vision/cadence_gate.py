"""Fail-closed gate that lets independent image geometry confirm grid cadence."""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.pairing.grid_lines import GridLineFamily
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.grid_cadence import GridCadence,select_supported_cadence_multiple
from mcm_solarcheck.vision.image_cadence_support import image_module_intervals

@dataclass(frozen=True)
class CadenceGateResult:
    accepted:bool
    axes:tuple[GridCadence,...]
    reason:str

def assess_module_cadence(families:tuple[GridLineFamily,...],image_support:tuple[ModuleDetection,...])->CadenceGateResult:
    """Require both grid axes to have independently supported larger cadence.

    Grid-line offsets vary along the family normal, so image module spans must be
    projected onto that normal rather than along the line direction itself.
    """
    if len(families)!=2:return CadenceGateResult(False,(),"two_grid_families_required")
    if not image_support:return CadenceGateResult(False,(),"independent_image_support_required")
    axes=tuple(select_supported_cadence_multiple(f,image_module_intervals(image_support,f.angle_deg+90.0)) for f in families)
    if not all(a.accepted and (a.dominant_multiple or 1)>=2 for a in axes):return CadenceGateResult(False,axes,"cadence_not_confirmed")
    return CadenceGateResult(True,axes,"accepted")
