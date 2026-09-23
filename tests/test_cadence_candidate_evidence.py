from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.cadence_candidate_evidence import enumerate_cadence_candidate_evidence

def fam(angle,offsets):return GridLineFamily(angle,tuple(GridLine(angle,x,1,100) for x in offsets))
def cell(x0,y0,x1,y1):return ModuleDetection(((x0,y0),(x0,y1),(x1,y1),(x1,y0)),.9)

def test_candidate_report_is_diagnostic_and_measures_finite_evidence():
    fs=(fam(0,(0,15,30,45,60,75,90)),fam(90,(0,-15,-30,-45,-60,-75,-90)))
    support=(cell(0,0,45,45),)
    lines=(
      StructuralLine(0,0,45,0,45,0),StructuralLine(0,0,0,45,45,90),
      StructuralLine(0,22.5,45,22.5,45,0),StructuralLine(22.5,0,22.5,45,45,90),
    )
    q=enumerate_cadence_candidate_evidence(fs,((3,),(3,)),support,lines,100,100)
    assert q and q[0].multiples==(3,3) and q[0].matched_cells>=1
    best=q[0].cells[0]
    assert best.best_iou>=.20
    assert best.outer_support>=1
    assert best.internal_lattice==(1,1)
    assert best.repeated_lattice

def test_candidate_report_fails_closed_without_independent_support():
    fs=(fam(0,(0,10,20,30)),fam(90,(0,-10,-20,-30)))
    assert enumerate_cadence_candidate_evidence(fs,((2,),(2,)),(),(),100,100)==()

def test_candidate_report_does_not_invent_subharmonic_multiples():
    fs=(fam(0,(0,10,20,30)),fam(90,(0,-10,-20,-30)))
    support=(cell(0,0,20,20),)
    assert enumerate_cadence_candidate_evidence(fs,((1,),(2,)),support,(),100,100)==()
