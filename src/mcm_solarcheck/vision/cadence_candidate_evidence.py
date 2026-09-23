"""Diagnostic enumeration of cadence/phase candidates without relaxing production gates."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
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
