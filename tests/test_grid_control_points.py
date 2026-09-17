from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_line_matching import GridLineFamilyMatch
from mcm_solarcheck.pairing.grid_control_points import grid_control_points,split_grid_control_points
from mcm_solarcheck.pairing.registration import estimate_homography


def fam(offsets,angle,scale=1):return GridLineFamily(angle,tuple(GridLine(angle,o*scale,1,100*scale) for o in offsets))

def matched(t,r,reversed_order=False,start_t=0,start_r=0,count=None):
    return GridLineFamilyMatch(t,r,reversed_order,start_t,start_r,count or min(len(t.lines)-start_t,len(r.lines)-start_r),0)


def test_intersections_become_cross_sensor_control_points():
    tv=fam((10,30,50),90);th=fam((20,40,70,100),0)
    rv=fam((60,180,300),90);rh=fam((120,240,420,600),0)
    points=grid_control_points((matched(tv,rv),matched(th,rh)))
    assert len(points)==12
    for p in points:
        assert abs(p.rgb_x-6*p.thermal_x)<1e-9
        assert abs(p.rgb_y-6*p.thermal_y)<1e-9


def test_reversed_rgb_family_preserves_index_correspondence():
    tv=fam((10,30,50),90);th=fam((20,40,70,100),0)
    rv=fam((300,180,60),90);rh=fam((120,240,420,600),0)
    points=grid_control_points((matched(tv,rv,True),matched(th,rh)))
    assert len(points)==12
    for p in points:
        assert abs(p.rgb_x-6*p.thermal_x)<1e-9
        assert abs(p.rgb_y-6*p.thermal_y)<1e-9


def test_swapped_family_match_order_preserves_control_points():
    tv=fam((10,30,50),90);th=fam((20,40,70,100),0)
    rv=fam((60,180,300),90);rh=fam((120,240,420,600),0)
    normal=grid_control_points((matched(tv,rv),matched(th,rh)))
    swapped=grid_control_points((matched(th,rh),matched(tv,rv)))
    assert {(p.thermal_x,p.thermal_y,p.rgb_x,p.rgb_y) for p in normal}=={(p.thermal_x,p.thermal_y,p.rgb_x,p.rgb_y) for p in swapped}


def test_matched_subwindows_use_their_selected_indices():
    tv=fam((0,10,30,50,80),90);th=fam((0,20,40,70,100),0)
    rv=fam((0,60,180,300,480),90);rh=fam((0,120,240,420,600),0)
    points=grid_control_points((matched(tv,rv,start_t=1,start_r=1,count=3),matched(th,rh,start_t=1,start_r=1,count=4)))
    assert len(points)==12
    for p in points:
        assert abs(p.rgb_x-6*p.thermal_x)<1e-9
        assert abs(p.rgb_y-6*p.thermal_y)<1e-9


def test_requires_two_crossing_families():
    assert grid_control_points((matched(fam((1,2,3),90),fam((6,12,18),90)),))==()
    a=matched(fam((1,2,3),90),fam((6,12,18),90));b=matched(fam((4,5,6),100),fam((24,30,36),100))
    assert grid_control_points((a,b))==()


def test_fit_and_holdout_are_disjoint_and_sufficient():
    tv=fam((10,30,50,80),90);th=fam((20,40,70,100),0);rv=fam((60,180,300,480),90);rh=fam((120,240,420,600),0)
    points=grid_control_points((matched(tv,rv),matched(th,rh)))
    fit,holdout=split_grid_control_points(points)
    assert len(fit)>=6;assert len(holdout)>=4
    a={(p.thermal_x,p.thermal_y) for p in fit};b={(p.thermal_x,p.thermal_y) for p in holdout};assert a.isdisjoint(b)


def test_grid_points_validate_homography_on_independent_holdout():
    tv=fam((10,30,50,80),90);th=fam((20,40,70,100),0);rv=fam((60,180,300,480),90);rh=fam((120,240,420,600),0)
    fit,holdout=split_grid_control_points(grid_control_points((matched(tv,rv),matched(th,rh))))
    estimate=estimate_homography(fit,holdout)
    assert estimate.quality.validated is True
    assert estimate.quality.reason=='accepted'
    assert estimate.fit_points>=6
    assert estimate.inliers>=6
    assert estimate.quality.control_points>=4
    assert estimate.quality.rms_error_px<1e-6


def test_corrupted_holdout_refuses_otherwise_good_homography():
    tv=fam((10,30,50,80),90);th=fam((20,40,70,100),0);rv=fam((60,180,300,480),90);rh=fam((120,240,420,600),0)
    fit,holdout=split_grid_control_points(grid_control_points((matched(tv,rv),matched(th,rh))))
    corrupted=tuple(type(p)(p.thermal_x,p.thermal_y,p.rgb_x+100,p.rgb_y) for p in holdout)
    estimate=estimate_homography(fit,corrupted)
    assert estimate.quality.validated is False
    assert estimate.quality.reason=='reprojection_error_too_high'
    assert estimate.transform.validated is False


def test_too_few_points_refuse_split():
    tv=fam((10,30,50),90);th=fam((20,40,70),0);rv=fam((60,180,300),90);rh=fam((120,240,420),0)
    points=grid_control_points((matched(tv,rv),matched(th,rh)))
    assert len(points)==9;assert split_grid_control_points(points)==((),())
