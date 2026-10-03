from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.pairing.grid_lines import extract_grid_line_families


def line(x1,y1,x2,y2,angle):
    length=((x2-x1)**2+(y2-y1)**2)**.5
    return StructuralLine(x1,y1,x2,y2,length,angle)


def pv_grid(scale=1):
    vertical=tuple(line(x*scale,10*scale,x*scale,500*scale,90) for x in (80,160,250,350,470))
    horizontal=tuple(line(20*scale,y*scale,600*scale,y*scale,0) for y in (70,150,240,340))
    return vertical+horizontal


def test_extracts_two_ordered_grid_families():
    families=extract_grid_line_families(pv_grid(),merge_distance_px=4)
    assert len(families)==2
    assert all(len(f.lines)>=4 for f in families)
    assert all(tuple(l.offset_px for l in f.lines)==tuple(sorted(l.offset_px for l in f.lines)) for f in families)


def test_spacing_profile_is_uniform_scale_invariant():
    a=extract_grid_line_families(pv_grid(),merge_distance_px=4)
    b=extract_grid_line_families(pv_grid(6),merge_distance_px=24)
    profiles_a=sorted(f.spacing_profile for f in a)
    profiles_b=sorted(f.spacing_profile for f in b)
    assert profiles_a==profiles_b


def test_duplicate_edges_are_merged_into_one_grid_line():
    lines=pv_grid()+(line(82,10,82,500,90),line(162,10,162,500,90))
    families=extract_grid_line_families(lines,merge_distance_px=4)
    vertical=max(families,key=lambda f:len(f.lines))
    assert any(l.support==2 for l in vertical.lines)


def test_exactly_equal_offsets_are_merged_without_comparing_line_objects():
    duplicates=tuple(line(80,10,80,500,90) for _ in range(3))
    vertical=duplicates+tuple(line(x,10,x,500,90) for x in (160,250,350))
    families=extract_grid_line_families(vertical,merge_distance_px=4)
    assert len(families)==1
    assert len(families[0].lines)==4
    merged=[grid_line for grid_line in families[0].lines if grid_line.support==3]
    assert len(merged)==1


def test_single_orientation_does_not_invent_second_family():
    vertical=tuple(line(x,0,x,500,90) for x in (50,100,150,200))
    families=extract_grid_line_families(vertical,merge_distance_px=4)
    assert len(families)==1


def test_noise_orientation_is_not_preferred_over_long_grid():
    noise=(line(0,0,60,60,45),line(20,0,80,60,45),line(40,0,100,60,45))
    families=extract_grid_line_families(pv_grid()+noise,merge_distance_px=4)
    assert len(families)==2
    angles=sorted(round(f.angle_deg) for f in families)
    assert angles==[0,90]


def test_single_extremely_long_roof_edge_does_not_seed_family_selection():
    # The old longest-line seed strategy could select this orientation first and
    # then exclude a real grid family through the minimum separation rule.
    roof=(line(0,0,3000,1500,27),)
    families=extract_grid_line_families(pv_grid()+roof,merge_distance_px=4)
    assert len(families)==2
    assert sorted(round(f.angle_deg) for f in families)==[0,90]


def test_repeated_grid_support_beats_longer_sparse_diagonal_structure():
    # Cell/roof diagonals can be individually longer than module-frame edges.
    # A sparse diagonal orientation must not outrank a denser repeated grid.
    diagonal=tuple(line(0,y,1200,y+840,35) for y in (0,220,440))
    families=extract_grid_line_families(pv_grid()+diagonal,merge_distance_px=4,minimum_lines=3)
    assert len(families)==2
    assert sorted(round(f.angle_deg) for f in families)==[0,90]


def test_invalid_parameters_fail_closed():
    for kwargs,expected in (
        ({'merge_distance_px':0},'merge_distance'),
        ({'minimum_family_separation_deg':0},'minimum_family_separation'),
        ({'minimum_family_separation_deg':91},'minimum_family_separation'),
    ):
        try:extract_grid_line_families(pv_grid(),**kwargs)
        except ValueError as exc:assert expected in str(exc)
        else:raise AssertionError('expected ValueError')
