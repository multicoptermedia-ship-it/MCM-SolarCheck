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
    # Missing Hough lines legitimately turn one base interval into 2x/3x gaps.
    # Test observed gaps themselves as base candidates; never invent a subharmonic.
    candidates=[]
    for base in gaps:
        if base<=1e-9:continue
        errors=[]
        for gap in gaps:
            multiple=round(gap/base)
            if 1<=multiple<=12:
                error=abs(gap/(base*multiple)-1)
                if error<=relative_tolerance:errors.append(error)
        coverage=len(errors)/len(gaps)
        if coverage>=.7:candidates.append((len(errors),-sum(errors)/len(errors),base))
    if not candidates:return GridCadence(False,"irregular_spacing",median(gaps))
    _,_,base=max(candidates)
    return GridCadence(True,"lattice_scale_only",base,1)


def select_supported_cadence_multiple(family:GridLineFamily,support_intervals,*,maximum_multiple:int=12,relative_tolerance:float=.18)->GridCadence:
    """Select a larger module cadence only from independent interval evidence.

    support_intervals are distances measured by a separate image/geometry cue; grid gaps
    themselves may establish the base scale but can never vote for a larger multiple.
    """
    base=assess_grid_cadence(family,relative_tolerance=relative_tolerance)
    if not base.accepted or base.median_gap_px is None:return base
    values=[float(v) for v in support_intervals if float(v)>0]
    if len(values)<2:return GridCadence(False,"insufficient_independent_support",base.median_gap_px)
    votes={}
    for v in values:
        k=round(v/base.median_gap_px)
        if 2<=k<=maximum_multiple and abs(v/(base.median_gap_px*k)-1)<=relative_tolerance:votes[k]=votes.get(k,0)+1
    if not votes:return GridCadence(False,"no_larger_supported_cadence",base.median_gap_px)
    ranked=sorted(votes.items(),key=lambda x:(-x[1],x[0]))
    if ranked[0][1]<2:return GridCadence(False,"insufficient_independent_support",base.median_gap_px)
    if len(ranked)>1 and ranked[1][1]==ranked[0][1]:return GridCadence(False,"ambiguous_cadence",base.median_gap_px)
    return GridCadence(True,"independently_supported",base.median_gap_px,ranked[0][0])


def cadence_line_subsets(family:GridLineFamily,multiple:int)->tuple[GridLineFamily,...]:
    """Return every possible phase for a confirmed cadence without guessing alignment."""
    if multiple<2 or len(family.lines)<2:return ()
    lines=tuple(sorted(family.lines,key=lambda x:x.offset_px))
    base=assess_grid_cadence(family)
    if not base.accepted or base.median_gap_px is None:return ()
    origin=lines[0].offset_px;out=[]
    for phase in range(multiple):
        chosen=tuple(line for line in lines if round((line.offset_px-origin)/base.median_gap_px)%multiple==phase)
        if len(chosen)>=2:out.append(GridLineFamily(family.angle_deg,chosen))
    return tuple(out)
