from mcm_solarcheck.pairing.oriented_features import OrientedStructuralPoint
from mcm_solarcheck.pairing.grid_topology import grid_topology_signatures,topology_distance


def grid(w,h,rotation=0):
    # Use a physically scaled grid so native-pixel projections differ only by scale.
    sx=w/640;sy=sx
    return tuple(OrientedStructuralPoint(x*640*sx,y*512*sy,rotation,(rotation+90)%180) for y in (.2,.5,.8) for x in (.15,.4,.7,.9))


def test_topology_is_uniform_scale_independent_for_same_grid():
    thermal=grid(640,512);rgb=grid(4000,3200)
    ts=grid_topology_signatures(thermal,(640,512));rs=grid_topology_signatures(rgb,(4000,3200))
    assert len(ts)==len(rs)
    assert max(topology_distance(a,b) for a,b in zip(ts,rs))<1e-3


def test_corner_and_interior_have_different_occupancy():
    sig=grid_topology_signatures(grid(640,512),(640,512))
    corner=sig[0];interior=sig[5]
    assert corner.occupancy!=interior.occupancy
    assert topology_distance(corner,interior)==float('inf')


def test_axis_order_is_canonicalized():
    points=grid(640,512);swapped=tuple(OrientedStructuralPoint(p.x,p.y,p.angle_b_deg,p.angle_a_deg) for p in points)
    a=grid_topology_signatures(points,(640,512));b=grid_topology_signatures(swapped,(640,512))
    assert all(topology_distance(x,y)<1e-9 for x,y in zip(a,b))


def test_tighter_angular_tolerance_changes_off_axis_neighbour_acceptance():
    center=OrientedStructuralPoint(50,50,0,90)
    off_axis=OrientedStructuralPoint(80,60,0,90)
    vertical=OrientedStructuralPoint(50,80,0,90)
    points=(center,off_axis,vertical)
    loose=grid_topology_signatures(points,(100,100),angular_tolerance_deg=20)[0]
    tight=grid_topology_signatures(points,(100,100),angular_tolerance_deg=10)[0]
    assert loose!=tight


def test_invalid_tolerance_is_rejected():
    try:grid_topology_signatures(grid(640,512),(640,512),angular_tolerance_deg=0)
    except ValueError as exc:assert 'angular_tolerance' in str(exc)
    else:raise AssertionError('expected ValueError')


def test_invalid_size_is_rejected():
    try:grid_topology_signatures((),(0,512))
    except ValueError as exc:assert 'dimensions' in str(exc)
    else:raise AssertionError('expected ValueError')
