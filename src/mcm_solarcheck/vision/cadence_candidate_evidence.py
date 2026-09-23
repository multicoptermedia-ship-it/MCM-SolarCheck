"""Diagnostic enumeration of cadence/phase candidates without relaxing production gates."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from math import isfinite
from mcm_solarcheck.pairing.grid_lines import GridLineFamily
from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.grid_cadence import assess_grid_cadence,cadence_line_subsets
from mcm_solarcheck.vision.grid_module_detector import grid_module_detections
from mcm_solarcheck.vision.grid_cell_support import finite_support_sides,internal_lattice_support,has_repeated_lattice_evidence
from mcm_solarcheck.vision.polygon_geometry import convex_polygon_iou

@dataclass(frozen=True)
class CadenceCellEvidence:
    multiples:tuple[int,int]
    phases:tuple[int,int]
    polygon_px:tuple[tuple[float,float],...]
    best_iou:float
    outer_support:int
    internal_lattice:tuple[int,int]
    repeated_lattice:bool

@dataclass(frozen=True)
class CadenceCandidateEvidence:
    multiples:tuple[int,int]
    phases:tuple[int,int]
    matched_cells:int
    iou_score:float
    cells:tuple[CadenceCellEvidence,...]

def enumerate_cadence_candidate_evidence(
    families:tuple[GridLineFamily,...],
    multiple_options:tuple[tuple[int,...],tuple[int,...]],
    support:tuple[ModuleDetection,...],
    lines:tuple[StructuralLine,...],
    width:int,
    height:int,
    *,
    minimum_iou:float=.20,
)->tuple[CadenceCandidateEvidence,...]:
    """Measure every independently supported candidate; never accept or alter a gate."""
    if len(families)!=2 or len(multiple_options)!=2 or not support or width<=0 or height<=0:return ()
    if not isfinite(float(minimum_iou)) or not 0.0<=minimum_iou<=1.0:return ()
    if any(not options for options in multiple_options):return ()
    if any(type(m) is not int or m<2 for options in multiple_options for m in options):return ()
    if any(len(set(options))!=len(options) for options in multiple_options):return ()
    bases=tuple(assess_grid_cadence(f) for f in families)
    if not all(b.accepted and b.median_gap_px for b in bases):return ()
    out=[]
    for multiples in product(*multiple_options):
        if any(m<2 for m in multiples):continue
        subsets=tuple(cadence_line_subsets(f,m) for f,m in zip(families,multiples))
        if not all(subsets):continue
        expected=tuple(float(b.median_gap_px)*m for b,m in zip(bases,multiples))
        for ia,a in enumerate(subsets[0]):
            for ib,b in enumerate(subsets[1]):
                cells=grid_module_detections((a,b),width,height,margin_px=2,expected_gaps_px=expected)
                measured=[]
                for cell in cells:
                    iou=max((convex_polygon_iou(cell.polygon_px,s.polygon_px) for s in support),default=0.0)
                    if iou<minimum_iou:continue
                    sides=finite_support_sides(cell,(a,b),lines)
                    lattice=internal_lattice_support(cell,(a,b),lines)
                    measured.append(CadenceCellEvidence(
                        (int(multiples[0]),int(multiples[1])),(ia,ib),cell.polygon_px,float(iou),
                        sum(sides),lattice,has_repeated_lattice_evidence(cell,(a,b),lines),
                    ))
                if measured:
                    out.append(CadenceCandidateEvidence(
                        (int(multiples[0]),int(multiples[1])),(ia,ib),len(measured),
                        sum(c.best_iou for c in measured),tuple(measured),
                    ))
    out.sort(key=lambda c:(-c.matched_cells,-c.iou_score,c.multiples,c.phases))
    return tuple(out)


@dataclass(frozen=True)
class CadenceDisambiguation:
    accepted:bool
    candidate:CadenceCandidateEvidence|None
    reason:str

def select_uniquely_supported_candidate(
    candidates:tuple[CadenceCandidateEvidence,...],
)->CadenceDisambiguation:
    """Accept only when repeated finite lattice evidence uniquely identifies one geometry.

    This helper is deliberately stricter than diagnostic ordering: IoU or matched-cell
    count can rank candidates for inspection, but neither may break a lattice tie.
    """
    valid=tuple(
        candidate for candidate in candidates
        if len(candidate.multiples)==2
        and len(candidate.phases)==2
        and candidate.matched_cells==len(candidate.cells)
        and candidate.matched_cells>0
        and isfinite(float(candidate.iou_score))
        and candidate.iou_score>=0
        and all(
            cell.multiples==candidate.multiples
            and cell.phases==candidate.phases
            and isfinite(float(cell.best_iou))
            and 0.0<=cell.best_iou<=1.0
            and 0<=cell.outer_support<=4
            and len(cell.internal_lattice)==2
            and all(type(v) is int and v>=0 for v in cell.internal_lattice)
            for cell in candidate.cells
        )
    )
    if len(valid)!=len(candidates):
        return CadenceDisambiguation(False,None,"invalid_candidate_evidence")
    supported=tuple(
        candidate for candidate in valid
        if any(cell.repeated_lattice for cell in candidate.cells)
    )
    if not supported:
        return CadenceDisambiguation(False,None,"repeated_lattice_support_required")
    geometries={candidate.multiples for candidate in supported}
    if len(geometries)!=1:
        return CadenceDisambiguation(False,None,"ambiguous_lattice_supported_cadence")
    geometry=next(iter(geometries))
    same_geometry=tuple(candidate for candidate in supported if candidate.multiples==geometry)
    phases={candidate.phases for candidate in same_geometry}
    if len(phases)!=1:
        return CadenceDisambiguation(False,None,"ambiguous_lattice_supported_phase")
    # Multiple measured records for the same geometry/phase are equivalent evidence,
    # not a second phase. Keep deterministic diagnostic ordering.
    chosen=max(same_geometry,key=lambda candidate:(candidate.matched_cells,candidate.iou_score))
    return CadenceDisambiguation(True,chosen,"accepted")
