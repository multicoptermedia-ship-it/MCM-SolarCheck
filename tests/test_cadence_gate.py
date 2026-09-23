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
 monkeypatch.setattr(gate,'supported_cadence_multiples',lambda *a,**k:(3,4))
 class Candidate:
  multiples=(3,4)
  phases=(1,2)
 class Resolution:
  accepted=True
  candidate=Candidate()
 monkeypatch.setattr(gate,'enumerate_cadence_candidate_evidence',lambda *a,**k:(object(),))
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
