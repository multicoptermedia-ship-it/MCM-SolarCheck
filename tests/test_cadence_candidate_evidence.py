from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.cadence_candidate_evidence import (CadenceCandidateEvidence,CadenceCellEvidence,enumerate_cadence_candidate_evidence,select_uniquely_supported_candidate)

def fam(angle,offsets):return GridLineFamily(angle,tuple(GridLine(angle,x,1,100) for x in offsets))
def cell(x0,y0,x1,y1):return ModuleDetection(((x0,y0),(x0,y1),(x1,y1),(x1,y0)),.9)

def test_candidate_report_is_diagnostic_and_measures_finite_evidence():
    fs=(fam(0,(15,30,45,60,75,90,105)),fam(90,(-15,-30,-45,-60,-75,-90,-105)))
    support=(cell(15,15,60,60),)
    lines=(
      StructuralLine(15,15,60,15,45,0),StructuralLine(15,15,15,60,45,90),
      StructuralLine(15,37.5,60,37.5,45,0),StructuralLine(37.5,15,37.5,60,45,90),
    )
    q=enumerate_cadence_candidate_evidence(fs,((3,),(3,)),support,lines,130,130)
    assert q and q[0].multiples==(3,3) and q[0].matched_cells>=1
    evidenced=[x for candidate in q for x in candidate.cells if x.repeated_lattice]
    assert evidenced
    best=max(evidenced,key=lambda x:x.best_iou)
    assert best.best_iou>=.20
    assert best.outer_support>=1
    assert all(v>=1 for v in best.internal_lattice)

def test_candidate_report_fails_closed_without_independent_support():
    fs=(fam(0,(0,10,20,30)),fam(90,(0,-10,-20,-30)))
    assert enumerate_cadence_candidate_evidence(fs,((2,),(2,)),(),(),100,100)==()

def test_candidate_report_does_not_invent_subharmonic_multiples():
    fs=(fam(0,(0,10,20,30)),fam(90,(0,-10,-20,-30)))
    support=(cell(0,0,20,20),)
    assert enumerate_cadence_candidate_evidence(fs,((1,),(2,)),support,(),100,100)==()


def evidence(multiples,phases,repeated=True,iou=.3):
    item=CadenceCellEvidence(multiples,phases,((0,0),(0,30),(30,30),(30,0)),iou,2,(1,1),repeated)
    return CadenceCandidateEvidence(multiples,phases,1,iou,(item,))

def test_disambiguation_accepts_one_unique_lattice_supported_geometry_and_phase():
    result=select_uniquely_supported_candidate((evidence((6,10),(0,1)),evidence((4,10),(3,7),False,.4)))
    assert result.accepted and result.candidate.multiples==(6,10)

def test_disambiguation_rejects_competing_lattice_supported_cadences():
    result=select_uniquely_supported_candidate((evidence((3,4),(1,0)),evidence((4,4),(0,0))))
    assert not result.accepted and result.reason=="ambiguous_lattice_supported_cadence"

def test_disambiguation_rejects_competing_phases_of_same_cadence():
    result=select_uniquely_supported_candidate((evidence((4,4),(0,0)),evidence((4,4),(1,0))))
    assert not result.accepted and result.reason=="ambiguous_lattice_supported_phase"

def test_disambiguation_rejects_iou_only_candidate():
    result=select_uniquely_supported_candidate((evidence((7,3),(0,0),False,.8),))
    assert not result.accepted and result.reason=="repeated_lattice_support_required"


def test_disambiguation_deduplicates_same_geometry_and_phase():
 result=select_uniquely_supported_candidate((
   evidence((6,10),(0,1),True,.3),
   evidence((6,10),(0,1),True,.4),
 ))
 assert result.accepted
 assert result.candidate.phases==(0,1)
 assert result.candidate.iou_score==.4


def test_enumeration_rejects_invalid_iou_thresholds():
 fs=(fam(0,(0,10,20,30,40)),fam(90,(0,-10,-20,-30,-40)))
 support=(cell(0,0,20,20),)
 assert enumerate_cadence_candidate_evidence(fs,((2,),(2,)),support,(),100,100,minimum_iou=-.1)==()
 assert enumerate_cadence_candidate_evidence(fs,((2,),(2,)),support,(),100,100,minimum_iou=float('nan'))==()

