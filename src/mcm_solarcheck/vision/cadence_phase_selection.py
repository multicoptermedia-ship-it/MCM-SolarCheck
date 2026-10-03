"""Select a unique two-axis cadence phase using independent image evidence."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from mcm_solarcheck.pairing.grid_lines import GridLineFamily
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.grid_cadence import cadence_line_subsets,assess_grid_cadence
from mcm_solarcheck.vision.grid_module_detector import grid_module_detections
from mcm_solarcheck.vision.polygon_geometry import convex_polygon_iou

@dataclass(frozen=True)
class CadencePhaseSelection:
    accepted:bool
    families:tuple[GridLineFamily,...]
    score:float
    reason:str

def select_cadence_phase(families:tuple[GridLineFamily,...],multiples:tuple[int,int],support:tuple[ModuleDetection,...],width:int,height:int,*,minimum_iou:float=.20,ambiguity_margin:float=.05)->CadencePhaseSelection:
    if len(families)!=2 or not support:return CadencePhaseSelection(False,(),0.0,"insufficient_evidence")
    if len(multiples)!=2 or any(type(m) is not int or m<2 for m in multiples):return CadencePhaseSelection(False,(),0.0,"invalid_multiples")
    if type(width) is not int or type(height) is not int or width<=0 or height<=0:return CadencePhaseSelection(False,(),0.0,"invalid_dimensions")
    if not isfinite(float(minimum_iou)) or not 0.0<=minimum_iou<=1.0:return CadencePhaseSelection(False,(),0.0,"invalid_minimum_iou")
    if not isfinite(float(ambiguity_margin)) or ambiguity_margin<0:return CadencePhaseSelection(False,(),0.0,"invalid_ambiguity_margin")
    bases=tuple(assess_grid_cadence(f) for f in families)
    if not all(b.accepted and b.median_gap_px for b in bases):return CadencePhaseSelection(False,(),0.0,"base_cadence_required")
    expected=tuple(float(b.median_gap_px)*m for b,m in zip(bases,multiples))
    candidates=[]
    for a in cadence_line_subsets(families[0],multiples[0]):
      for b in cadence_line_subsets(families[1],multiples[1]):
        cells=grid_module_detections((a,b),width,height,margin_px=2,expected_gaps_px=expected)
        hits=[max((convex_polygon_iou(cell.polygon_px,s.polygon_px) for s in support),default=0.0) for cell in cells]
        matched=[v for v in hits if v>=minimum_iou]
        score=sum(matched)
        if matched:candidates.append((len(matched),score,a,b))
    if not candidates:return CadencePhaseSelection(False,(),0.0,"no_supported_phase")
    candidates.sort(key=lambda x:(-x[0],-x[1]))
    best=candidates[0]
    if len(candidates)>1 and best[0]==candidates[1][0] and best[1]-candidates[1][1]<ambiguity_margin:return CadencePhaseSelection(False,(),best[1],"ambiguous_phase")
    return CadencePhaseSelection(True,(best[2],best[3]),best[1],"accepted")
