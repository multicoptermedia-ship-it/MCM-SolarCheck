from mcm_solarcheck.pairing.structural_features import StructuralPoint
from mcm_solarcheck.pairing.structural_matching import match_structural_points,split_fit_holdout


def grid(scale_x,scale_y,offset_x=0,offset_y=0):
    coords=((.1,.1),(.3,.12),(.55,.15),(.8,.2),(.15,.45),(.42,.48),(.72,.5),(.2,.78),(.5,.82),(.85,.75))
    return tuple(StructuralPoint(offset_x+x*scale_x,offset_y+y*scale_y) for x,y in coords)


def test_matches_same_normalized_geometry_across_sensor_resolutions():
    thermal=grid(640,512);rgb=grid(4000,3000)
    matches=match_structural_points(thermal,rgb,max_score=.02,ambiguity_margin=.005)
    assert len(matches)>=8
    for match in matches:
        assert abs(match.thermal.x/640-match.rgb.x/4000)<1e-9
        assert abs(match.thermal.y/512-match.rgb.y/3000)<1e-9


def test_ambiguous_duplicate_geometry_is_not_forced():
    thermal=grid(640,512);rgb=list(grid(4000,3000));rgb.append(rgb[0])
    matches=match_structural_points(thermal,tuple(rgb),max_score=.02,ambiguity_margin=.005)
    assert all(not (m.thermal==thermal[0] and m.rgb==rgb[0]) for m in matches)


def test_unrelated_geometry_produces_no_confident_matches():
    thermal=grid(640,512)
    rgb=tuple(StructuralPoint(100+i*350,100+(i%2)*100) for i in range(10))
    assert match_structural_points(thermal,rgb,max_score=.01,ambiguity_margin=.005)==()


def test_split_keeps_independent_spatially_distributed_holdout():
    matches=match_structural_points(grid(640,512),grid(4000,3000),max_score=.02,ambiguity_margin=.005)
    fit,holdout=split_fit_holdout(matches,holdout_fraction=.3,minimum_holdout=4)
    assert len(fit)>=4;assert len(holdout)>=4
    fit_xy={(p.thermal_x,p.thermal_y) for p in fit};holdout_xy={(p.thermal_x,p.thermal_y) for p in holdout}
    assert fit_xy.isdisjoint(holdout_xy)
    assert max(p.thermal_y for p in holdout)-min(p.thermal_y for p in holdout)>200