def test_enumeration_rejects_empty_multiplier_axis():
 fs=(fam(0,(0,10,20,30,40)),fam(90,(0,-10,-20,-30,-40)))
 assert enumerate_cadence_candidate_evidence(fs,((),(2,)),(cell(0,0,20,20),),(),100,100)==()

def test_enumeration_rejects_noninteger_multiplier():
 fs=(fam(0,(0,10,20,30,40)),fam(90,(0,-10,-20,-30,-40)))
 assert enumerate_cadence_candidate_evidence(fs,((2.0,),(2,)),(cell(0,0,20,20),),(),100,100)==()

def test_enumeration_rejects_duplicate_multiplier_options():
 fs=(fam(0,(0,10,20,30,40)),fam(90,(0,-10,-20,-30,-40)))
 assert enumerate_cadence_candidate_evidence(fs,((2,2),(2,)),(cell(0,0,20,20),),(),100,100)==()

def test_disambiguation_rejects_mismatched_matched_cell_count():
 candidate=evidence((3,4),(0,0))
 candidate=CadenceCandidateEvidence(candidate.multiples,candidate.phases,2,candidate.iou_score,candidate.cells)
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_cell_provenance_mismatch():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((4,4),(0,0),candidate.cells[0].polygon_px,.3,2,(1,1),True)
 candidate=CadenceCandidateEvidence((3,4),(0,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_nonfinite_iou_score():
 candidate=evidence((3,4),(0,0))
 candidate=CadenceCandidateEvidence(candidate.multiples,candidate.phases,1,float('nan'),candidate.cells)
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_cell_iou_outside_probability_range():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(0,0),candidate.cells[0].polygon_px,1.1,2,(1,1),True)
 candidate=CadenceCandidateEvidence((3,4),(0,0),1,1.1,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_impossible_outer_support_count():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(0,0),candidate.cells[0].polygon_px,.3,5,(1,1),True)
 candidate=CadenceCandidateEvidence((3,4),(0,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_invalid_internal_lattice_shape():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(0,0),candidate.cells[0].polygon_px,.3,2,(1,),True)
 candidate=CadenceCandidateEvidence((3,4),(0,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_negative_internal_lattice_count():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(0,0),candidate.cells[0].polygon_px,.3,2,(-1,1),True)
 candidate=CadenceCandidateEvidence((3,4),(0,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'


def test_disambiguation_rejects_boolean_matched_cell_count():
 candidate=evidence((3,4),(0,0))
 candidate=CadenceCandidateEvidence(candidate.multiples,candidate.phases,True,candidate.iou_score,candidate.cells)
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_iou_score_not_equal_to_cells():
 candidate=evidence((3,4),(0,0))
 candidate=CadenceCandidateEvidence(candidate.multiples,candidate.phases,1,.4,candidate.cells)
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_boolean_multiplier():
 candidate=evidence((3,4),(0,0))
 candidate=CadenceCandidateEvidence((True,4),candidate.phases,1,candidate.iou_score,candidate.cells)
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_multiplier_below_two():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((1,4),(0,0),candidate.cells[0].polygon_px,.3,2,(1,1),True)
 candidate=CadenceCandidateEvidence((1,4),(0,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_boolean_phase():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(True,0),candidate.cells[0].polygon_px,.3,2,(1,1),True)
 candidate=CadenceCandidateEvidence((3,4),(True,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_negative_phase():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(-1,0),candidate.cells[0].polygon_px,.3,2,(1,1),True)
 candidate=CadenceCandidateEvidence((3,4),(-1,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_boolean_outer_support():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(0,0),candidate.cells[0].polygon_px,.3,True,(1,1),True)
 candidate=CadenceCandidateEvidence((3,4),(0,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_nonboolean_repeated_lattice_flag():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(0,0),candidate.cells[0].polygon_px,.3,2,(1,1),1)
 candidate=CadenceCandidateEvidence((3,4),(0,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'

def test_disambiguation_rejects_boolean_internal_lattice_count():
 candidate=evidence((3,4),(0,0))
 wrong=CadenceCellEvidence((3,4),(0,0),candidate.cells[0].polygon_px,.3,2,(True,1),True)
 candidate=CadenceCandidateEvidence((3,4),(0,0),1,.3,(wrong,))
 assert select_uniquely_supported_candidate((candidate,)).reason=='invalid_candidate_evidence'
