from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_line_matching import match_grid_line_family,match_grid_line_families


def family(offsets,angle=90,scale=1):
    return GridLineFamily(angle,tuple(GridLine(angle,x*scale,1,100*scale) for x in offsets))


def test_matches_same_spacing_pattern_across_scale_and_offset():
    t=family((10,30,55,85,120));r=family((100,220,370,550,760),scale=1)
    m=match_grid_line_family(t,r,max_spacing_error=.001)
    assert m is not None;assert m.count==5;assert m.score<1e-9


def test_matches_contiguous_subset_when_rgb_has_extra_outer_lines():
    t=family((10,30,55,85));r=family((20,100,220,370,550,900))
    m=match_grid_line_family(t,r,max_spacing_error=.001,ambiguity_margin=.001)
    assert m is not None;assert m.count==4;assert m.start_rgb==1


def test_reversed_order_can_be_identified():
    t=family((0,10,30,60));r=family((0,180,300,360))
    m=match_grid_line_family(t,r,max_spacing_error=.001,ambiguity_margin=0)
    assert m is not None;assert m.reversed_order is True


def test_repetitive_uniform_spacing_is_rejected_as_ambiguous():
    t=family((0,10,20,30));r=family((0,100,200,300,400))
    assert match_grid_line_family(t,r,max_spacing_error=.01,ambiguity_margin=.01) is None


def test_two_families_are_mapped_one_to_one():
    thermal=(family((0,10,25,45),90),family((0,20,50,90),0))
    rgb=(family((0,120,300,540),0),family((0,60,150,270),90))
    matches=match_grid_line_families(thermal,rgb,max_spacing_error=.001,ambiguity_margin=0,mapping_ambiguity_margin=0)
    assert len(matches)==2
    assert len({id(m.thermal) for m in matches})==2;assert len({id(m.rgb) for m in matches})==2


def test_joint_mapping_preserves_common_sensor_rotation():
    thermal=(family((0,10,25,45),92),family((0,20,50,90),4))
    rgb=(family((0,60,150,270),3),family((0,120,300,540),91))
    matches=match_grid_line_families(thermal,rgb,max_spacing_error=.001,ambiguity_margin=0,mapping_ambiguity_margin=0,maximum_axis_geometry_error_deg=8)
    assert len(matches)==2
    assert matches[0].rgb is rgb[1]
    assert matches[1].rgb is rgb[0]


def test_ninety_degree_axis_swap_is_rejected_despite_spacing_fit():
    thermal=(family((0,10,25,45),92),family((0,20,50,90),4))
    rgb=(family((0,60,150,270),3),family((0,120,300,540),91))
    matches=match_grid_line_families(thermal,rgb,max_spacing_error=.001,ambiguity_margin=0,mapping_ambiguity_margin=0,maximum_axis_geometry_error_deg=8)
    assert all(abs(((m.rgb.angle_deg-m.thermal.angle_deg+90)%180)-90)<8 for m in matches)


def test_joint_mapping_rejects_inconsistent_axis_rotations():
    thermal=(family((0,10,25,45),90),family((0,20,50,90),0))
    rgb=(family((0,60,150,270),10),family((0,120,300,540),55))
    assert match_grid_line_families(thermal,rgb,max_spacing_error=.001,ambiguity_margin=0,mapping_ambiguity_margin=0,maximum_axis_geometry_error_deg=10)==()


def test_equally_good_physically_valid_axis_permutations_fail_closed():
    # Degenerate duplicate orientations make two permutations physically and
    # statistically indistinguishable; the matcher must refuse the assignment.
    pattern=(0,10,25,45)
    thermal=(family(pattern,90),family(pattern,90))
    rgb=(family(tuple(x*6 for x in pattern),91),family(tuple(x*6 for x in pattern),91))
    assert match_grid_line_families(thermal,rgb,max_spacing_error=.001,ambiguity_margin=0,mapping_ambiguity_margin=.01)==()


def test_insufficient_lines_fail_closed():
    assert match_grid_line_family(family((0,10,20)),family((0,100,200))) is None


def test_consistent_near_ninety_degree_axis_swap_is_rejected_by_absolute_rotation():
    # Crossing-angle and common-rotation consistency alone cannot distinguish
    # this swapped mapping. Near-synchronous M3T sensor geometry makes the
    # approximately 85-degree cross-sensor rotation physically implausible.
    thermal=(family((0,10,25,45),162),family((0,20,50,90),71))
    rgb=(family((0,60,150,270),77),family((0,120,300,540),169))
    assert match_grid_line_families(thermal,rgb,max_spacing_error=.001,ambiguity_margin=0,mapping_ambiguity_margin=0,maximum_axis_geometry_error_deg=8,maximum_absolute_rotation_deg=30)==()


def test_absolute_rotation_gate_accepts_small_common_rotation():
    thermal=(family((0,10,25,45),179),family((0,20,50,90),89))
    rgb=(family((0,60,150,270),91),family((0,120,300,540),1))
    matches=match_grid_line_families(thermal,rgb,max_spacing_error=.001,ambiguity_margin=0,mapping_ambiguity_margin=0,maximum_axis_geometry_error_deg=8,maximum_absolute_rotation_deg=30)
    assert len(matches)==2
    rotations=[((m.rgb.angle_deg-m.thermal.angle_deg+90)%180)-90 for m in matches]
    assert all(abs(rotation-2)<1e-9 for rotation in rotations)


def test_absolute_rotation_limit_is_validated():
    thermal=(family((0,10,25,45),90),family((0,20,50,90),0))
    rgb=(family((0,60,150,270),1),family((0,120,300,540),91))
    import pytest
    with pytest.raises(ValueError,match='maximum_absolute_rotation_deg'):
        match_grid_line_families(thermal,rgb,maximum_absolute_rotation_deg=91)
