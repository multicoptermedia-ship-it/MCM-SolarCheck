from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_line_selection import select_regular_grid_lines


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
