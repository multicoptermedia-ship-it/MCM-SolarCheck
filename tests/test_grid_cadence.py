from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.vision.grid_cadence import assess_grid_cadence,select_supported_cadence_multiple

def fam(offsets):return GridLineFamily(0,tuple(GridLine(0,x,1,10) for x in offsets))

def test_regular_cell_cadence_is_not_mistaken_for_module_boundary_cadence():
 q=assess_grid_cadence(fam((0,10,20,30,40,50)))
 assert q.accepted and q.reason=='single_scale_only' and q.dominant_multiple==1

def test_irregular_spacing_fails_closed():
 assert not assess_grid_cadence(fam((0,10,31,44,80,95))).accepted

def test_too_few_gaps_fails_closed():
 assert assess_grid_cadence(fam((0,10,20))).reason=='insufficient_gaps'


def test_larger_cadence_requires_repeated_independent_support():
 q=select_supported_cadence_multiple(fam((0,10,20,30,40,50)),(29,31,30))
 assert q.accepted and q.dominant_multiple==3 and q.reason=='independently_supported'

def test_single_independent_interval_cannot_select_multiple():
 assert select_supported_cadence_multiple(fam((0,10,20,30,40,50)),(30,)).reason=='insufficient_independent_support'

def test_equal_competing_multiples_fail_closed():
 q=select_supported_cadence_multiple(fam((0,10,20,30,40,50)),(20,20,30,30))
 assert not q.accepted and q.reason=='ambiguous_cadence'
