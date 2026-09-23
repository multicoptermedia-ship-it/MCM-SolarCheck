from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.vision.grid_cadence import assess_grid_cadence,select_supported_cadence_multiple,cadence_line_subsets

def fam(offsets):return GridLineFamily(0,tuple(GridLine(0,x,1,10) for x in offsets))

def test_regular_cell_cadence_is_not_mistaken_for_module_boundary_cadence():
 q=assess_grid_cadence(fam((0,10,20,30,40,50)))
 assert q.accepted and q.reason=='lattice_scale_only' and q.dominant_multiple==1

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


def test_cadence_subsets_preserve_all_alignment_phases():
 f=fam((0,10,20,30,40,50,60))
 q=cadence_line_subsets(f,3)
 assert tuple(tuple(x.offset_px for x in s.lines) for s in q)==((0,30,60),(10,40),(20,50))

def test_invalid_or_unusable_multiple_returns_no_subsets():
 assert cadence_line_subsets(fam((0,10,20)),1)==()
 assert cadence_line_subsets(fam((0,10)),3)==()


def test_missing_grid_lines_preserve_base_lattice():
 q=assess_grid_cadence(fam((0,10,30,40,70,80)))
 assert q.accepted and abs(q.median_gap_px-10)<1e-9

def test_lattice_does_not_invent_smaller_subharmonic():
 q=assess_grid_cadence(fam((0,20,40,60,80,100)))
 assert q.accepted and abs(q.median_gap_px-20)<1e-9


def test_cadence_phases_follow_lattice_coordinates_when_lines_are_missing():
 f=fam((0,10,30,40,60,70))
 q=cadence_line_subsets(f,3)
 assert tuple(tuple(x.offset_px for x in s.lines) for s in q)==((0,30,60),(10,40,70))


def test_cadence_is_invariant_to_family_line_order():
 forward=assess_grid_cadence(fam((0,10,20,30,40,50)))
 reverse=assess_grid_cadence(fam((50,40,30,20,10,0)))
 assert reverse.accepted and reverse.median_gap_px==forward.median_gap_px


def test_equal_lattice_fit_prefers_smallest_observed_base_gap():
 q=assess_grid_cadence(fam((0,10,30,60,100,150)))
 assert q.accepted and abs(q.median_gap_px-10)<1e-9
