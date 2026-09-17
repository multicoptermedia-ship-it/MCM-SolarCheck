from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_line_matching import GridLineFamilyMatch
from mcm_solarcheck.pairing.grid_control_points import grid_control_points,split_grid_control_points


def fam(offsets,angle,scale=1):return GridLineFamily(angle,tuple(GridLine(angle,o*scale,1,100*scale) for o in offsets))

def matched(t,r):return GridLineFamilyMatch(t,r,False,0,0,min(len(t.lines),len(r.lines)),0)


def test_intersections_become_cross_sensor_control_points():
    tv=fam((10,30,50),90);th=fam((20,40,70,100),0)
    rv=fam((60,180,300),90);rh=fam((120,240,420,600),0)
    points=grid_control_points((matched(tv,rv),matched(th,rh)))
    assert len(points)==12
    # Normal-form signs may depend on line orientation; correspondence scale must remain exact.
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


def test_too_few_points_refuse_split():
    tv=fam((10,30,50),90);th=fam((20,40,70),0);rv=fam((60,180,300),90);rh=fam((120,240,420),0)
    points=grid_control_points((matched(tv,rv),matched(th,rh)))
    assert len(points)==9;assert split_grid_control_points(points)==((),())
