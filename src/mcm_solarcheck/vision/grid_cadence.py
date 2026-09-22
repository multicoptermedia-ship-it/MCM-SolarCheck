"""Conservative cadence evidence for separating repeated cell lines from module boundaries."""
from __future__ import annotations
from dataclasses import dataclass
from statistics import median
from mcm_solarcheck.pairing.grid_lines import GridLineFamily

@dataclass(frozen=True)
class GridCadence:
    accepted:bool
    reason:str
    median_gap_px:float|None=None
    dominant_multiple:int|None=None

def assess_grid_cadence(family:GridLineFamily,*,minimum_gaps:int=4,relative_tolerance:float=.18)->GridCadence:
    """Describe repeated spacing only when the evidence is unambiguous.

    This does not yet remove lines. It intentionally refuses to infer module boundaries
    from a single spacing scale; a larger repeated cadence must be demonstrated later by
    independent image/geometry evidence.
    """
    if minimum_gaps<2 or not 0<relative_tolerance<.5:return GridCadence(False,"invalid_parameters")
    gaps=[family.lines[i+1].offset_px-family.lines[i].offset_px for i in range(len(family.lines)-1)]
    gaps=[g for g in gaps if g>1e-9]
    if len(gaps)<minimum_gaps:return GridCadence(False,"insufficient_gaps")
    m=median(gaps)
    if m<=0:return GridCadence(False,"invalid_spacing")
    near=sum(abs(g/m-1)<=relative_tolerance for g in gaps)
    if near/len(gaps)<.6:return GridCadence(False,"irregular_spacing",m)
    return GridCadence(True,"single_scale_only",m,1)
