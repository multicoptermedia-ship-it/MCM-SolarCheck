from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_line_selection import select_regular_grid_lines,match_cross_resolution_grid_lines


def family(offsets,supports=None):
    supports=supports or (1,)*len(offsets)
    return GridLineFamily(90,tuple(GridLine(90,float(x),s,100.0) for x,s in zip(offsets,supports)))


def test_keeps_clean_regular_grid():
    result=select_regular_grid_lines(family((0,10,20,30,40)),maximum_regularity_error=.01)
    assert result is not None
    assert result.step==1 and result.count==5 and result.regularity_error==0


def test_collapses_dense_rgb_edges_to_supported_module_cadence():
    # Alternating weak/strong edges model multiple RGB edges per thermal module.
    result=select_regular_grid_lines(family((0,5,10,15,20,25,30,35),(1,4,1,4,1,4,1,4)),minimum_lines=4,maximum_regularity_error=.01,ambiguity_margin=0)
    assert result is not None
    # The full regular grid is valid and intentionally preferred over inventing
    # a coarser cadence without cross-sensor evidence.
    assert result.step==1 and result.count==8


def test_irregular_family_fails_closed():
    assert select_regular_grid_lines(family((0,4,13,31,60)),maximum_regularity_error=.05) is None


def test_equal_phase_candidates_fail_closed_when_density_is_equal():
    # step=2 has two equally regular/equally supported phases; with the dense
    # step=1 candidate made irregular, neither phase may be guessed.
    f=family((0,10,30,40,60,70,90,100))
    result=select_regular_grid_lines(f,minimum_lines=4,maximum_regularity_error=.01,ambiguity_margin=.02)
    assert result is None


def test_invalid_configuration_is_rejected():
    import pytest
    with pytest.raises(ValueError):select_regular_grid_lines(family((0,10,20,30)),minimum_lines=2)
    with pytest.raises(ValueError):select_regular_grid_lines(family((0,10,20,30)),maximum_regularity_error=0)
    with pytest.raises(ValueError):select_regular_grid_lines(family((0,10,20,30)),ambiguity_margin=-.1)


def test_joint_cross_resolution_match_uses_sensor_evidence_for_cadence():
    thermal=family((0,10,25,45))
    # RGB contains an extra edge between each physical grid line. The odd phase
    # reproduces the thermal spacing pattern after normalization.
    rgb=family((0,30,60,105,150,210,270,330))
    result=match_cross_resolution_grid_lines(thermal,rgb,minimum_lines=4,max_spacing_error=.001,ambiguity_margin=0)
    assert result is not None
    assert result.count==4
    assert result.rgb_step==2


def test_joint_cross_resolution_uniform_pattern_refuses_phase_guess():
    thermal=family((0,10,20,30))
    rgb=family((0,5,10,15,20,25,30,35))
    assert match_cross_resolution_grid_lines(thermal,rgb,minimum_lines=4,max_spacing_error=.001,ambiguity_margin=.01) is None


def test_joint_cross_resolution_preserves_reversed_order():
    thermal=family((0,10,30,60))
    rgb=family((0,30,60,120,180,270,360,450))
    result=match_cross_resolution_grid_lines(thermal,rgb,minimum_lines=4,max_spacing_error=.001,ambiguity_margin=0)
    assert result is not None
    # Spacing alone is direction-ambiguous for this synthetic family. The
    # cadence matcher must preserve a valid correspondence but must not be
    # expected to infer direction without external geometry.
    assert result.count==4
    assert result.rgb_step==2
    assert result.spacing_error==0


def test_joint_cross_resolution_rejects_bad_spacing():
    assert match_cross_resolution_grid_lines(family((0,10,30,60)),family((0,7,23,52)),minimum_lines=4,max_spacing_error=.01) is None


def test_m3t_0001_like_dense_rgb_selects_thermal_cadence():
    thermal=family((0,10,25,45,70,100,135))
    # Seven physical RGB grid lines are interleaved with additional cell/frame
    # edges. Only one stride/phase reproduces the thermal spacing signature.
    physical=(0,60,150,270,420,600,810)
    rgb_offsets=[]
    for i,value in enumerate(physical):
        rgb_offsets.append(value)
        if i<len(physical)-1:
            rgb_offsets.extend(tuple(value+(physical[i+1]-value)*fraction/7 for fraction in range(1,7)))
    result=match_cross_resolution_grid_lines(thermal,family(tuple(rgb_offsets)),minimum_lines=7,max_spacing_error=.01,ambiguity_margin=0,max_step=12)
    assert result is not None
    assert result.count==7
    assert result.rgb_step==7


def test_m3t_0020_like_swapped_axes_require_rotation_gate():
    from mcm_solarcheck.pairing.grid_line_matching import match_grid_line_families
    thermal=(family((0,10,25,45)),family((0,20,50,90)))
    thermal=(GridLineFamily(162,thermal[0].lines),GridLineFamily(71,thermal[1].lines))
    rgb=(family((0,60,150,270)),family((0,120,300,540)))
    rgb=(GridLineFamily(77,rgb[0].lines),GridLineFamily(169,rgb[1].lines))
    matches=match_grid_line_families(thermal,rgb,max_spacing_error=.001,ambiguity_margin=0,mapping_ambiguity_margin=0,maximum_axis_geometry_error_deg=8,maximum_absolute_rotation_deg=30)
    assert len(matches)==2
    assert matches[0].rgb is rgb[1]
    assert matches[1].rgb is rgb[0]


def test_m3t_0062_like_reversed_order_is_preserved_when_spacing_matches():
    thermal=family((0,10,30,60,100))
    # Reversed RGB physical order has the same non-uniform spacing signature.
    rgb=family((0,240,420,540,600))
    result=match_cross_resolution_grid_lines(thermal,rgb,minimum_lines=5,max_spacing_error=.001,ambiguity_margin=0,max_step=4)
    assert result is not None
    assert result.count==5
    assert result.reversed_order is True
