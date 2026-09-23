from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.cadence_gate import assess_module_cadence,assess_ambiguous_module_cadence

def fam(angle,offsets):return GridLineFamily(angle,tuple(GridLine(angle,x,1,10) for x in offsets))
def mod(w,h):return ModuleDetection(((0,0),(w,0),(w,h),(0,h)),.8)

def test_both_axes_use_family_normal_for_independent_cadence():
 q=assess_module_cadence((fam(0,(0,10,20,30,40,50)),fam(90,(0,10,20,30,40,50))),(mod(30,20),mod(30,20)))
 assert q.accepted and [a.dominant_multiple for a in q.axes]==[2,3]

def test_missing_image_support_fails_closed():
 assert assess_module_cadence((fam(0,(0,10,20,30,40,50)),fam(90,(0,10,20,30,40,50))),()).reason=='independent_image_support_required'

def test_one_unconfirmed_axis_rejects_gate():
 q=assess_module_cadence((fam(0,(0,10,20,30,40,50)),fam(90,(0,10,20,30,40,50))),(mod(30,10),mod(30,10)))
 assert not q.accepted and q.reason=='cadence_not_confirmed'


def test_ambiguous_gate_does_not_relax_without_lattice_evidence():
 q=assess_ambiguous_module_cadence(
   (fam(0,(0,10,20,30,40,50,60)),fam(90,(0,10,20,30,40,50,60))),
   (mod(30,40),mod(40,30)),(),100,100,
 )
 assert not q.accepted

def test_ambiguous_gate_preserves_primary_success():
 support=(mod(30,20),mod(30,20))
 families=(fam(0,(0,10,20,30,40,50)),fam(90,(0,10,20,30,40,50)))
 assert assess_ambiguous_module_cadence(families,support,(),100,100)==assess_module_cadence(families,support)


def test_lattice_resolution_never_synthesizes_independent_votes(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 families=(fam(0,(0,10,20,30,40,50,60)),fam(90,(0,10,20,30,40,50,60)))
 support=(mod(30,40),mod(40,30))
 monkeypatch.setattr(gate,'assess_module_cadence',lambda *a,**k:gate.CadenceGateResult(False,(
  gate.GridCadence(False,'ambiguous_cadence',10.0,None),
  gate.GridCadence(False,'ambiguous_cadence',10.0,None),
 ),'cadence_not_confirmed'))
 monkeypatch.setattr(gate,'supported_cadence_multiples',lambda *a,**k:(3,4))
 class Candidate:
  multiples=(3,4)
  phases=(1,2)
 class Resolution:
  accepted=True
  candidate=Candidate()
 monkeypatch.setattr(gate,'enumerate_cadence_candidate_evidence',lambda *a,**k:(Resolution.candidate,))
 monkeypatch.setattr(gate,'select_uniquely_supported_candidate',lambda evidence:Resolution())
 result=gate.assess_ambiguous_module_cadence(families,support,(),100,100)
 assert result.accepted
 assert tuple(a.dominant_multiple for a in result.axes)==(3,4)
 assert result.phases==(1,2)
 assert all(a.reason=='uniquely_lattice_supported' for a in result.axes)


def test_ambiguity_fallback_is_not_used_for_nonambiguous_rejection(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 families=(fam(0,(0,10,20,30,40,50)),fam(90,(0,10,20,30,40,50)))
 support=(mod(30,20),)
 primary=gate.assess_module_cadence(families,support)
 assert not primary.accepted
 assert not any(axis.reason=='ambiguous_cadence' for axis in primary.axes)
 monkeypatch.setattr(gate,'supported_cadence_multiples',lambda *a,**k:(_ for _ in ()).throw(AssertionError('fallback must not run')))
 assert gate.assess_ambiguous_module_cadence(families,support,(),100,100)==primary


def _ambiguity_setup(monkeypatch,gate,candidate,evidence=None):
 families=(fam(0,(0,10,20,30,40,50,60,70)),fam(90,(0,10,20,30,40,50,60,70)))
 support=(mod(30,40),mod(40,30))
 primary=gate.CadenceGateResult(False,(
  gate.GridCadence(False,'ambiguous_cadence',10.0,None),
  gate.GridCadence(False,'ambiguous_cadence',10.0,None),
 ),'cadence_not_confirmed')
 monkeypatch.setattr(gate,'assess_module_cadence',lambda *a,**k:primary)
 monkeypatch.setattr(gate,'supported_cadence_multiples',lambda *a,**k:(3,4))
 evidence=(candidate,) if evidence is None else evidence
 monkeypatch.setattr(gate,'enumerate_cadence_candidate_evidence',lambda *a,**k:evidence)
 class Resolution:
  accepted=True
  reason='accepted'
  def __init__(self,candidate):self.candidate=candidate
 monkeypatch.setattr(gate,'select_uniquely_supported_candidate',lambda items:Resolution(candidate))
 return families,support,primary

def test_fallback_rejects_nonpositive_image_dimensions(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 candidate=type('Candidate',(),{'multiples':(3,4),'phases':(0,0)})()
 families,support,_=_ambiguity_setup(monkeypatch,gate,candidate)
 assert gate.assess_ambiguous_module_cadence(families,support,(),0,100).reason=='invalid_image_dimensions'

def test_fallback_rejects_invalid_iou_threshold(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 candidate=type('Candidate',(),{'multiples':(3,4),'phases':(0,0)})()
 families,support,_=_ambiguity_setup(monkeypatch,gate,candidate)
 assert gate.assess_ambiguous_module_cadence(families,support,(),100,100,minimum_iou=1.1).reason=='invalid_minimum_iou'

def test_fallback_rejects_candidate_not_from_enumeration(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 candidate=type('Candidate',(),{'multiples':(3,4),'phases':(0,0)})()
 families,support,_=_ambiguity_setup(monkeypatch,gate,candidate,evidence=(object(),))
 assert gate.assess_ambiguous_module_cadence(families,support,(),100,100).reason=='resolved_candidate_not_enumerated'

def test_fallback_rejects_unvoted_resolved_cadence(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 candidate=type('Candidate',(),{'multiples':(5,4),'phases':(0,0)})()
 families,support,_=_ambiguity_setup(monkeypatch,gate,candidate)
 assert gate.assess_ambiguous_module_cadence(families,support,(),100,100).reason=='resolved_cadence_not_supported'

def test_fallback_rejects_noninteger_resolved_cadence(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 candidate=type('Candidate',(),{'multiples':(3.0,4),'phases':(0,0)})()
 families,support,_=_ambiguity_setup(monkeypatch,gate,candidate)
 assert gate.assess_ambiguous_module_cadence(families,support,(),100,100).reason=='resolved_cadence_not_supported'

def test_fallback_rejects_negative_resolved_phase_at_gate(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 candidate=type('Candidate',(),{'multiples':(3,4),'phases':(-1,0)})()
 families,support,_=_ambiguity_setup(monkeypatch,gate,candidate)
 assert gate.assess_ambiguous_module_cadence(families,support,(),100,100).reason=='resolved_phase_invalid'

def test_fallback_rejects_out_of_range_resolved_phase_at_gate(monkeypatch):
 import mcm_solarcheck.vision.cadence_gate as gate
 candidate=type('Candidate',(),{'multiples':(3,4),'phases':(99,0)})()
 families,support,_=_ambiguity_setup(monkeypatch,gate,candidate)
 assert gate.assess_ambiguous_module_cadence(families,support,(),100,100).reason=='resolved_phase_out_of_range'
