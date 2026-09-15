from math import cos,sin,radians
from mcm_solarcheck.pairing.oriented_features import OrientedStructuralPoint
from mcm_solarcheck.pairing.oriented_matching import match_oriented_points,split_oriented_matches

COORDS=((.1,.1),(.3,.12),(.55,.15),(.8,.2),(.15,.45),(.42,.48),(.72,.5),(.2,.78),(.5,.82),(.85,.75))

def grid(w,h,rotation=0,crossing=88):
    return tuple(OrientedStructuralPoint(x*w,y*h,rotation%180,(rotation+crossing)%180) for x,y in COORDS)


def test_matches_same_grid_across_sensor_resolution():
    # The M3T pair has nearly identical gimbal orientation. Resolution/FOV differ,
    # but an artificial change of line angle without rotating the point geometry is
    # not a physically valid rotation test for an axis-aware topology descriptor.
    thermal=grid(640,512,5);rgb=grid(4000,3000,5)
    matches=match_oriented_points(thermal,rgb,max_score=.03,ambiguity_margin=.005)
    assert len(matches)>=8
    for m in matches:
        assert abs(m.thermal.x/640-m.rgb.x/4000)<1e-9
        assert abs(m.thermal.y/512-m.rgb.y/3000)<1e-9


def test_incompatible_crossing_angle_is_rejected():
    assert match_oriented_points(grid(640,512,0,88),grid(4000,3000,0,55),max_score=.5)==()


def test_incompatible_grid_topology_is_rejected_even_with_loose_geometry_score():
    thermal=grid(640,512);rgb=list(grid(4000,3000));removed=rgb.pop(5)
    matches=match_oriented_points(thermal,tuple(rgb),max_score=1.0,ambiguity_margin=0,maximum_topology_distance=.05)
    assert all(not (m.thermal==thermal[5]) for m in matches)
    assert all(m.rgb!=removed for m in matches)


def test_ambiguous_duplicate_is_not_forced():
    thermal=grid(640,512);rgb=list(grid(4000,3000));rgb.append(rgb[0])
    matches=match_oriented_points(thermal,tuple(rgb),max_score=.03,ambiguity_margin=.005)
    assert all(not (m.thermal==thermal[0] and m.rgb==rgb[0]) for m in matches)


def test_fit_holdout_are_disjoint_and_distributed():
    matches=match_oriented_points(grid(640,512),grid(4000,3000),max_score=.03,ambiguity_margin=.005)
    fit,holdout=split_oriented_matches(matches)
    assert len(fit)>=4;assert len(holdout)>=4
    a={(p.thermal_x,p.thermal_y) for p in fit};b={(p.thermal_x,p.thermal_y) for p in holdout};assert a.isdisjoint(b)
    assert max(p.thermal_y for p in holdout)-min(p.thermal_y for p in holdout)>200


def test_negative_topology_weight_is_rejected():
    try:match_oriented_points(grid(640,512),grid(4000,3000),topology_weight=-1)
    except ValueError as exc:assert 'topology_weight' in str(exc)
    else:raise AssertionError('expected ValueError')
