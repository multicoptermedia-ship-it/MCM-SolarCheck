"""Fail-closed gate that lets independent image geometry confirm grid cadence."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from mcm_solarcheck.pairing.grid_lines import GridLineFamily
from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.grid_cadence import GridCadence,assess_grid_cadence,select_supported_cadence_multiple,supported_cadence_multiples,cadence_line_subsets
from mcm_solarcheck.vision.image_cadence_support import image_module_intervals
from mcm_solarcheck.vision.cadence_candidate_evidence import enumerate_cadence_candidate_evidence,select_uniquely_supported_candidate

@dataclass(frozen=True)
class CadenceGateResult:
    accepted:bool
    axes:tuple[GridCadence,...]
    reason:str
    phases:tuple[int,int]|None=None

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


def assess_ambiguous_module_cadence(
    families:tuple[GridLineFamily,...],
    image_support:tuple[ModuleDetection,...],
    lines:tuple[StructuralLine,...],
    width:int,
    height:int,
    *,
    minimum_iou:float=.20,
)->CadenceGateResult:
    """Resolve only image-supported cadence ties with unique finite lattice evidence."""
    primary=assess_module_cadence(families,image_support)
    if primary.accepted:return primary
    if primary.reason!="cadence_not_confirmed" or len(families)!=2 or not image_support:
        return primary
    if not any(axis.reason=="ambiguous_cadence" for axis in primary.axes):
        return primary
    if type(width) is not int or type(height) is not int or width<=0 or height<=0:
        return CadenceGateResult(False,primary.axes,"invalid_image_dimensions")
    if not isfinite(float(minimum_iou)) or not 0.0<=minimum_iou<=1.0:
        return CadenceGateResult(False,primary.axes,"invalid_minimum_iou")
    options=tuple(
        supported_cadence_multiples(
            family,image_module_intervals(image_support,family.angle_deg+90.0)
        )
        for family in families
    )
    if not all(options):
        return CadenceGateResult(False,primary.axes,"cadence_candidates_not_confirmed")
    evidence=enumerate_cadence_candidate_evidence(
        families,(options[0],options[1]),image_support,lines,width,height,
        minimum_iou=minimum_iou,
    )
    resolved=select_uniquely_supported_candidate(evidence)
    if not resolved.accepted or resolved.candidate is None:
        return CadenceGateResult(False,primary.axes,resolved.reason)
    candidate=resolved.candidate
    if candidate not in evidence:
        return CadenceGateResult(False,primary.axes,"resolved_candidate_not_enumerated")
    if len(candidate.multiples)!=2 or any(type(m) is not int or m not in axis_options for m,axis_options in zip(candidate.multiples,options)):
        return CadenceGateResult(False,primary.axes,"resolved_cadence_not_supported")
    if len(candidate.phases)!=2 or any(type(p) is not int or p<0 for p in candidate.phases):
        return CadenceGateResult(False,primary.axes,"resolved_phase_invalid")
    subsets=tuple(cadence_line_subsets(f,m) for f,m in zip(families,candidate.multiples))
    if len(subsets)!=2 or any(p>=len(axis_subsets) for p,axis_subsets in zip(candidate.phases,subsets)):
        return CadenceGateResult(False,primary.axes,"resolved_phase_out_of_range")
    bases=tuple(assess_grid_cadence(family) for family in families)
    if not all(a.accepted and a.median_gap_px is not None for a in bases):
        return CadenceGateResult(False,primary.axes,"resolved_cadence_invalid")
    axes=tuple(
        GridCadence(True,"uniquely_lattice_supported",float(base.median_gap_px),multiple)
        for base,multiple in zip(bases,candidate.multiples)
    )
    return CadenceGateResult(True,axes,"accepted_by_unique_lattice_evidence",candidate.phases)
