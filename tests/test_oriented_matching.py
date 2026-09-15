from mcm_solarcheck.pairing.oriented_features import OrientedStructuralPoint
from mcm_solarcheck.pairing.oriented_matching import match_oriented_points,split_oriented_matches

COORDS=((.1,.1),(.3,.12),(.55,.15),(.8,.2),(.15,.45),(.42,.48),(.72,.5),(.2,.78),(.5,.82),(.85,.75))

def grid(w,h,rotation=0,crossing=88):
    return tuple(OrientedStructuralPoint(x*w,y*h,rotation%180,(rotation+crossing)%180) for x,y in COORDS)


def test_matches_same_grid_across_resolution_and_rotation():
    thermal=grid(640,512,5);rgb=grid(4000,3000,42)
    matches=match_oriented_points(thermal,rgb,max_score=.03,ambiguity_margin=.005)
    assert len(matches)>=8
    for m in matches:
        assert abs(m.thermal.x/640-m.rgb.x/4000)<1e-9
        assert abs(m.thermal.y/512-m.rgb.y/3000)<1e-9


def test_incompatible_crossing_angle_is_rejected():
    thermal=grid(640,512,0,88);rgb=grid(4000,3000,0,55)
    assert match_oriented_points(thermal,rgb,max_score=.5)==()


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
